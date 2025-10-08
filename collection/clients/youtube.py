import httpx
import logging
import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

logger = logging.getLogger(__name__)

class YouTubeSettings(BaseSettings):
    youtube_api_key: str

    class Config:
        env_file = ".env"
        extra = "ignore"

class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    description: str
    channel: str
    category: str
    tags: List[str]
    country_code: str
    published_at: datetime
    view_count: int
    like_count: int
    comment_count: int

class YouTubeClient:
    def __init__(self):
        self.settings = YouTubeSettings()
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.client = httpx.Client(
            timeout=10.0,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def get_trending_videos(self, region_code: str = "KR", max_results: int = 50) -> List[YouTubeVideo]:
        """Fetch trending videos from YouTube Data API v3"""
        try:
            # Step 1: Get video list from mostPopular chart
            videos_response = self._fetch_videos_list(region_code, max_results)
            video_ids = [item["id"] for item in videos_response.get("items", [])]

            if not video_ids:
                logger.warning("No video IDs found in trending response")
                return []

            # Step 2: Get detailed video information
            videos_details = self._fetch_videos_details(video_ids)

            # Step 3: Parse and return structured data
            return self._parse_videos(videos_details, region_code)

        except Exception as e:
            logger.error(f"Failed to fetch trending videos: {e}", extra={"trace_id": "youtube_fetch_error"})
            raise

    def _fetch_videos_list(self, region_code: str, max_results: int) -> Dict[str, Any]:
        """Fetch mostPopular videos list"""
        return self._make_request("videos", {
            "part": "id",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results
        })

    def _fetch_videos_details(self, video_ids: List[str]) -> Dict[str, Any]:
        """Fetch detailed video information"""
        return self._make_request("videos", {
            "part": "snippet,statistics",
            "id": ",".join(video_ids)
        })

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=0.2),
        retry_error_callback=lambda retry_state: logger.warning(
            f"Retry {retry_state.attempt_number}: {retry_state.outcome.exception()}"
        )
    )
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with retry logic for 429/5xx errors"""
        params = {
            **params,
            "key": self.settings.youtube_api_key
        }

        try:
            response = self.client.get(f"{self.base_url}/{endpoint}", params=params)

            # Retry on 429 (rate limit) and 5xx (server errors)
            if response.status_code == 429 or response.status_code >= 500:
                logger.warning(f"HTTP {response.status_code}: retrying request")
                response.raise_for_status()

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise

    def _parse_videos(self, videos_data: Dict[str, Any], region_code: str) -> List[YouTubeVideo]:
        """Parse video data into YouTubeVideo models"""
        videos = []

        for item in videos_data.get("items", []):
            try:
                snippet = item["snippet"]
                statistics = item["statistics"]

                video = YouTubeVideo(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    channel=snippet.get("channelTitle", ""),
                    category=snippet.get("categoryId", ""),
                    tags=snippet.get("tags", []),
                    country_code=region_code,
                    published_at=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")),
                    view_count=int(statistics.get("viewCount", 0)),
                    like_count=int(statistics.get("likeCount", 0)),
                    comment_count=int(statistics.get("commentCount", 0))
                )
                videos.append(video)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse video {item.get('id', 'unknown')}: {e}")
                continue

        return videos