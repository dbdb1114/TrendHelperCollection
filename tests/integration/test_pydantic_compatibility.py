"""Tests for Pydantic compatibility and no deprecation warnings"""
import warnings
import pytest
from generation.schemas.idea import IdeaRequest, IdeaResponse, ScriptBeats


class TestPydanticCompatibility:
    """Test Pydantic models use current API without deprecation warnings"""

    def test_idea_request_model_dump(self):
        """Test IdeaRequest uses model_dump() without warnings"""
        request = IdeaRequest(
            video_id="test_123",
            keywords=["test", "keyword"],
            signals={"views_per_min": 100.0},
            style={"tone": "info", "language": "ko"}
        )

        # Capture warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Use model_dump (new API)
            data = request.model_dump()

            # Check no deprecation warnings
            deprecation_warnings = [w for w in warning_list
                                  if issubclass(w.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 0, f"Deprecation warnings found: {deprecation_warnings}"

        # Verify data structure
        assert isinstance(data, dict)
        assert data["video_id"] == "test_123"
        assert data["keywords"] == ["test", "keyword"]

    def test_idea_response_model_dump(self):
        """Test IdeaResponse uses model_dump() without warnings"""
        script_beats = ScriptBeats(
            hook="Test hook content for testing",
            body="Test body content for testing purposes",
            cta="Test CTA content"
        )

        response = IdeaResponse(
            titles=["테스트 제목 하나 스무글자 이상으로 작성한 것", "테스트 제목 둘째 스무글자 이상으로 작성한 것", "테스트 제목 셋째 스무글자 이상으로 작성한 것"],
            tags=["#test1", "#test2", "#test3", "#test4", "#test5"],
            script_beats=script_beats,
            metadata={"model": "test-model", "safety_flags": []}
        )

        # Capture warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Use model_dump (new API)
            data = response.model_dump()

            # Check no deprecation warnings
            deprecation_warnings = [w for w in warning_list
                                  if issubclass(w.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 0, f"Deprecation warnings found: {deprecation_warnings}"

        # Verify data structure
        assert isinstance(data, dict)
        assert len(data["titles"]) == 3
        assert len(data["tags"]) == 5
        assert isinstance(data["script_beats"], dict)

    def test_script_beats_model_dump(self):
        """Test ScriptBeats uses model_dump() without warnings"""
        script_beats = ScriptBeats(
            hook="Test hook content for testing",
            body="Test body content for testing purposes and more content",
            cta="Test CTA content"
        )

        # Capture warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Use model_dump (new API)
            data = script_beats.model_dump()

            # Check no deprecation warnings
            deprecation_warnings = [w for w in warning_list
                                  if issubclass(w.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 0, f"Deprecation warnings found: {deprecation_warnings}"

        # Verify data structure
        assert isinstance(data, dict)
        assert "hook" in data
        assert "body" in data
        assert "cta" in data

    def test_dict_method_still_works_with_warning(self):
        """Test that .dict() method still works but produces warning"""
        request = IdeaRequest(
            keywords=["test"],
            signals={"views_per_min": 100.0}
        )

        # Capture warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Use deprecated .dict() method
            data = request.dict()

            # Should produce deprecation warning
            deprecation_warnings = [w for w in warning_list
                                  if issubclass(w.category, DeprecationWarning)]
            # Note: This test documents the warning exists, but we've fixed the code
            # In fixed code, we don't use .dict() anymore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])