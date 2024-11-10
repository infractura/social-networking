import pytest
import random
from social_integrator.utils.backoff import AdaptiveBackoffManager

def test_backoff_basic():
    """Test basic backoff functionality."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # First attempt should use base delay
    delay = backoff.get_delay(0)
    assert 0.09 <= delay <= 0.11  # Allow for jitter
    
    # Second attempt should double the delay
    delay = backoff.get_delay(1)
    assert 0.18 <= delay <= 0.22  # Allow for jitter

def test_backoff_max_delay():
    """Test that backoff respects maximum delay."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=0.5)
    
    # Try many attempts to ensure we don't exceed max_delay
    for attempt in range(10):
        delay = backoff.get_delay(attempt)
        assert delay <= 0.5

def test_backoff_jitter():
    """Test that jitter is applied correctly."""
    random.seed(42)  # For reproducible tests
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    backoff.jitter_factor = 0.1  # 10% jitter
    
    # Get multiple delays for the same attempt
    delays = [backoff.get_delay(1) for _ in range(10)]
    
    # Verify delays are different (due to jitter)
    assert len(set(delays)) > 1
    
    # Verify delays are within expected range
    base_delay = 0.2  # Second attempt should be 2 * base_delay
    for delay in delays:
        assert base_delay * 0.9 <= delay <= base_delay * 1.1

def test_backoff_error_type_adjustment():
    """Test backoff adjustment based on error type."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Rate limit errors should increase delay more
    rate_limit_delay = backoff.get_delay(1, error_type="rate_limit")
    normal_delay = backoff.get_delay(1)
    assert rate_limit_delay > normal_delay
    
    # Record multiple rate limit errors
    for _ in range(4):
        backoff.get_delay(1, error_type="rate_limit")
    
    # Verify increased delay for persistent rate limits
    final_delay = backoff.get_delay(1, error_type="rate_limit")
    assert final_delay > rate_limit_delay

def test_backoff_success_adaptation():
    """Test backoff adaptation based on success/failure patterns."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    initial_jitter = backoff.jitter_factor
    
    # Record multiple successes
    for _ in range(5):
        backoff.record_result(True)
    
    # Jitter should increase after consistent success
    assert backoff.jitter_factor > initial_jitter
    
    # Record multiple failures
    for _ in range(3):
        backoff.record_result(False)
    
    # Jitter should decrease after consistent failures
    assert backoff.jitter_factor < initial_jitter

def test_backoff_stats():
    """Test backoff statistics collection."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Get delays for different attempts
    delays = [backoff.get_delay(i) for i in range(3)]
    
    stats = backoff.get_stats()
    assert stats["min_delay"] == pytest.approx(min(delays), abs=0.01)
    assert stats["max_delay"] == pytest.approx(max(delays), abs=0.01)
    assert stats["avg_delay"] == pytest.approx(sum(delays) / len(delays), abs=0.01)
    assert stats["current_jitter"] == backoff.jitter_factor

def test_backoff_reset():
    """Test backoff reset functionality."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Make some attempts and record results
    backoff.get_delay(1, error_type="timeout")
    backoff.record_result(False)
    
    # Reset backoff
    backoff.reset()
    
    # Verify reset state
    assert backoff.success_streak == 0
    assert backoff.failure_streak == 0
    assert backoff.jitter_factor == 0.1
    assert len(backoff.delay_history) == 0
    assert len(backoff.error_counts) == 0
    assert backoff.last_backoff is None

def test_backoff_error_tracking():
    """Test error type tracking and analysis."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Record different types of errors
    error_types = ["timeout", "network", "rate_limit", "timeout"]
    for error_type in error_types:
        backoff.get_delay(1, error_type=error_type)
    
    # Verify error counts
    assert backoff.error_counts["timeout"] == 2
    assert backoff.error_counts["network"] == 1
    assert backoff.error_counts["rate_limit"] == 1

def test_backoff_delay_sequence():
    """Test sequence of delays with exponential backoff."""
    random.seed(42)  # For reproducible tests
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    backoff.jitter_factor = 0  # Disable jitter for predictable testing
    
    # Get sequence of delays
    delays = [backoff.get_delay(attempt) for attempt in range(5)]
    
    # Verify exponential increase
    assert delays[0] == pytest.approx(0.1, abs=0.01)  # ~0.1
    assert delays[1] == pytest.approx(0.2, abs=0.01)  # ~0.2
    assert delays[2] == pytest.approx(0.4, abs=0.01)  # ~0.4
    assert delays[3] == pytest.approx(0.8, abs=0.01)  # ~0.8
    assert delays[4] == pytest.approx(1.0, abs=0.01)  # Max delay

def test_backoff_combined_strategy():
    """Test combined backoff strategy with all features."""
    random.seed(42)  # For reproducible tests
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Simulate a sequence of events
    scenarios = [
        (0, "timeout", False),    # Initial timeout
        (1, "timeout", False),    # Second timeout
        (2, None, True),          # Success
        (1, "rate_limit", False), # Rate limit error
        (2, None, True),          # Success
        (1, None, True),          # Success
    ]
    
    delays = []
    for attempt, error_type, success in scenarios:
        delay = backoff.get_delay(attempt, error_type=error_type)
        delays.append(delay)
        backoff.record_result(success)
    
    # Verify behavior
    assert len(delays) == len(scenarios)
    assert all(0.09 <= d <= 1.0 for d in delays)  # All delays within bounds
    assert backoff.success_streak > 0
    assert backoff.failure_streak == 0
