"""LLM客户端封装"""
import asyncio
import json
from typing import Optional, Dict, Any, List, Callable, Tuple

from app.config import get_settings
from openai import OpenAI


class LLMClient:
    """LLM API客户端"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_api_base_url
        self.model = settings.llm_model
        self.timeout = 60.0
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or None,
            timeout=self.timeout,
        )

    def _chat_sync(self, payload: Dict[str, Any]) -> str:
        response = self.client.chat.completions.create(**payload)
        return response.choices[0].message.content or ""

    def _safe_json_loads(self, raw: str) -> Tuple[Optional[Dict[str, Any]], str]:
        try:
            return json.loads(raw), ""
        except Exception as exc:
            return None, f"JSON parse error: {type(exc).__name__}: {exc}"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[str] = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        return await asyncio.to_thread(self._chat_sync, payload)

    async def analyze_json(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant that responds in JSON format.",
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await self.chat(messages, response_format="json")
        data, error = self._safe_json_loads(response)
        if data is None:
            raise ValueError(error)
        return data

    async def analyze_json_with_repair(
        self,
        prompt: str,
        system_prompt: str,
        repair_system_prompt: str,
        repair_user_prompt_builder: Callable[[str, str], str],
        validator: Callable[[Any], Tuple[bool, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        response = await self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json",
        )
        data, error = self._safe_json_loads(response)
        if data is not None:
            valid, verror = validator(data)
            if valid:
                return data
            error = verror or error

        repair_user_prompt = repair_user_prompt_builder(response, error)
        repair_messages = [
            {"role": "system", "content": repair_system_prompt},
            {"role": "user", "content": repair_user_prompt},
        ]
        repair_response = await self.chat(
            repair_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json",
        )
        repair_data, repair_error = self._safe_json_loads(repair_response)
        if repair_data is None:
            raise ValueError(repair_error)
        valid, verror = validator(repair_data)
        if not valid:
            raise ValueError(verror)
        return repair_data
