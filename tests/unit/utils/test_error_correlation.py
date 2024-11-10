import pytest
import time
from social_integrator.utils.error_correlation import ErrorCorrelationAnalyzer

def test_error_correlation_basic():
    """Test basic error correlation functionality."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.monotonic()
    
    # Add sequence of errors
    analyzer.add_error("timeout", current_time)
    analyzer.add_error("timeout", current_time + 0.1)
    
    # Check correlation score
    score = analyzer.get_correlation_score()
    assert score > 0.5  # High correlation due to repeated errors
    
    # Check dominant error
    assert analyzer.get_dominant_error() == "timeout"

def test_error_window_management():
    """Test error window size management."""
    window_size = 3
    analyzer = ErrorCorrelationAnalyzer(window_size=window_size)
    current_time = time.monotonic()
    
    # Add more errors than window size
    errors = ["timeout", "network", "rate_limit", "timeout", "network"]
    for i, error in enumerate(errors):
        analyzer.add_error(error, current_time + i * 0.1)
    
    # Verify window size is maintained
    assert len(analyzer.error_window) == window_size
    
    # Verify only recent errors are considered
    recent_errors = [e[0] for e in analyzer.error_window]
    assert recent_errors == errors[-window_size:]

def test_error_pattern_detection():
    """Test detection of error patterns."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.monotonic()
    
    # Add alternating error pattern
    pattern = ["timeout", "network"] * 3
    for i, error in enumerate(pattern):
        analyzer.add_error(error, current_time + i * 0.1)
    
    # Get error patterns
    patterns = analyzer.get_error_patterns()
    
    # Verify patterns
    assert ("timeout", "network") in patterns
    assert ("network", "timeout") in patterns
    
    # Score should reflect regular pattern
    score = analyzer.get_correlation_score()
    assert 0 < score < 1  # Some correlation, but not perfect

def test_error_distribution():
    """Test error type distribution analysis."""
    analyzer = ErrorCorrelationAnalyzer(window_size=10)
    current_time = time.monotonic()
    
    # Add errors with known distribution
    errors = ["timeout"] * 4 + ["network"] * 2 + ["rate_limit"]
    for i, error in enumerate(errors):
        analyzer.add_error(error, current_time + i * 0.1)
    
    distribution = analyzer.get_error_distribution()
    
    # Verify distribution
    assert distribution["timeout"] == 4/7  # 4 out of 7 errors
    assert distribution["network"] == 2/7  # 2 out of 7 errors
    assert distribution["rate_limit"] == 1/7  # 1 out of 7 errors

def test_correlation_score_evolution():
    """Test how correlation score evolves with different patterns."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.monotonic()
    scores = []
    
    # Test different error sequences
    sequences = [
        ["timeout"] * 3,                    # High correlation
        ["network", "timeout"] * 2,         # Pattern correlation
        ["rate_limit", "network", "timeout"] # Low correlation
    ]
    
    for sequence in sequences:
        for error in sequence:
            analyzer.add_error(error, current_time)
            current_time += 0.1
            scores.append(analyzer.get_correlation_score())
    
    # Verify score evolution
    assert scores[2] > 0.8  # High correlation for repeated errors
    assert scores[-1] < scores[2]  # Lower correlation for mixed errors

def test_error_cleanup():
    """Test cleanup of old errors."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.monotonic()
    
    # Add old errors
    for i in range(3):
        analyzer.add_error("old_error", current_time - 3600)  # 1 hour old
    
    # Add recent errors
    for i in range(2):
        analyzer.add_error("new_error", current_time)
    
    # Get dominant error - should only consider recent errors
    assert analyzer.get_dominant_error() == "new_error"

def test_empty_analyzer():
    """Test analyzer behavior with no errors."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    
    assert analyzer.get_correlation_score() == 0.0
    assert analyzer.get_dominant_error() is None
    assert analyzer.get_error_patterns() == {}
    assert analyzer.get_error_distribution() == {}

def test_single_error():
    """Test analyzer behavior with single error."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.monotonic()
    
    analyzer.add_error("timeout", current_time)
    
    assert analyzer.get_correlation_score() == 0.0  # No correlation with single error
    assert analyzer.get_dominant_error() == "timeout"
    assert analyzer.get_error_patterns() == {}  # No patterns with single error
    assert analyzer.get_error_distribution() == {"timeout": 1.0}

def test_pattern_strength():
    """Test pattern strength calculation."""
    analyzer = ErrorCorrelationAnalyzer(window_size=6)
    current_time = time.monotonic()
    
    # Add strong pattern: A-B-A-B-A-B
    pattern = ["A", "B"] * 3
    for i, error in enumerate(pattern):
        analyzer.add_error(error, current_time + i * 0.1)
    
    patterns = analyzer.get_error_patterns()
    
    # Should have strong A->B and B->A patterns
    assert patterns[("A", "B")] > 0.3
    assert patterns[("B", "A")] > 0.3

def test_correlation_with_gaps():
    """Test correlation analysis with time gaps between errors."""
    analyzer = ErrorCorrelationAnalyzer(window_size=5)
    current_time = time.monotonic()
    
    # Add errors with varying time gaps
    analyzer.add_error("timeout", current_time)
    analyzer.add_error("timeout", current_time + 1.0)  # 1 second gap
    analyzer.add_error("timeout", current_time + 10.0)  # 9 second gap
    
    score = analyzer.get_correlation_score()
    assert score > 0  # Should still show correlation despite gaps
