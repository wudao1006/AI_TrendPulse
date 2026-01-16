import asyncio

from app.analyzers.llm_client import LLMClient
from app.config import get_settings


async def main() -> int:
    settings = get_settings()
    if not settings.llm_api_key:
        print("LLM_API_KEY is empty in environment/.env.")
        return 1

    print(f"LLM base URL: {settings.llm_api_base_url}")
    print(f"LLM model: {settings.llm_model}")

    client = LLMClient()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'pong' only."},
    ]

    try:
        reply = await client.chat(messages, temperature=0.2, max_tokens=50)
        print("Chat reply:", reply)
    except Exception as exc:
        print("Chat error:", type(exc).__name__, exc)
        return 2

    try:
        json_reply = await client.analyze_json(
            "Return JSON exactly as: {\"ping\":\"pong\"}.",
            system_prompt="Respond in JSON only.",
        )
        print("JSON reply:", json_reply)
    except Exception as exc:
        print("JSON error:", type(exc).__name__, exc)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
