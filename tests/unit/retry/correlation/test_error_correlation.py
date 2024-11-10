import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Dict, Any

class ErrorCorrelationAnalyzer:
    """Analyzes error patterns to detect correlated failures."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.error_window = []
        self.error_patterns = {}
        self.correlation_scores = []

    def add_error(self, error_type: str, timestamp: float):
        """Add error to window and analyze patterns."""
        self.error_window.append((error_type, timestamp))
        if len(self.error_window) > self.window_size:
            self.error_window.pop(0)

        # Analyze error patterns
        if len(self.error_window) >= 2:
            pattern = tuple(e[0] for e in self.error_window[-2:])
            self.error_patterns[pattern] = self.error_patterns.get(pattern, 0) + 1

    def get_correlation_score(self) -> float:
        """Calculate error correlation score."""
        if not self.error_patterns:
            return 0.0

        total_patterns = sum(self.error_patterns.values())
        repeated_patterns = sum(
            count for pattern, count in self.error_patterns.items()
            if pattern[0] == pattern[1]
        )
        score = repeated_patterns / total_patterns
        self.correlation_scores.append(score)
        return score

    def get_dominant_error(self) -> Optional[str]:
        """Get most frequent error type in current window."""
        if not self.error_window:
            return None

        error_counts = {}
        for error_type, _ in self.error_window:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return max(error_counts.items(), key=lambda x: x[1])[0]

@pytest.mark.asyncio
async def test_error_correlation_basic():
    """Test basic error correlation detection."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.time()
    
    # Add sequence of errors
    errors = [
        "timeout", "timeout",  # Correlated timeouts
        "network", "network",  # Correlated network errors
        "rate_limit"          # Single rate limit
    ]
    
    for i, error in enumerate(errors):
        analyzer.add_error(error, current_time + i)
        
    # Check correlation score
    score = analyzer.get_correlation_score()
    assert score > 0.5  # High correlation due to repeated errors
    
    # Check dominant error
    dominant = analyzer.get_dominant_error()
    assert dominant in ["timeout", "network"]  # Both appear twice

@pytest.mark.asyncio
async def test_error_pattern_detection():
    """Test detection of error patterns over time."""
    analyzer = ErrorCorrelationAnalyzer(window_size=4)
    current_time = time.time()
    
    # Add alternating error pattern
    pattern = ["timeout", "network"] * 3
    
    for i, error in enumerate(pattern):
        analyzer.add_error(error, current_time + i)
        
    # Verify pattern detection
    assert ("timeout", "network") in analyzer.error_patterns
    assert ("network", "timeout") in analyzer.error_patterns
    
    # Score should reflect regular pattern
    score = analyzer.get_correlation_score()
    assert score > 0  # Some correlation due to pattern
    assert score < 1  # But not perfect correlation

@pytest.mark.asyncio
async def test_error_window_management():
    """Test error window size management."""
    window_size = 3
    analyzer = ErrorCorrelationAnalyzer(window_size=window_size)
    current_time = time.time()
    
    # Add more errors than window size
    errors = ["timeout", "network", "rate_limit", "timeout", "network"]
    
    for i, error in enumerate(errors):
        analyzer.add_error(error, current_time + i)
        
    # Verify window size is maintained
    assert len(analyzer.error_window) == window_size
    
    # Verify only recent errors are considered
    recent_errors = [e[0] for e in analyzer.error_window]
    assert recent_errors == errors[-window_size:]

@pytest.mark.asyncio
async def test_correlation_score_evolution():
    """Test how correlation score evolves with different patterns."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.time()
    scores = []
    
    # Test different error sequences
    sequences = [
        ["timeout"] * 3,                    # High correlation
        ["network", "timeout"] * 2,         # Pattern correlation
        ["rate_limit", "network", "timeout"] # Low correlation
    ]
    
    for sequence in sequences:
        for i, error in enumerate(sequence):
            analyzer.add_error(error, current_time + len(scores) + i)
            scores.append(analyzer.get_correlation_score())
    
    # Verify score evolution
    assert scores[2] > 0.8  # High correlation for repeated errors
    assert scores[-1] < scores[2]  # Lower correlation for mixed errors

@pytest.mark.asyncio
async def test_error_correlation_with_requests(twitter_api, social_post):
    """Test error correlation analysis with simulated requests."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    
    # Mock session with error patterns
    mock_session = AsyncMock()
    request_count = 0
    
    async def mock_response():
        nonlocal request_count
        current_time = time.time()
        
        if request_count < 3:  # First 3: timeouts
            analyzer.add_error("timeout", current_time)
            request_count += 1
            raise asyncio.TimeoutError()
        elif request_count < 5:  # Next 2: network errors
            analyzer.add_error("network", current_time)
            request_count += 1
            raise aiohttp.ClientError("Network error")
        else:  # Then success
            request_count += 1
            return MagicMock(
                status=200,
                ok=True,
                json=AsyncMock(return_value={"data": {"id": "123"}})
            )
    
    mock_session.post.side_effect = lambda *args, **kwargs: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response())
    )()

    with patch.object(twitter_api, "session", mock_session):
        # Make requests and track correlation
        correlation_scores = []
        dominant_errors = []
        
        for _ in range(6):
            try:
                await twitter_api.post(social_post)
            except Exception:
                pass
            
            correlation_scores.append(analyzer.get_correlation_score())
            dominant_errors.append(analyzer.get_dominant_error())
        
        # Verify error analysis
        assert max(correlation_scores) > 0.5  # High correlation during timeout burst
        assert "timeout" in dominant_errors  # Timeout should be dominant initially
        assert "network" in dominant_errors  # Network errors should be dominant later
