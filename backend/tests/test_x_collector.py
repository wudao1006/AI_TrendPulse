import asyncio

from app.collectors.x import XCollector
from app.config import get_settings


async def main() -> int:
    settings = get_settings()
    if not (settings.x_accounts_json or settings.x_accounts_path):
        print("X accounts config missing (X_ACCOUNTS_JSON or X_ACCOUNTS_PATH).")
        return 1

    collector = XCollector(
        config={
            "x_accounts_path": settings.x_accounts_path,
            "x_accounts_json": settings.x_accounts_json,
            "x_headless": settings.x_headless,
            "x_proxy": settings.x_proxy,
            "x_timeout_ms": settings.x_timeout_ms,
            "x_account_error_limit": settings.x_account_error_limit,
            "platform_config": {
                "sort": "latest",
                "include_replies": True,
                "max_replies": 5,
                "reply_depth": 1,
            },
        }
    )

    keyword = "deepseek"
    items = await collector.collect(keyword=keyword, limit=5, language="en")
    print(f"Collected {len(items)} items for '{keyword}'.")
    for idx, item in enumerate(items[:5], start=1):
        content = (item.content or item.title or "").replace("\n", " ").strip()
        if len(content) > 120:
            content = f"{content[:117]}..."
        print(f"{idx}. {item.content_type} {item.source_id} {item.author} {item.url}")
        print(f"   content: {content or '[empty]'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
