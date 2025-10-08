"""Abstract model client interface for idea generation"""
import time
from abc import ABC, abstractmethod
from typing import Dict, Any
from generation.schemas.idea import IdeaRequest, IdeaResponse

class IdeaModelClient(ABC):
    """Abstract base class for idea generation model clients"""

    @abstractmethod
    def generate_ideas(self, request: IdeaRequest, trace_id: str) -> IdeaResponse:
        """Generate content ideas from request"""
        pass

class StubModelClient(IdeaModelClient):
    """Stub implementation for testing without real API calls"""

    def generate_ideas(self, request: IdeaRequest, trace_id: str) -> IdeaResponse:
        """Generate stub ideas for testing"""
        time.sleep(0.1)  # Simulate API call

        # Generate guardrail-compliant content
        keyword = request.keywords[0] if request.keywords else "트렌드"

        return IdeaResponse(
            titles=[
                f"{keyword} 최신 정보와 전문가 분석 결과 총정리",
                f"이번 주 {keyword} 주요 동향과 핵심 포인트 살펴보기",
                f"{keyword} 관련 소식과 향후 전망 완벽 분석",
                f"전문가가 말하는 {keyword} 트렌드와 시장 분석"
            ],
            tags=[f"#{kw}" for kw in request.keywords[:3]] + ["#분석", "#정보", "#트렌드", "#리뷰"],
            script_beats={
                "hook": f"안녕하세요! 오늘은 {keyword}에 대한 흥미로운 소식을 가져왔습니다.",
                "body": f"{keyword}의 최신 동향과 관련 정보를 자세히 살펴보고, 여러분이 알아야 할 핵심 포인트들을 정리해드리겠습니다. 전문가들의 의견과 데이터를 바탕으로 객관적인 분석을 제공합니다.",
                "cta": "도움이 되셨다면 구독과 좋아요 부탁드려요!"
            },
            metadata={"model": "stub-client", "safety_flags": []}
        )