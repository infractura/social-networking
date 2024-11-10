import pytest
import time
from social_integrator.utils.metrics import RetryMetricsCollector

def test_basic_metrics_collection():
    """Test basic metrics collection functionality."""
    collector = RetryMetricsCollector()
    
    # Record successful request
    collector.record_attempt("req1", 0.1)
    
    # Record failed request with retry
    collector.record_attempt("req2", 0.2, error_type="timeout", retry_count=1)
    collector.record_retry_interval(1.0)
    collector.record_attempt("req2", 0.3)
    
    metrics = collector.get_metrics()
    
    assert metrics["success_rate"] == pytest.approx(0.67, abs=0.01)  # 2 successes out of 3 attempts
    assert metrics["avg_retries"] == pytest.approx(0.5, abs=0.01)    # 1 retry across 2 requests
    assert 0.1 < metrics["avg_response_time"] < 0.3
    assert metrics["error_distribution"]["timeout"] == 1
    assert metrics["avg_retry_interval"] == 1.0

def test_error_pattern_tracking():
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
    assert metrics["success_rate"] == pytest.approx(0.2, abs=0.01)  # 1 success out of 5

def test_retry_interval_analysis():
    """Test analysis of retry intervals."""
    collector = RetryMetricsCollector()
    
    # Record varying retry intervals
    intervals = [0.1, 0.2, 0.4, 0.8]
    for interval in intervals:
        collector.record_retry_interval(interval)
        
    metrics = collector.get_metrics()
    
    assert metrics["avg_retry_interval"] == pytest.approx(0.375, abs=0.01)  # (0.1 + 0.2 + 0.4 + 0.8) / 4

def test_consecutive_failure_tracking():
    """Test tracking of consecutive failures."""
    collector = RetryMetricsCollector()
    
    # Simulate sequence of failures followed by success
    collector.record_attempt("req1", 0.1, "timeout")
    collector.record_attempt("req2", 0.1, "network")
    collector.record_attempt("req3", 0.1, "timeout")
    assert collector.consecutive_failures == 3
    
    collector.record_attempt("req4", 0.1)  # Success
    assert collector.consecutive_failures == 0

def test_response_time_analysis():
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
    
    assert metrics["avg_response_time"] == pytest.approx(0.225, abs=0.01)  # (0.1 + 0.5 + 0.2 + 0.1) / 4
    assert all(0.1 <= sum(times)/len(times) <= 0.5 
              for times in collector.response_times.values())

def test_retry_distribution():
    """Test distribution of retry counts."""
    collector = RetryMetricsCollector()
    
    # Record attempts with different retry counts
    collector.record_attempt("req1", 0.1, retry_count=0)
    collector.record_attempt("req2", 0.1, retry_count=2)
    collector.record_attempt("req3", 0.1, retry_count=1)
    collector.record_attempt("req4", 0.1, retry_count=2)
    
    distribution = collector.get_retry_distribution()
    
    assert distribution[0] == 1  # One request with no retries
    assert distribution[1] == 1  # One request with 1 retry
    assert distribution[2] == 2  # Two requests with 2 retries

def test_time_since_last_success():
    """Test tracking of time since last success."""
    collector = RetryMetricsCollector()
    start_time = time.monotonic()
    
    # Record some failures
    collector.record_attempt("req1", 0.1, "timeout")
    collector.record_attempt("req2", 0.1, "network")
    
    # Record success
    time.sleep(0.1)  # Small delay
    collector.record_attempt("req3", 0.1)
    
    metrics = collector.get_metrics()
    assert metrics["time_since_last_success"] is not None
    assert metrics["time_since_last_success"] < 0.2  # Should be close to our sleep time

def test_empty_metrics():
    """Test metrics when no data is collected."""
    collector = RetryMetricsCollector()
    metrics = collector.get_metrics()
    
    assert metrics["success_rate"] == 1.0  # No failures
    assert metrics["avg_retries"] == 0
    assert metrics["avg_response_time"] == 0
    assert metrics["error_distribution"] == {}
    assert metrics["avg_retry_interval"] == 0
    assert metrics["consecutive_failures"] == 0
    assert metrics["time_since_last_success"] is None

def test_request_history():
    """Test request history tracking."""
    collector = RetryMetricsCollector()
    
    # Record sequence of requests
    collector.record_attempt("req1", 0.1)
    collector.record_attempt("req1", 0.2, "timeout", retry_count=1)
    collector.record_attempt("req1", 0.3)
    
    # Verify history
    assert len(collector._request_history) == 3
    assert collector._request_history[0]["retry_count"] == 0
    assert collector._request_history[1]["error_type"] == "timeout"
    assert collector._request_history[1]["retry_count"] == 1
    assert collector._request_history[2]["retry_count"] == 0

def test_error_distribution_calculation():
    """Test calculation of error type distribution."""
    collector = RetryMetricsCollector()
    
    # Record errors with known distribution
    errors = ["timeout"] * 4 + ["network"] * 2 + ["rate_limit"]
    for i, error in enumerate(errors):
        collector.record_attempt(f"req{i}", 0.1, error)
    
    distribution = collector.get_error_distribution()
    
    assert distribution["timeout"] == pytest.approx(4/7, abs=0.01)  # 4 out of 7 errors
    assert distribution["network"] == pytest.approx(2/7, abs=0.01)  # 2 out of 7 errors
    assert distribution["rate_limit"] == pytest.approx(1/7, abs=0.01)  # 1 out of 7 errors
