# Usage Notes

## Mindmap rendering (ECharts)
- Web builds render mindmaps in an `IFrameElement` via `HtmlElementView` using ECharts (SVG renderer).
- Mobile/desktop builds render the same ECharts mindmap inside `WebView`.
- `MermaidView` falls back to a code-only view if the iframe/WebView fails to load.
- ECharts is loaded from jsdelivr CDN; if blocked, serve ECharts locally and update the HTML source.

## LLM client
- LLM calls use the OpenAI SDK (sync client) via an async wrapper.
- Required env vars: `LLM_API_KEY`, `LLM_API_BASE_URL` (must include `/v1`), `LLM_MODEL`.
- Example for Moonshot:
  - `LLM_API_BASE_URL=https://api.moonshot.cn/v1`
  - `LLM_MODEL=kimi-k2-turbo-preview`
## Prompt design
- Prompt sources live in `backend/prompts/analysis_prompts.py` and are versioned (`analysis-v1.6.1`).
- Sentiment: JSON only, exact N items, ordered 1..N, `score` 0-100, 0-3 `key_phrases` copied from text.
- Sentiment: key phrases are contiguous substrings, short length, use rubric for mixed/neutral content.
- Clustering: JSON only, 2-6 viewpoints (adaptive), noun-phrase titles, grounded descriptions, ordered by prevalence.
- Summary: 4-6 sentences covering overall trend, dominant views, dissent, and sentiment balance.
- Clustering: each opinion includes `points` (2-4 short bullet points) for richer mindmaps.
- Mermaid: Mermaid-only output, `mindmap` root with `root((keyword))`, sentiment branch, opinion branches with `Points` sub-branch.
## Reddit Collector
- Supports two modes: **PRAW API** (official) and **HTTP Fallback** (no credentials required).
- Auto-fallback to HTTP mode when PRAW unavailable or API credentials missing.
- Multi-keyword search: separators (`,`, `，`, `;`, `/`, `|`) are converted to `OR` queries.
- **Retry mechanisms** (HTTP Fallback mode):
  | Layer | Method | Behavior |
  |-------|--------|----------|
  | Overall flow | `_collect_via_http` | Retries full collection on failure (default 3x) |
  | HTTP request | `_http_request_with_retry` | Retries on timeout/5xx/429 with exponential backoff |
  | Comment fetch | `_fetch_comments_with_retry` | Retries per-post comment retrieval (default 3x) |
- Exponential backoff: `base_delay * 2^attempt + random jitter`.
- Retryable errors: Timeout, ConnectionError, ChunkedEncodingError, ConnectionReset/Refused/Aborted, HTTP 429/5xx.
- Rate limit protection: random delays (0.5-1.5s) between requests.

## X (Twitter) Collector
- Uses Playwright + cookies. Requires at least one account cookie.
- Account pool accepts either `X_ACCOUNTS_PATH` (JSON file) or `X_ACCOUNTS_JSON` (string).
- Account JSON can be either a list or `{ "accounts": [...] }`.
- Single account works; multiple accounts rotate automatically.
- User-Agent is randomized via `scripts/user_agent_generator.py`.
- Account entries may include either `cookies` (structured list) or a raw `cookie_header` string.
- Per-task config:
  - `limit` (posts), `sort` (`top`/`latest`)
  - `include_replies` (bool), `max_replies`, `reply_depth` (1 or 2)
- If Playwright is not installed, X collection returns an empty list with a warning.
- After installing the Python package, run `playwright install` to fetch browser binaries.
- Frontend supports per-task and subscription config for X (sorting, reply toggle, reply count, reply depth).

Example account pool JSON:
```json
[
  {
    "id": "acc-1",
    "label": "primary",
    "cookies": [
      { "name": "auth_token", "value": "xxx", "domain": ".x.com", "path": "/" }
    ]
  }
]
```

## Scheduler
- Scheduler status endpoint: `GET /api/v1/subscriptions/scheduler/status`
  - Returns `scheduler_enabled`, `initialized`, `lock_acquired`, `job_count`.
- Subscription job info: `GET /api/v1/subscriptions/{id}/job`
  - Returns `last_run_at`, `next_run_at`, job trigger info, and scheduler status snapshot.
- Subscription list refreshes `next_run_at` from the running scheduler when enabled.
- Subscriptions support minute-level intervals via `interval_minutes` (takes priority over `interval_hours`).

## Subscriptions
- The subscription dialog no longer exposes a global "default limit".
- The backend `limit` value is derived from per-platform config limits and sent automatically.
- UI supports interval minutes for testing (leave empty to use hours).
- If upgrading an existing database, add `interval_minutes` column to `subscriptions`.

## Opinion clustering
- Adaptive opinion count is controlled by env vars:
  - `OPINION_COUNT_MIN`, `OPINION_COUNT_MAX`
  - `OPINION_COUNT_THRESHOLDS` (comma-separated, e.g. `12,24,36,48`)

## Mindmap styling
- Mindmap supports zoom/pan with toolbar controls and mouse/touch gestures.
- Nodes are styled per depth and special nodes (`Points`, `Sentiment`, `NN/100`) are highlighted.

## Output guardrails
- JSON responses are validated before use.
- On validation failure, the system sends a repair prompt and retries once.
- Mermaid output is validated and repaired once before falling back to a template.

## Tests
- X collector smoke test: `python -m tests.test_x_collector`
