"""X (Twitter) collector powered by Playwright + cookies."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from app.collectors.base import BaseCollector, CollectedItem
from scripts.user_agent_generator import get_random_user_agent

logger = logging.getLogger(__name__)


@dataclass
class XAccount:
    account_id: str
    label: str
    cookies: List[Dict[str, Any]]
    status: str = "active"
    error_count: int = 0
    last_used_at: Optional[datetime] = None


class XAccountPool:
    def __init__(self, accounts: List[XAccount]):
        self.accounts = accounts
        self._cursor = 0

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "XAccountPool":
        accounts_json = config.get("x_accounts_json")
        accounts_path = config.get("x_accounts_path")
        accounts: List[XAccount] = []

        if accounts_json:
            accounts = cls._parse_accounts(accounts_json)
        elif accounts_path:
            accounts = cls._load_from_file(accounts_path)

        return cls(accounts)

    @staticmethod
    def _load_from_file(path: str) -> List[XAccount]:
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("X accounts file not found: %s", path)
            return []
        except OSError as exc:
            logger.warning("Failed to read X accounts file: %s", exc)
            return []
        return XAccountPool._parse_accounts(raw)

    @staticmethod
    def _parse_accounts(raw: str) -> List[XAccount]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid X accounts JSON: %s", exc)
            return []

        accounts: List[XAccount] = []
        if isinstance(data, dict):
            data = data.get("accounts", [])

        if not isinstance(data, list):
            logger.warning("X accounts JSON must be a list or {accounts: []}.")
            return []

        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                continue
            cookies = entry.get("cookies")
            if not isinstance(cookies, list) or not cookies:
                cookie_header = entry.get("cookie_header")
                if isinstance(cookie_header, str) and cookie_header.strip():
                    cookie_domain = entry.get("cookie_domain") or ".x.com"
                    cookie_path = entry.get("cookie_path") or "/"
                    cookies = _parse_cookie_header(
                        cookie_header,
                        domain=str(cookie_domain),
                        path=str(cookie_path),
                    )
                else:
                    continue
            account_id = str(entry.get("id") or entry.get("account_id") or idx)
            label = str(entry.get("label") or entry.get("name") or account_id)
            status = str(entry.get("status") or "active")
            accounts.append(
                XAccount(
                    account_id=account_id,
                    label=label,
                    cookies=cookies,
                    status=status,
                )
            )
        return accounts

    def has_accounts(self) -> bool:
        return bool(self.accounts)

    def get_next_account(self) -> Optional[XAccount]:
        active_accounts = [acc for acc in self.accounts if acc.status == "active"]
        if not active_accounts:
            return None
        account = active_accounts[self._cursor % len(active_accounts)]
        self._cursor += 1
        account.last_used_at = datetime.utcnow()
        return account

    def mark_failure(self, account: XAccount, max_errors: int = 3) -> None:
        account.error_count += 1
        if account.error_count >= max_errors:
            account.status = "paused"

    def mark_success(self, account: XAccount) -> None:
        account.error_count = 0


class XCollector(BaseCollector):
    """Framework for X (Twitter) collection via Playwright + cookies."""

    platform_name = "x"
    _status_re = re.compile(r"/status/(\d+)")

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.platform_config = self.config.get("platform_config", {}) or {}
        self.account_pool = XAccountPool.from_config(self.config)
        self.headless = bool(self.config.get("x_headless", True))
        self.proxy = self.config.get("x_proxy") or None
        self.user_agent = self.config.get("x_user_agent") or None
        self.timeout_ms = int(self.config.get("x_timeout_ms", 30000))
        self.max_account_errors = int(self.config.get("x_account_error_limit", 3))

    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        if not self.account_pool.has_accounts():
            logger.warning("X collector has no accounts configured.")
            return []

        accounts_total = len(self.account_pool.accounts)
        attempts = max(accounts_total, 1)

        include_replies = bool(
            self.platform_config.get(
                "include_replies",
                self.platform_config.get("include_comments", True),
            )
        )
        max_replies = max(
            0,
            int(
                self.platform_config.get(
                    "max_replies",
                    self.platform_config.get("comments_limit", 20),
                )
            ),
        )
        reply_depth = max(1, int(self.platform_config.get("reply_depth", 1)))
        sort = str(self.platform_config.get("sort", "top"))

        logger.info(
            "X collect start: keyword=%s limit=%s language=%s sort=%s include_replies=%s max_replies=%s depth=%s",
            keyword,
            limit,
            language,
            sort,
            include_replies,
            max_replies,
            reply_depth,
        )

        last_error: Optional[Exception] = None
        for _ in range(attempts):
            account = self.account_pool.get_next_account()
            if not account:
                break
            try:
                logger.info("X collect using account: %s (status=%s)", account.label, account.status)
                items = await self._collect_with_playwright(
                    account=account,
                    keyword=keyword,
                    limit=limit,
                    language=language,
                    include_replies=include_replies,
                    max_replies=max_replies,
                    reply_depth=reply_depth,
                    sort=sort,
                )
                self.account_pool.mark_success(account)
                logger.info("X collect done: total_items=%s", len(items))
                return items
            except Exception as exc:
                last_error = exc
                logger.warning("X collector failed for account %s: %s", account.label, exc)
                self.account_pool.mark_failure(account, self.max_account_errors)

        if last_error:
            logger.warning("X collector exhausted all accounts: %s", last_error)
        return []

    async def _collect_with_playwright(
        self,
        account: XAccount,
        keyword: str,
        limit: int,
        language: str,
        include_replies: bool,
        max_replies: int,
        reply_depth: int,
        sort: str,
    ) -> List[CollectedItem]:
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            logger.warning("Playwright not available: %s", exc)
            return []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                proxy=_build_proxy(self.proxy),
            )
            locale = "en-US" if language == "en" else "zh-CN"
            user_agent = self.user_agent or get_random_user_agent()
            context = await browser.new_context(
                user_agent=user_agent,
                locale=locale,
                viewport={"width": 1280, "height": 720},
            )
            await context.add_cookies(account.cookies)

            try:
                page = await context.new_page()
                page.set_default_timeout(self.timeout_ms)

                await page.goto("https://x.com/home", wait_until="domcontentloaded")
                is_logged_in = await self._is_logged_in(page)
                if not is_logged_in:
                    raise RuntimeError("X login failed or cookies expired.")
                logger.info("X login check OK for account: %s", account.label)

                posts = await self._collect_search_posts(
                    page=page,
                    keyword=keyword,
                    limit=limit,
                    language=language,
                    sort=sort,
                )

                items = list(posts)
                logger.info("X search collected posts: %s", len(posts))
                if include_replies and posts and max_replies > 0:
                    replies = await self._collect_replies(
                        context=context,
                        posts=posts,
                        max_replies=max_replies,
                        reply_depth=reply_depth,
                    )
                    items.extend(replies)
                    logger.info("X replies collected: %s", len(replies))

                return items
            finally:
                await context.close()
                await browser.close()

    async def _is_logged_in(self, page) -> bool:
        if await page.locator('a[href="/login"]').count() > 0:
            return False
        if await page.locator('a[href="/home"]').count() > 0:
            return True
        if await page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').count() > 0:
            return True
        return True

    async def _collect_search_posts(
        self,
        page,
        keyword: str,
        limit: int,
        language: str,
        sort: str,
    ) -> List[CollectedItem]:
        url = self._build_search_url(keyword, language, sort)
        logger.info("X search URL: %s", url)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=self.timeout_ms)

        seen_ids: set[str] = set()
        items: List[CollectedItem] = []
        stagnant_rounds = 0
        last_seen = 0
        max_scrolls = max(8, limit * 2)

        for _ in range(max_scrolls):
            new_items = await self._extract_tweets_from_page(
                page=page,
                seen_ids=seen_ids,
                content_type="post",
                parent_id=None,
                depth=0,
                exclude_ids=None,
            )
            if new_items:
                items.extend(new_items)
            if len(seen_ids) == last_seen:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
                last_seen = len(seen_ids)

            if len(items) >= limit or stagnant_rounds >= 3:
                break

            await self._scroll_page(page)

        if not items:
            logger.warning("X search returned no items for keyword=%s", keyword)
        return items[:limit]

    async def _collect_replies(
        self,
        context,
        posts: List[CollectedItem],
        max_replies: int,
        reply_depth: int,
    ) -> List[CollectedItem]:
        replies: List[CollectedItem] = []
        for post in posts:
            if len(replies) >= max_replies:
                break
            logger.debug("X collecting replies for post=%s", post.source_id)
            post_replies = await self._collect_replies_for_post(
                context=context,
                post=post,
                limit=max_replies - len(replies),
                reply_depth=reply_depth,
            )
            replies.extend(post_replies)
        return replies

    async def _collect_replies_for_post(
        self,
        context,
        post: CollectedItem,
        limit: int,
        reply_depth: int,
    ) -> List[CollectedItem]:
        if not post.url or limit <= 0:
            return []

        page = await context.new_page()
        page.set_default_timeout(self.timeout_ms)
        try:
            await page.goto(post.url, wait_until="domcontentloaded")
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=self.timeout_ms)

            replies = await self._collect_replies_from_page(
                page=page,
                parent_id=post.source_id,
                limit=limit,
                depth=1,
            )

            if reply_depth > 1 and replies:
                nested = await self._collect_nested_replies(
                    context=context,
                    replies=replies,
                    limit=limit - len(replies),
                )
                replies.extend(nested)
            return replies
        finally:
            await page.close()

    async def _collect_replies_from_page(
        self,
        page,
        parent_id: str,
        limit: int,
        depth: int,
    ) -> List[CollectedItem]:
        seen_ids: set[str] = set()
        exclude_ids = {parent_id}
        items: List[CollectedItem] = []
        stagnant_rounds = 0
        last_seen = 0
        max_scrolls = max(6, limit * 2)

        for _ in range(max_scrolls):
            new_items = await self._extract_tweets_from_page(
                page=page,
                seen_ids=seen_ids,
                content_type="comment",
                parent_id=parent_id,
                depth=depth,
                exclude_ids=exclude_ids,
            )
            if new_items:
                items.extend(new_items)
            if len(seen_ids) == last_seen:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
                last_seen = len(seen_ids)

            if len(items) >= limit or stagnant_rounds >= 3:
                break

            await self._scroll_page(page)

        return items[:limit]

    async def _collect_nested_replies(
        self,
        context,
        replies: List[CollectedItem],
        limit: int,
    ) -> List[CollectedItem]:
        if limit <= 0:
            return []
        nested: List[CollectedItem] = []
        for reply in replies:
            if len(nested) >= limit:
                break
            if not reply.url:
                continue
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)
            try:
                await page.goto(reply.url, wait_until="domcontentloaded")
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=self.timeout_ms)
                more = await self._collect_replies_from_page(
                    page=page,
                    parent_id=reply.source_id,
                    limit=limit - len(nested),
                    depth=2,
                )
                nested.extend(more)
            finally:
                await page.close()
        return nested

    async def _extract_tweets_from_page(
        self,
        page,
        seen_ids: set[str],
        content_type: str,
        parent_id: Optional[str],
        depth: int,
        exclude_ids: Optional[set[str]],
    ) -> List[CollectedItem]:
        items: List[CollectedItem] = []
        articles = await page.query_selector_all('article[data-testid="tweet"]')
        for article in articles:
            item = await self._parse_tweet_from_element(
                article=article,
                content_type=content_type,
                parent_id=parent_id,
                depth=depth,
            )
            if not item:
                continue
            if exclude_ids and item.source_id in exclude_ids:
                continue
            if item.source_id in seen_ids:
                continue
            seen_ids.add(item.source_id)
            items.append(item)
        return items

    async def _parse_tweet_from_element(
        self,
        article,
        content_type: str,
        parent_id: Optional[str],
        depth: int,
    ) -> Optional[CollectedItem]:
        url = await self._get_first_href(article, 'a[href*="/status/"]')
        if not url:
            return None
        full_url = self._normalize_url(url)
        source_id = self._extract_status_id(full_url)
        if not source_id:
            return None

        text = await self._get_text(article, 'div[data-testid="tweetText"]')
        content = self.clean_text(text) or text
        title = (content or "").strip()[:80] if content else None

        author_name = await self._get_author_name(article)
        author_handle = await self._get_author_handle(article)
        published_at = self._parse_datetime(await self._get_attr(article, 'time', 'datetime'))

        metrics = {
            "num_comments": await self._get_metric(article, "reply"),
            "retweets": await self._get_metric(article, "retweet"),
            "likes": await self._get_metric(article, "like"),
            "views": await self._get_views(article),
        }

        extra_fields: Dict[str, Any] = {}
        if author_name:
            extra_fields["author_name"] = author_name
        if author_handle:
            extra_fields["author_handle"] = author_handle
        if parent_id:
            extra_fields["parent_id"] = parent_id
            extra_fields["depth"] = depth

        return CollectedItem(
            platform=self.platform_name,
            content_type=content_type,
            source_id=source_id,
            title=title,
            content=content,
            author=author_handle or author_name,
            url=full_url,
            metrics=metrics,
            extra_fields=extra_fields,
            published_at=published_at,
        )

    async def _get_text(self, element, selector: str) -> Optional[str]:
        target = await element.query_selector(selector)
        if not target:
            return None
        text = await target.inner_text()
        return text.strip() if text else None

    async def _get_attr(self, element, selector: str, attr: str) -> Optional[str]:
        target = await element.query_selector(selector)
        if not target:
            return None
        value = await target.get_attribute(attr)
        return value.strip() if value else None

    async def _get_first_href(self, element, selector: str) -> Optional[str]:
        target = await element.query_selector(selector)
        if not target:
            return None
        href = await target.get_attribute("href")
        return href.strip() if href else None

    async def _get_author_handle(self, article) -> Optional[str]:
        user_link = await article.query_selector('div[data-testid="User-Name"] a')
        if not user_link:
            return None
        href = await user_link.get_attribute("href")
        if not href:
            return None
        handle = href.strip().lstrip("/")
        if handle and "/" not in handle:
            return handle
        return None

    async def _get_author_name(self, article) -> Optional[str]:
        name_container = await article.query_selector('div[data-testid="User-Name"]')
        if not name_container:
            return None
        spans = await name_container.query_selector_all("span")
        for span in spans:
            text = (await span.inner_text()).strip()
            if text and not text.startswith("@"):
                return text
        return None

    async def _get_metric(self, article, testid: str) -> int:
        metric = await article.query_selector(f'div[data-testid="{testid}"]')
        if not metric:
            return 0
        label = await metric.get_attribute("aria-label")
        text = label or (await metric.inner_text())
        return self._parse_count(text)

    async def _get_views(self, article) -> int:
        view_el = await article.query_selector('a[href*="/analytics"]')
        if not view_el:
            view_el = await article.query_selector('div[data-testid="viewCount"]')
        if not view_el:
            return 0
        label = await view_el.get_attribute("aria-label")
        text = label or (await view_el.inner_text())
        return self._parse_count(text)

    async def _scroll_page(self, page) -> None:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(random.uniform(0.7, 1.4))

    def _build_search_url(self, keyword: str, language: str, sort: str) -> str:
        query = keyword.strip()
        if language:
            query = f"{query} lang:{language}"
        encoded = quote_plus(query)
        sort_key = "top" if sort.lower() in {"top", "relevance"} else "live"
        return f"https://x.com/search?q={encoded}&src=typed_query&f={sort_key}"

    def _normalize_url(self, url: str) -> str:
        if url.startswith("http"):
            return url
        return f"https://x.com{url}"

    def _extract_status_id(self, url: str) -> Optional[str]:
        match = self._status_re.search(url)
        if match:
            return match.group(1)
        return None

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _parse_count(self, text: Optional[str]) -> int:
        if not text:
            return 0
        cleaned = text.replace(",", "").strip().lower()
        match = re.search(r"([\d.]+)\s*([km]?)", cleaned)
        if not match:
            return 0
        value = float(match.group(1))
        suffix = match.group(2)
        if suffix == "k":
            value *= 1000
        elif suffix == "m":
            value *= 1000000
        return int(value)


def _build_proxy(proxy: Optional[str]) -> Optional[Dict[str, str]]:
    if not proxy:
        return None
    return {"server": proxy}


def _parse_cookie_header(cookie_header: str, domain: str, path: str) -> List[Dict[str, str]]:
    cookies: List[Dict[str, str]] = []
    if not cookie_header:
        return cookies
    parts = [part.strip() for part in cookie_header.split(";") if part.strip()]
    for part in parts:
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"')
        if not name:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
            }
        )
    return cookies
