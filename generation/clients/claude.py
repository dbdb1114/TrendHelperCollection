import httpx
import json
import logging
import time
from typing import Dict, Any
from pydantic_settings import BaseSettings

from generation.schemas.idea import IdeaRequest, IdeaResponse, GenerationMetadata
from generation.clients.model_client import IdeaModelClient

logger = logging.getLogger(__name__)

class ClaudeSettings(BaseSettings):
    anthropic_api_key: str
    claude_model: str = "claude-3-haiku-20240307"

    class Config:
        env_file = ".env"
        extra = "ignore"

class ClaudeClient(IdeaModelClient):
    def __init__(self):
        self.settings = ClaudeSettings()
        self.client = httpx.Client(
            timeout=60.0,
            headers={
                "x-api-key": self.settings.anthropic_api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def generate_ideas(self, request: IdeaRequest, trace_id: str) -> IdeaResponse:
        """Generate content ideas with retry logic"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                # Generate content
                response_data = self._call_claude_api(request, trace_id, attempt)

                # Parse and validate response
                idea_response = self._parse_response(response_data, trace_id, attempt)

                # Add metadata
                generation_time = time.time() - start_time
                idea_response.metadata = GenerationMetadata(
                    model=self.settings.claude_model,
                    generation_time=generation_time,
                    retry_count=attempt
                ).dict()

                logger.info(f"Content generation successful", extra={
                    "trace_id": trace_id,
                    "attempt": attempt + 1,
                    "generation_time": generation_time
                })

                return idea_response

            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}", extra={
                    "trace_id": trace_id,
                    "attempt": attempt + 1
                })

                if attempt == max_retries - 1:
                    raise Exception(f"All generation attempts failed. Last error: {e}")

        raise Exception("Max retries exceeded")

    def _call_claude_api(self, request: IdeaRequest, trace_id: str, attempt: int) -> Dict[str, Any]:
        """Call Claude API to generate content"""
        prompt = self._build_prompt(request)

        payload = {
            "model": self.settings.claude_model,
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = self.client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload
        )

        response.raise_for_status()
        return response.json()

    def _build_prompt(self, request: IdeaRequest) -> str:
        """Build Claude prompt for content generation"""
        keywords_str = ", ".join(request.keywords)
        signals_str = ", ".join([f"{k}: {v}" for k, v in request.signals.items()])

        prompt = f"""
YouTube 콘텐츠 아이디어를 생성해주세요.

입력 정보:
- 키워드: {keywords_str}
- 신호: {signals_str}
- 스타일: {request.style}

요구사항:
1. 제목 3-5개 (20-35자, 이모지 최대 1개, 낚시성 금지)
2. 태그 5-10개 (#으로 시작, 핵심 키워드 포함)
3. 스크립트 구조 (Hook, Body, CTA)

JSON 형태로 응답:
{{
  "titles": ["제목1", "제목2", "제목3"],
  "tags": ["#태그1", "#태그2", "#태그3", "#태그4", "#태그5"],
  "script_beats": {{
    "hook": "시청자 관심을 끄는 첫 15초 내용",
    "body": "핵심 정보를 전달하는 메인 내용",
    "cta": "구독과 좋아요를 유도하는 마무리"
  }}
}}

주의사항:
- 사실 기반으로 작성
- 과도한 과장 금지
- 한국어 사용
- 트렌드에 맞는 자연스러운 표현
"""
        return prompt

    def _parse_response(self, response_data: Dict[str, Any], trace_id: str, attempt: int) -> IdeaResponse:
        """Parse Claude API response and validate"""
        try:
            content = response_data["content"][0]["text"]

            # Extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = content[json_start:json_end]
            parsed_data = json.loads(json_str)

            # Validate with Pydantic
            idea_response = IdeaResponse(**parsed_data)

            return idea_response

        except Exception as e:
            logger.error(f"Failed to parse response: {e}", extra={
                "trace_id": trace_id,
                "attempt": attempt + 1,
                "response_content": response_data.get("content", [{}])[0].get("text", "")[:200]
            })
            raise