import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

class RetryMetricsCollector:
    """Collects and analyzes retry-related metrics."""
    
    def __init__(self):
        self.retry_counts = {}
        self.response_times = {}
        self.error_types = {}
        self.success_rate = 1.0
        self.total_requests = 0
        self.failed_requests = 0
        self.retry_intervals = []
        self.consecutive_failures = 0
        self.last_success_time = None

    def record_attempt(self, request_id: str, response_time: float, 
                      error_type: Optional[str] = None, retry_count: int = 0):
        """Record metrics for an attempt."""
        self.retry_counts[request_id] = retry_count
        self.response_times.setdefault(request_id, []).append(response_time)
        
        if error_type:
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
            self.failed_requests += 1
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
            self.last_success_time = time.time()
            
        self.total_requests += 1
        self.success_rate = 1 - (self.failed_requests / self.total_requests)

    def record_retry_interval(self, interval: float):
        """Record time between retries."""
        self.retry_intervals.append(interval)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "success_rate": self.success_rate,
            "avg_retries": (sum(self.retry_counts.values()) / 
                          len(self.retry_counts) if self.retry_counts else 0),
            "avg_response_time": (sum(sum(times) / len(times) 
                                for times in self.response_times.values()) / 
                                len(self.response_times) if self.response_times else 0),
            "error_distribution": self.error_types,
            "avg_retry_interval": (sum(self.retry_intervals) / 
                                 len(self.retry_intervals) if self.retry_intervals else 0),
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success": (time.time() - self.last_success_time 
                                      if self.last_success_time else None)
        }

@pytest.mark.asyncio
async def test_basic_metrics_collection():
    """Test basic metrics collection functionality."""
    collector = RetryMetricsCollector()
    
    # Simulate successful request
    collector.record_attempt("req1", 0.1)
    
    # Simulate failed request with retry
    collector.record_attempt("req2", 0.2, error_type="timeout", retry_count=1)
    collector.record_retry_interval(1.0)
    collector.record_attempt("req2", 0.3)
    
    metrics = collector.get_metrics()
    
    assert metrics["success_rate"] == 0.75  # 3 attempts, 1 failure
    assert metrics["avg_retries"] == 0.5    # 1 retry across 2 requests
    assert 0.1 < metrics["avg_response_time"] < 0.3
    assert metrics["error_distribution"]["timeout"] == 1
    assert metrics["avg_retry_interval"] == 1.0

@pytest.mark.asyncio
async def test_error_pattern_tracking():
    """Test tracking of error patterns and distributions."""
    collector = RetryMetricsCollector()
    
    # Simulate various error scenarios
    scenarios = [
        ("req1", 0.1, "timeout"),
        ("req2", 0.2, "network"),
        ("req3", 0.1, "timeout"),
        ("req4", 0.2, None),      # Success
        ("req5", 0.1, "timeout")
    ]
    
    for req_id, time, error in scenarios:
        collector.record_attempt(req_id, time, error)
        
    metrics = collector.get_metrics()
    
    assert metrics["error_distribution"]["timeout"] == 3
    assert metrics["error_distribution"]["network"] == 1
    assert metrics["success_rate"] == 0.2  # 1 success out of 5

@pytest.mark.asyncio
async def test_retry_interval_analysis():
    """Test analysis of retry intervals."""
    collector = RetryMetricsCollector()
    
    # Record varying retry intervals
    intervals = [0.1, 0.2, 0.4, 0.8]
    for interval in intervals:
        collector.record_retry_interval(interval)
        
    metrics = collector.get_metrics()
    
    assert metrics["avg_retry_interval"] == sum(intervals) / len(intervals)

@pytest.mark.asyncio
async def test_consecutive_failure_tracking():
    """Test tracking of consecutive failures."""
    collector = RetryMetricsCollector()
    
    # Simulate sequence of failures followed by success
    collector.record_attempt("req1", 0.1, "timeout")
    collector.record_attempt("req2", 0.1, "network")
    collector.record_attempt("req3", 0.1, "timeout")
    assert collector.consecutive_failures == 3
    
    collector.record_attempt("req4", 0.1)  # Success
    assert collector.consecutive_failures == 0

@pytest.mark.asyncio
async def test_metrics_with_real_requests(twitter_api, social_post):
    """Test metrics collection with simulated API requests."""
    collector = RetryMetricsCollector()
    
    # Mock session with varying responses
    mock_session = AsyncMock()
    request_count = 0
    
    async def mock_response():
        nonlocal request_count
        request_count += 1
        
        if request_count <= 2:  # First 2 fail with timeout
            collector.record_attempt(f"req{request_count}", 0.2, "timeout", 
                                  retry_count=request_count-1)
            raise asyncio.TimeoutError()
        elif request_count == 3:  # Third fails with network error
            collector.record_attempt(f"req{request_count}", 0.3, "network", 
                                  retry_count=request_count-1)
            raise aiohttp.ClientError("Network error")
        else:  # Then succeed
            collector.record_attempt(f"req{request_count}", 0.1)
            return MagicMock(
                status=200,
                ok=True,
                json=AsyncMock(return_value={"data": {"id": "123"}})
            )
    
    mock_session.post.side_effect = lambda *args, **kwargs: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response())
    )()

    with patch.object(twitter_api, "session", mock_session):
        # Make requests and collect metrics
        for _ in range(4):
            try:
                await twitter_api.post(social_post)
            except Exception:
                collector.record_retry_interval(0.5)
                
        metrics = collector.get_metrics()
        
        # Verify metrics
        assert metrics["success_rate"] == 0.25  # 1 success out of 4
        assert "timeout" in metrics["error_distribution"]
        assert "network" in metrics["error_distribution"]
        assert metrics["consecutive_failures"] == 0  # Last request succeeded
        assert metrics["time_since_last_success"] is not None

@pytest.mark.asyncio
async def test_response_time_analysis():
    """Test analysis of response time patterns."""
    collector = RetryMetricsCollector()
    
    # Simulate requests with varying response times
    scenarios = [
        ("req1", 0.1),    # Fast
        ("req2", 0.5),    # Slow
        ("req3", 0.2),    # Medium
        ("req4", 0.1)     # Fast
    ]
    
    for req_id, time in scenarios:
        collector.record_attempt(req_id, time)
        
    metrics = collector.get_metrics()
    
    assert 0.1 < metrics["avg_response_time"] < 0.5
    assert all(0.1 <= sum(times)/len(times) <= 0.5 
              for times in collector.response_times.values())
