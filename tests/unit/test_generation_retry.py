"""Unit tests for generation retry logic and failure handling"""
import pytest
from unittest.mock import Mock, patch
from generation.clients.model_client import StubModelClient
from generation.schemas.idea import IdeaRequest, IdeaResponse, ScriptBeats


class TestGenerationRetryLogic:
    """Test retry logic for generation failures"""

    def test_successful_generation_no_retry(self):
        """Test successful generation without retry"""
        client = StubModelClient()
        request = IdeaRequest(
            keywords=["테스트"],
            signals={"views_per_min": 100.0}
        )

        response = client.generate_ideas(request, "test_trace")

        assert isinstance(response, IdeaResponse)
        assert len(response.titles) >= 3
        assert len(response.tags) >= 5

    def test_guardrail_compliance_verification(self):
        """Test that StubModelClient generates guardrail-compliant content"""
        client = StubModelClient()
        request = IdeaRequest(
            keywords=["테스트키워드"],
            signals={"views_per_min": 100.0}
        )

        response = client.generate_ideas(request, "test_trace")

        # Verify response passes guardrails
        from generation.guardrails.rules import validate_titles, validate_tags, validate_script_beats

        title_violations = validate_titles(response.titles)
        tag_violations = validate_tags(response.tags)
        script_violations = validate_script_beats(response.script_beats.model_dump())

        assert len(title_violations) == 0, f"Titles should pass guardrails: {title_violations}"
        assert len(tag_violations) == 0, f"Tags should pass guardrails: {tag_violations}"
        assert len(script_violations) == 0, f"Scripts should pass guardrails: {script_violations}"

    def test_stub_client_consistency(self):
        """Test that StubModelClient produces consistent results"""
        client = StubModelClient()
        request = IdeaRequest(
            keywords=["일관성테스트"],
            signals={"views_per_min": 100.0}
        )

        # Generate multiple times
        response1 = client.generate_ideas(request, "trace1")
        response2 = client.generate_ideas(request, "trace2")

        # Should produce titles with same pattern but different content
        assert len(response1.titles) == len(response2.titles)
        assert len(response1.tags) == len(response2.tags)

        # All should include the keyword
        for title in response1.titles:
            assert "일관성테스트" in title

    def test_empty_keywords_handling(self):
        """Test handling of empty keywords"""
        client = StubModelClient()
        request = IdeaRequest(
            keywords=[],  # Empty keywords
            signals={"views_per_min": 100.0}
        )

        response = client.generate_ideas(request, "test_trace")

        # Should still generate valid content (fallback to default)
        assert isinstance(response, IdeaResponse)
        assert len(response.titles) >= 3
        assert len(response.tags) >= 5

    def test_malformed_signals_handling(self):
        """Test handling of malformed signals"""
        client = StubModelClient()

        # Missing views_per_min
        request1 = IdeaRequest(
            keywords=["테스트"],
            signals={}  # Empty signals
        )
        response1 = client.generate_ideas(request1, "test_trace")
        assert isinstance(response1, IdeaResponse)

        # Invalid signal values
        request2 = IdeaRequest(
            keywords=["테스트"],
            signals={"views_per_min": "invalid"}  # String instead of number
        )
        # Should handle gracefully (StubModelClient doesn't use signals much)
        response2 = client.generate_ideas(request2, "test_trace")
        assert isinstance(response2, IdeaResponse)

    def test_extreme_keyword_scenarios(self):
        """Test extreme keyword scenarios"""
        client = StubModelClient()

        # Very long keyword
        long_keyword = "매우긴키워드" * 20
        request = IdeaRequest(
            keywords=[long_keyword],
            signals={"views_per_min": 100.0}
        )
        response = client.generate_ideas(request, "test_trace")
        assert isinstance(response, IdeaResponse)

        # Many keywords
        many_keywords = [f"키워드{i}" for i in range(20)]
        request = IdeaRequest(
            keywords=many_keywords,
            signals={"views_per_min": 100.0}
        )
        response = client.generate_ideas(request, "test_trace")
        assert isinstance(response, IdeaResponse)

    def test_response_structure_validation(self):
        """Test that response structure is always valid"""
        client = StubModelClient()
        request = IdeaRequest(
            keywords=["구조테스트"],
            signals={"views_per_min": 100.0}
        )

        response = client.generate_ideas(request, "test_trace")

        # Verify all required fields are present
        assert hasattr(response, 'titles')
        assert hasattr(response, 'tags')
        assert hasattr(response, 'script_beats')
        assert hasattr(response, 'metadata')

        # Verify script_beats structure
        script_beats = response.script_beats
        assert hasattr(script_beats, 'hook')
        assert hasattr(script_beats, 'body')
        assert hasattr(script_beats, 'cta')

        # Verify metadata structure
        assert 'model' in response.metadata
        assert 'safety_flags' in response.metadata

    @pytest.mark.skip(reason="Future implementation - requires real model client with retry")
    def test_max_retry_limit_enforcement(self):
        """Test maximum retry limit enforcement"""
        # Mock a client that always fails guardrails
        mock_client = Mock()
        mock_client.generate_ideas.side_effect = ValueError("Guardrail violation")

        # Test that after max retries, appropriate exception is raised
        # This will be implemented when real retry logic is added
        pass

    @pytest.mark.skip(reason="Future implementation - requires real model client with retry")
    def test_retry_with_violation_feedback(self):
        """Test retry with specific violation feedback"""
        # Mock scenarios where feedback improves subsequent attempts
        # Example: first attempt fails title length, second attempt succeeds
        # This will be implemented when real retry logic is added
        pass

    @pytest.mark.skip(reason="Future implementation - requires real model client with retry")
    def test_exponential_backoff_timing(self):
        """Test exponential backoff between retries"""
        # Test timing between retry attempts
        # This will be implemented when real retry logic with timing is added
        pass

    def test_trace_id_propagation(self):
        """Test that trace_id is properly handled"""
        client = StubModelClient()
        request = IdeaRequest(
            keywords=["추적테스트"],
            signals={"views_per_min": 100.0}
        )

        trace_id = "test_trace_12345"
        response = client.generate_ideas(request, trace_id)

        # StubModelClient doesn't store trace_id, but should not error
        assert isinstance(response, IdeaResponse)

    def test_concurrent_generation_safety(self):
        """Test that concurrent generation calls are safe"""
        import threading
        import time

        client = StubModelClient()
        results = []
        errors = []

        def generate_ideas():
            try:
                request = IdeaRequest(
                    keywords=["동시성테스트"],
                    signals={"views_per_min": 100.0}
                )
                response = client.generate_ideas(request, f"trace_{threading.current_thread().ident}")
                results.append(response)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_ideas)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All should succeed without errors
        assert len(errors) == 0, f"Concurrent generation failed: {errors}"
        assert len(results) == 5
        for result in results:
            assert isinstance(result, IdeaResponse)