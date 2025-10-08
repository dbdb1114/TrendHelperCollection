"""Common test fixtures for all test modules"""
import pytest
from datetime import datetime, timezone
import pandas as pd
import numpy as np


@pytest.fixture
def sample_velocity_data():
    """Sample velocity calculation data with edge cases"""
    return pd.DataFrame([
        # Normal cases
        {"video_id": "v1", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 1000},
        {"video_id": "v1", "captured_at": datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc), "view_count": 1100},
        {"video_id": "v1", "captured_at": datetime(2025, 1, 1, 10, 2, tzinfo=timezone.utc), "view_count": 1250},

        # Δt=0 case (same timestamp)
        {"video_id": "v2", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 2000},
        {"video_id": "v2", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 2100},

        # Negative delta (view count decrease)
        {"video_id": "v3", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 3000},
        {"video_id": "v3", "captured_at": datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc), "view_count": 2900},

        # Outlier case
        {"video_id": "v4", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 100},
        {"video_id": "v4", "captured_at": datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc), "view_count": 100000},
    ])


@pytest.fixture
def guardrail_test_cases():
    """Test cases for guardrail validation"""
    return {
        "valid_titles": [
            "아이폰17 새로운 기능들과 총정리 리뷰분석",  # 20+ chars
            "이번 주 가장 핫한 테크 뉴스들 모음정리",  # 20+ chars
            "전문가가 분석하는 AI 트렌드 전망과 예측"  # 20+ chars
        ],
        "invalid_titles": {
            "too_short": ["짧은제목"],
            "too_long": ["매우매우매우매우매우매우매우매우매우매우매우매우매우매우길고긴제목으로테스트하는것입니다"],
            "too_many_emojis": ["😀😁😂🤣 여러 이모지가 포함된 제목"],
            "clickbait": ["절대 믿을 수 없는 충격적인 결과!!! 클릭해보세요!!"]
        },
        "valid_tags": ["#아이폰17", "#리뷰", "#테크", "#정보", "#분석"],
        "invalid_tags": ["#" * 50, "no_hash", "#민감정보포함"]
    }


@pytest.fixture
def sample_script_beats():
    """Sample script beats for testing"""
    return {
        "valid": {
            "hook": "흥미로운 도입부로 시청자의 관심을 끌어보겠습니다",
            "body": "본문에서는 핵심 내용을 자세히 설명하고 유용한 정보를 제공합니다. 데이터와 사실을 바탕으로 객관적인 분석을 진행합니다",
            "cta": "도움이 되셨다면 구독과 좋아요 부탁드려요"
        },
        "invalid": {
            "too_short": {
                "hook": "짧음",
                "body": "짧은내용",
                "cta": "구독"
            },
            "missing_fields": {
                "hook": "도입부만 있는 경우"
                # body and cta missing
            }
        }
    }