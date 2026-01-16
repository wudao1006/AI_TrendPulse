"""YouTube数据采集器"""
from datetime import datetime
from typing import List, Optional

from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from app.collectors.base import BaseCollector, CollectedItem
from app.config import get_settings


class YouTubeCollector(BaseCollector):
    """YouTube采集器，使用官方API + youtube-transcript-api"""

    platform_name = "youtube"

    def __init__(self, config: dict = None):
        super().__init__(config)
        settings = get_settings()

        self.youtube = build(
            "youtube", "v3",
            developerKey=settings.youtube_api_key,
        )

    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        items = []
        platform_config = self.config.get("platform_config", {})
        include_transcript = platform_config.get("include_transcript", True)
        transcript_language = platform_config.get("transcript_language", language)
        segment_duration_sec = platform_config.get("segment_duration_sec", 300)
        try:
            segment_duration_sec = int(segment_duration_sec)
        except (TypeError, ValueError):
            segment_duration_sec = 300

        # limit 代表要获取的视频数量（不是字幕段数量）
        try:
            video_limit = int(limit)
        except (TypeError, ValueError):
            video_limit = 10
        video_limit = min(max(1, video_limit), 50)

        search_response = self.youtube.search().list(
            q=keyword,
            part="snippet",
            type="video",
            maxResults=video_limit,
            order="relevance",
            relevanceLanguage=language,
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

        if not video_ids:
            return items

        videos_response = self.youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids),
        ).execute()

        for video in videos_response.get("items", []):
            video_item = self._parse_video(video)
            if video_item and self.is_valid_item(video_item):
                items.append(video_item)

            if include_transcript:
                transcript_items = self._get_transcript(
                    video["id"],
                    transcript_language,
                    segment_duration_sec=segment_duration_sec,
                )
                items.extend(transcript_items)

        return items

    def _parse_video(self, video: dict) -> Optional[CollectedItem]:
        try:
            snippet = video["snippet"]
            statistics = video.get("statistics", {})

            return CollectedItem(
                platform=self.platform_name,
                content_type="video",
                source_id=video["id"],
                title=self.clean_text(snippet.get("title")),
                content=self.clean_text(snippet.get("description")),
                author=snippet.get("channelTitle"),
                url=f"https://www.youtube.com/watch?v={video['id']}",
                metrics={
                    "views": int(statistics.get("viewCount", 0)),
                    "likes": int(statistics.get("likeCount", 0)),
                    "num_comments": int(statistics.get("commentCount", 0)),
                },
                extra_fields={
                    "channel_id": snippet.get("channelId"),
                    "tags": snippet.get("tags", []),
                },
                published_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
            )
        except Exception:
            return None

    def _get_transcript(
        self,
        video_id: str,
        language: str,
        segment_duration_sec: int = 300,
    ) -> List[CollectedItem]:
        items = []

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            transcript = None
            normalized_language = (language or "").strip().lower()
            if normalized_language in {"all", "*", "any"}:
                language = ""
            if language:
                try:
                    transcript = transcript_list.find_transcript([language])
                except NoTranscriptFound:
                    transcript = None
                if transcript is None:
                    try:
                        transcript = transcript_list.find_generated_transcript([language, "en"])
                    except NoTranscriptFound:
                        transcript = None

            if transcript is None:
                transcript = self._select_any_transcript(transcript_list)
                if transcript is None:
                    return items

            transcript_data = transcript.fetch()
            segments = self._segment_transcript(
                transcript_data,
                video_id,
                segment_duration=segment_duration_sec,
            )
            items.extend(segments)

        except (TranscriptsDisabled, VideoUnavailable):
            pass
        except Exception:
            pass

        return items

    def _select_any_transcript(self, transcript_list):
        for attr in ("_manually_created_transcripts", "manually_created_transcripts"):
            transcripts_map = getattr(transcript_list, attr, None)
            if isinstance(transcripts_map, dict) and transcripts_map:
                return next(iter(transcripts_map.values()))
        for attr in ("_generated_transcripts", "generated_transcripts"):
            transcripts_map = getattr(transcript_list, attr, None)
            if isinstance(transcripts_map, dict) and transcripts_map:
                return next(iter(transcripts_map.values()))
        try:
            return next(iter(transcript_list))
        except (StopIteration, TypeError):
            return None
        except Exception:
            return None

    def _segment_transcript(
        self,
        transcript_data: List[dict],
        video_id: str,
        segment_duration: int = 300,
    ) -> List[CollectedItem]:
        items = []
        current_segment = []
        current_start = 0
        segment_index = 0

        for entry in transcript_data:
            start_time = entry.get("start", 0)
            text = entry.get("text", "").strip()

            if not text:
                continue

            if start_time - current_start >= segment_duration and current_segment:
                segment_text = " ".join(current_segment)
                if len(segment_text) >= 50:
                    items.append(CollectedItem(
                        platform=self.platform_name,
                        content_type="transcript",
                        source_id=f"{video_id}_seg_{segment_index}",
                        title=None,
                        content=self.clean_text(segment_text),
                        author=None,
                        url=f"https://www.youtube.com/watch?v={video_id}&t={int(current_start)}",
                        metrics={},
                        extra_fields={
                            "video_id": video_id,
                            "segment_index": segment_index,
                            "start_time": current_start,
                            "end_time": start_time,
                        },
                        published_at=None,
                    ))

                current_segment = []
                current_start = start_time
                segment_index += 1

            current_segment.append(text)

        if current_segment:
            segment_text = " ".join(current_segment)
            if len(segment_text) >= 50:
                items.append(CollectedItem(
                    platform=self.platform_name,
                    content_type="transcript",
                    source_id=f"{video_id}_seg_{segment_index}",
                    title=None,
                    content=self.clean_text(segment_text),
                    author=None,
                    url=f"https://www.youtube.com/watch?v={video_id}&t={int(current_start)}",
                    metrics={},
                    extra_fields={
                        "video_id": video_id,
                        "segment_index": segment_index,
                        "start_time": current_start,
                    },
                    published_at=None,
                ))

        return items
