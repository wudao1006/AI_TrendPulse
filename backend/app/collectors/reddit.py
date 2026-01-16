"""Reddit数据采集器 - 支持PRAW API和HTTP Fallback"""
import asyncio
import logging
import random
import re
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

import requests

from app.collectors.base import BaseCollector, CollectedItem
from app.config import get_settings
from scripts.user_agent_generator import get_random_user_agent

logger = logging.getLogger(__name__)

# 尝试导入praw，如果不可用则设置为None
try:
    import praw
    from praw.models import Submission
    PRAW_AVAILABLE = True
except ImportError:
    praw = None
    Submission = None
    PRAW_AVAILABLE = False
    logger.warning("PRAW库未安装，将使用HTTP fallback模式")


class RedditCollector(BaseCollector):
    """Reddit采集器，支持PRAW官方API和HTTP Fallback模式

    当以下情况时自动降级到HTTP模式：
    1. PRAW库未安装
    2. Reddit API凭证未配置或为空
    3. PRAW初始化失败
    """

    platform_name = "reddit"

    def __init__(self, config: dict = None):
        super().__init__(config)
        settings = get_settings()

        self.use_fallback = False
        self.reddit = None

        # 检查是否应该使用fallback模式
        if not PRAW_AVAILABLE:
            self.use_fallback = True
            logger.info("Reddit采集器: PRAW不可用，使用HTTP fallback模式")
        elif not self._has_valid_api_config(settings):
            self.use_fallback = True
            logger.info("Reddit采集器: API凭证未配置，使用HTTP fallback模式")
        else:
            # 尝试初始化PRAW
            try:
                self.reddit = praw.Reddit(
                    client_id=settings.reddit_client_id,
                    client_secret=settings.reddit_client_secret,
                    user_agent=settings.reddit_user_agent,
                )
                logger.info("Reddit采集器: 使用PRAW API模式")
            except Exception as e:
                self.use_fallback = True
                logger.warning(f"Reddit采集器: PRAW初始化失败({e})，使用HTTP fallback模式")

    def _has_valid_api_config(self, settings) -> bool:
        """检查是否有有效的API配置"""
        client_id = getattr(settings, 'reddit_client_id', None)
        client_secret = getattr(settings, 'reddit_client_secret', None)

        # 检查配置是否存在且不是占位符
        if not client_id or not client_secret:
            return False

        # 检查是否是常见的占位符值
        placeholder_values = ['', 'your_client_id', 'your_client_secret', 'xxx', 'placeholder']
        if client_id.lower() in placeholder_values or client_secret.lower() in placeholder_values:
            return False

        return True

    def _normalize_query(self, keyword: str) -> str:
        if not keyword:
            return ""
        parts = re.split(r"[，,;/|、]+", keyword)
        cleaned = [p.strip() for p in parts if p.strip()]
        if len(cleaned) <= 1:
            return keyword.strip()
        # Use OR to broaden matching across multiple keywords.
        return " OR ".join(dict.fromkeys(cleaned))

    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        """采集Reddit数据，自动选择PRAW或HTTP模式"""
        platform_config = self.config.get("platform_config", {})
        search_query = self._normalize_query(keyword)

        if self.use_fallback:
            return await self._collect_via_http(search_query, limit, platform_config)
        else:
            return await self._collect_via_praw(search_query, limit, platform_config)

    async def _collect_via_praw(
        self,
        keyword: str,
        limit: int,
        platform_config: Dict,
    ) -> List[CollectedItem]:
        """使用PRAW API采集数据"""
        items = []
        subreddit = platform_config.get("subreddit", "all")
        sort = platform_config.get("sort", "relevance")
        time_filter = platform_config.get("time_filter", "week")
        include_comments = platform_config.get("include_comments", True)
        comments_limit = platform_config.get("comments_limit", 10)
        try:
            comments_limit = max(0, int(comments_limit))
        except (TypeError, ValueError):
            comments_limit = 10

        loop = asyncio.get_event_loop()
        posts = await loop.run_in_executor(
            None,
            lambda: list(self.reddit.subreddit(subreddit).search(
                keyword,
                sort=sort,
                time_filter=time_filter,
                limit=limit,
            ))
        )

        for post in posts:
            post_item = self._parse_post(post)
            if post_item and self.is_valid_item(post_item):
                items.append(post_item)

            if include_comments and comments_limit > 0:
                try:
                    post.comments.replace_more(limit=0)
                    sample_limit = max(comments_limit * 2, comments_limit)
                    top_comments = sorted(
                        post.comments.list()[:sample_limit],
                        key=lambda c: getattr(c, 'score', 0),
                        reverse=True
                    )[:comments_limit]

                    for comment in top_comments:
                        comment_item = self._parse_comment(comment, post)
                        if comment_item and self.is_valid_item(comment_item):
                            items.append(comment_item)
                except Exception:
                    pass

        return items

    async def _collect_via_http(
        self,
        keyword: str,
        limit: int,
        platform_config: Dict,
        max_retries: int = 3,
    ) -> List[CollectedItem]:
        """使用HTTP请求采集数据（fallback模式）

        Args:
            keyword: 搜索关键词
            limit: 采集数量限制
            platform_config: 平台配置
            max_retries: 整体采集失败时的最大重试次数

        Returns:
            采集到的数据列表
        """
        subreddit = platform_config.get("subreddit", "all")
        sort = platform_config.get("sort", "relevance")
        time_filter = platform_config.get("time_filter", "week")
        include_comments = platform_config.get("include_comments", True)
        comments_limit = platform_config.get("comments_limit", 10)

        try:
            comments_limit = max(0, int(comments_limit))
        except (TypeError, ValueError):
            comments_limit = 10

        last_error = None

        for attempt in range(max_retries):
            try:
                items = []
                loop = asyncio.get_event_loop()

                # 获取帖子
                logger.info(f"Reddit HTTP采集: 搜索 '{keyword}'，第{attempt + 1}次尝试...")
                posts_data = await loop.run_in_executor(
                    None,
                    lambda: self._http_search_posts(keyword, limit, subreddit, sort, time_filter)
                )

                if not posts_data:
                    if attempt < max_retries - 1:
                        wait_time = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Reddit HTTP采集: 未获取到帖子数据，{wait_time:.1f}s后重试...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning("Reddit HTTP采集: 多次尝试后仍未获取到数据")
                        return []

                logger.info(f"Reddit HTTP采集: 获取到 {len(posts_data)} 个帖子")

                for post_data in posts_data:
                    post_item = self._parse_post_from_json(post_data)
                    if post_item and self.is_valid_item(post_item):
                        items.append(post_item)

                        # 获取评论
                        if include_comments and comments_limit > 0:
                            post_id = post_data.get('id')
                            post_subreddit = post_data.get('subreddit')
                            if post_id and post_subreddit:
                                comments_data = await self._fetch_comments_with_retry(
                                    post_id, post_subreddit, comments_limit, loop
                                )
                                for comment_data in comments_data:
                                    comment_item = self._parse_comment_from_json(comment_data, post_data)
                                    if comment_item and self.is_valid_item(comment_item):
                                        items.append(comment_item)

                logger.info(f"Reddit HTTP采集完成: 共获取 {len(items)} 条数据")
                return items

            except asyncio.CancelledError:
                # 任务被取消，不重试
                logger.info("Reddit HTTP采集被取消")
                raise

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Reddit HTTP采集异常({type(e).__name__}: {e})，"
                        f"第{attempt + 1}/{max_retries}次重试，等待 {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Reddit HTTP采集在{max_retries}次重试后失败: {type(e).__name__}: {e}")

        return []

    def _get_random_headers(self) -> Dict[str, str]:
        """获取随机的请求头"""
        return {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.reddit.com/',
        }

    def _is_retryable_error(self, exception: Exception) -> bool:
        """判断异常是否可重试"""
        retryable_exceptions = (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            ConnectionResetError,
            ConnectionRefusedError,
            ConnectionAbortedError,
        )
        return isinstance(exception, retryable_exceptions)

    def _http_request_with_retry(
        self,
        url: str,
        params: Dict = None,
        max_retries: int = 3,
        base_delay: float = 2.0,
    ) -> Optional[Dict]:
        """带重试的HTTP请求

        Args:
            url: 请求URL
            params: 请求参数
            max_retries: 最大重试次数（默认3次）
            base_delay: 基础延迟时间（秒），用于指数退避

        Returns:
            响应JSON数据，失败返回None
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                headers = self._get_random_headers()
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=15,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit，等待后重试
                    wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Reddit rate limit (429)，第{attempt + 1}次重试，等待 {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code in (500, 502, 503, 504):
                    # 服务器错误，可重试
                    wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Reddit服务器错误({response.status_code})，第{attempt + 1}次重试，等待 {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 403:
                    logger.error("Reddit返回403禁止访问，停止重试")
                    return None
                elif response.status_code == 404:
                    logger.warning("Reddit返回404未找到")
                    return None
                else:
                    logger.warning(f"Reddit HTTP请求失败，状态码: {response.status_code}")
                    # 非预期状态码，尝试重试
                    if attempt < max_retries - 1:
                        time.sleep(base_delay)
                        continue

            except requests.exceptions.Timeout as e:
                last_exception = e
                wait_time = base_delay * (2 ** attempt)
                logger.warning(f"Reddit请求超时，第{attempt + 1}/{max_retries}次重试，等待 {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                wait_time = base_delay * (2 ** attempt)
                logger.warning(f"Reddit连接错误({type(e).__name__})，第{attempt + 1}/{max_retries}次重试，等待 {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue

            except requests.exceptions.ChunkedEncodingError as e:
                last_exception = e
                wait_time = base_delay * (2 ** attempt)
                logger.warning(f"Reddit响应编码错误，第{attempt + 1}/{max_retries}次重试，等待 {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue

            except (ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError) as e:
                last_exception = e
                wait_time = base_delay * (2 ** attempt)
                logger.warning(f"网络连接被重置/拒绝({type(e).__name__})，第{attempt + 1}/{max_retries}次重试，等待 {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue

            except requests.exceptions.RequestException as e:
                # 其他请求异常，不可重试
                logger.error(f"Reddit请求异常(不可重试): {type(e).__name__}: {e}")
                return None

            except Exception as e:
                # 未知异常
                logger.error(f"Reddit请求未知异常: {type(e).__name__}: {e}")
                return None

        # 所有重试都失败
        if last_exception:
            logger.error(f"Reddit请求在{max_retries}次重试后仍然失败: {type(last_exception).__name__}")

        return None

    def _http_search_posts(
        self,
        keyword: str,
        limit: int,
        subreddit: str = "all",
        sort: str = "relevance",
        time_filter: str = "week",
    ) -> List[Dict]:
        """通过HTTP搜索Reddit帖子"""
        # Reddit JSON API的搜索端点
        if subreddit == "all":
            url = "https://www.reddit.com/search.json"
        else:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"

        params = {
            'q': keyword,
            'limit': min(limit, 100),  # Reddit API限制最多100
            'sort': sort,
            't': time_filter,
            'type': 'link',
            'restrict_sr': 'true' if subreddit != "all" else 'false',
            'raw_json': 1,
        }

        data = self._http_request_with_retry(url, params)
        if not data:
            return []

        try:
            posts = data.get('data', {}).get('children', [])
            return [post.get('data', {}) for post in posts if post.get('data')]
        except (KeyError, TypeError) as e:
            logger.error(f"解析Reddit搜索结果失败: {e}")
            return []

    async def _fetch_comments_with_retry(
        self,
        post_id: str,
        subreddit: str,
        comments_limit: int,
        loop: asyncio.AbstractEventLoop,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> List[Dict]:
        """带重试机制的评论获取

        Args:
            post_id: 帖子ID
            subreddit: 子版块名称
            comments_limit: 评论数量限制
            loop: 事件循环
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）

        Returns:
            评论数据列表，失败返回空列表
        """
        last_exception = None

        for attempt in range(max_retries):
            # 添加随机延迟避免被限速
            if attempt > 0:
                wait_time = base_delay * (2 ** (attempt - 1)) + random.uniform(0.3, 0.8)
                logger.debug(f"评论获取重试等待 {wait_time:.1f}s (帖子 {post_id})")
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(random.uniform(0.5, 1.5))

            try:
                comments_data = await loop.run_in_executor(
                    None,
                    lambda pid=post_id, psub=subreddit: self._http_get_comments(
                        pid, psub, comments_limit
                    )
                )

                if comments_data:
                    return comments_data

                # 如果返回空列表，可能是临时问题，继续重试
                if attempt < max_retries - 1:
                    logger.debug(f"帖子 {post_id} 评论为空，第{attempt + 1}/{max_retries}次重试...")
                    continue

            except (requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError,
                    ConnectionResetError,
                    ConnectionRefusedError,
                    ConnectionAbortedError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.debug(
                        f"获取帖子 {post_id} 评论网络错误({type(e).__name__})，"
                        f"第{attempt + 1}/{max_retries}次重试..."
                    )
                    continue
                else:
                    logger.warning(f"获取帖子 {post_id} 评论失败(已重试{max_retries}次): {type(e).__name__}")

            except Exception as e:
                # 其他异常不重试，直接跳过
                logger.debug(f"获取帖子 {post_id} 评论异常(不重试): {type(e).__name__}: {e}")
                return []

        if last_exception:
            logger.debug(f"帖子 {post_id} 评论获取在{max_retries}次重试后失败")

        return []

    def _http_get_comments(
        self,
        post_id: str,
        subreddit: str,
        limit: int = 10,
    ) -> List[Dict]:
        """通过HTTP获取帖子评论"""
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"

        params = {
            'limit': min(limit * 2, 50),  # 获取更多以便筛选
            'sort': 'top',
            'depth': 1,  # 只获取顶级评论
            'raw_json': 1,
        }

        data = self._http_request_with_retry(url, params)
        if not data:
            return []

        try:
            # Reddit返回的是一个数组，第二个元素包含评论
            if isinstance(data, list) and len(data) > 1:
                comments_data = data[1].get('data', {}).get('children', [])
                result = []
                for comment in comments_data:
                    if comment.get('kind') == 't1':  # t1 表示评论
                        comment_body = comment.get('data', {})
                        if comment_body:
                            result.append(comment_body)
                # 按分数排序并限制数量
                result.sort(key=lambda x: x.get('score', 0), reverse=True)
                return result[:limit]
            return []
        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"解析Reddit评论失败: {e}")
            return []

    def _parse_post(self, post: Submission) -> Optional[CollectedItem]:
        try:
            content = self.clean_text(post.selftext) if post.selftext else None

            return CollectedItem(
                platform=self.platform_name,
                content_type="post",
                source_id=post.id,
                title=self.clean_text(post.title),
                content=content,
                author=str(post.author) if post.author else None,
                url=f"https://reddit.com{post.permalink}",
                metrics={
                    "upvotes": post.score,
                    "upvote_ratio": post.upvote_ratio,
                    "num_comments": post.num_comments,
                },
                extra_fields={
                    "subreddit": str(post.subreddit),
                    "is_video": post.is_video,
                },
                published_at=datetime.utcfromtimestamp(post.created_utc),
            )
        except Exception:
            return None

    def _parse_comment(self, comment, post: Submission) -> Optional[CollectedItem]:
        try:
            content = self.clean_text(comment.body)
            if not content or content in ["[deleted]", "[removed]"]:
                return None

            author = str(comment.author) if comment.author else None
            if author and "bot" in author.lower():
                return None

            return CollectedItem(
                platform=self.platform_name,
                content_type="comment",
                source_id=comment.id,
                title=None,
                content=content,
                author=author,
                url=f"https://reddit.com{post.permalink}{comment.id}",
                metrics={"upvotes": comment.score},
                extra_fields={
                    "post_id": post.id,
                    "subreddit": str(post.subreddit),
                },
                published_at=datetime.utcfromtimestamp(comment.created_utc),
            )
        except Exception:
            return None

    def _parse_post_from_json(self, post_data: Dict) -> Optional[CollectedItem]:
        """从JSON数据解析帖子（HTTP fallback模式使用）"""
        try:
            title = self.clean_text(post_data.get('title', ''))
            selftext = post_data.get('selftext', '')
            content = self.clean_text(selftext) if selftext else None

            # 获取发布时间
            created_utc = post_data.get('created_utc')
            published_at = None
            if created_utc:
                try:
                    published_at = datetime.utcfromtimestamp(float(created_utc))
                except (ValueError, TypeError):
                    pass

            permalink = post_data.get('permalink', '')
            url = f"https://reddit.com{permalink}" if permalink else None

            return CollectedItem(
                platform=self.platform_name,
                content_type="post",
                source_id=post_data.get('id', ''),
                title=title,
                content=content,
                author=post_data.get('author'),
                url=url,
                metrics={
                    "upvotes": post_data.get('score', 0),
                    "upvote_ratio": post_data.get('upvote_ratio', 0),
                    "num_comments": post_data.get('num_comments', 0),
                },
                extra_fields={
                    "subreddit": post_data.get('subreddit', ''),
                    "is_video": post_data.get('is_video', False),
                },
                published_at=published_at,
            )
        except Exception as e:
            logger.debug(f"解析帖子JSON失败: {e}")
            return None

    def _parse_comment_from_json(
        self,
        comment_data: Dict,
        post_data: Dict,
    ) -> Optional[CollectedItem]:
        """从JSON数据解析评论（HTTP fallback模式使用）"""
        try:
            body = comment_data.get('body', '')
            content = self.clean_text(body)

            if not content or content in ["[deleted]", "[removed]"]:
                return None

            author = comment_data.get('author')
            if author and "bot" in author.lower():
                return None

            # 获取发布时间
            created_utc = comment_data.get('created_utc')
            published_at = None
            if created_utc:
                try:
                    published_at = datetime.utcfromtimestamp(float(created_utc))
                except (ValueError, TypeError):
                    pass

            post_permalink = post_data.get('permalink', '')
            comment_id = comment_data.get('id', '')
            url = f"https://reddit.com{post_permalink}{comment_id}" if post_permalink else None

            return CollectedItem(
                platform=self.platform_name,
                content_type="comment",
                source_id=comment_id,
                title=None,
                content=content,
                author=author,
                url=url,
                metrics={"upvotes": comment_data.get('score', 0)},
                extra_fields={
                    "post_id": post_data.get('id', ''),
                    "subreddit": post_data.get('subreddit', ''),
                },
                published_at=published_at,
            )
        except Exception as e:
            logger.debug(f"解析评论JSON失败: {e}")
            return None
