import time
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

class ErrorCorrelationAnalyzer:
    """Analyzes error patterns to detect correlated failures."""
    
    def __init__(self, window_size: int = 10):
        """Initialize analyzer.
        
        Args:
            window_size: Maximum number of errors to track
        """
        self.window_size = window_size
        self.error_window: List[Tuple[str, float]] = []
        self.error_patterns: Dict[Tuple[str, str], int] = defaultdict(int)
        self.correlation_scores: List[float] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self._cleanup_threshold = 3600  # 1 hour in seconds
    
    def _cleanup_old_errors(self, current_time: float) -> None:
        """Remove errors older than cleanup threshold."""
        cutoff = current_time - self._cleanup_threshold
        self.error_window = [(e, t) for e, t in self.error_window if t > cutoff]
    
    def add_error(self, error_type: str, timestamp: float) -> None:
        """Add error to window and analyze patterns.
        
        Args:
            error_type: Type of error
            timestamp: Time of error occurrence
        """
        self._cleanup_old_errors(timestamp)
        
        # Add to window
        self.error_window.append((error_type, timestamp))
        if len(self.error_window) > self.window_size:
            self.error_window.pop(0)
        
        # Update error counts
        self.error_counts[error_type] += 1
        
        # Analyze patterns
        if len(self.error_window) >= 2:
            # Look at consecutive errors
            for i in range(len(self.error_window) - 1):
                pattern = (self.error_window[i][0], self.error_window[i + 1][0])
                self.error_patterns[pattern] += 1
    
    def get_correlation_score(self) -> float:
        """Calculate error correlation score.
        
        Returns:
            Score between 0 and 1, where higher values indicate stronger correlation
        """
        if not self.error_patterns:
            return 0.0
        
        total_patterns = sum(self.error_patterns.values())
        if total_patterns == 0:
            return 0.0
        
        # Calculate repeated patterns (same error type in sequence)
        repeated_patterns = sum(
            count for (error1, error2), count in self.error_patterns.items()
            if error1 == error2
        )
        
        # Calculate pattern strength
        unique_patterns = len(set(self.error_patterns.keys()))
        pattern_ratio = 1.0 / unique_patterns if unique_patterns > 0 else 0.0
        
        # Combine metrics
        correlation = (repeated_patterns / total_patterns) + pattern_ratio
        normalized_score = min(1.0, correlation / 2.0)
        
        self.correlation_scores.append(normalized_score)
        return normalized_score
    
    def get_dominant_error(self) -> Optional[str]:
        """Get most frequent error type in current window.
        
        Returns:
            Most frequent error type or None if no errors
        """
        if not self.error_window:
            return None
        
        error_counts: Dict[str, int] = defaultdict(int)
        for error_type, _ in self.error_window:
            error_counts[error_type] += 1
        
        return max(error_counts.items(), key=lambda x: x[1])[0]
    
    def get_error_patterns(self) -> Dict[Tuple[str, str], float]:
        """Get error pattern frequencies.
        
        Returns:
            Dictionary mapping error patterns to their frequencies
        """
        total_patterns = sum(self.error_patterns.values())
        if total_patterns == 0:
            return {}
        
        return {
            pattern: count / total_patterns
            for pattern, count in self.error_patterns.items()
        }
    
    def get_error_distribution(self) -> Dict[str, float]:
        """Get distribution of error types.
        
        Returns:
            Dictionary mapping error types to their frequencies
        """
        total_errors = sum(self.error_counts.values())
        if total_errors == 0:
            return {}
        
        return {
            error_type: count / total_errors
            for error_type, count in self.error_counts.items()
        }
