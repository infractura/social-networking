import random
import time
from typing import Dict, Optional

class AdaptiveBackoffManager:
    """Manages retry backoff with adaptive strategies and jitter."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0):
        """Initialize backoff manager.
        
        Args:
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.success_streak = 0
        self.failure_streak = 0
        self.jitter_factor = 0.1
        self.delay_history: list[float] = []
        self.error_counts: Dict[str, int] = {}
        self.last_backoff: Optional[float] = None
        self._min_jitter = 0.01
        self._max_jitter = 0.5
    
    def add_jitter(self, delay: float) -> float:
        """Add randomized jitter to delay.
        
        Args:
            delay: Base delay value
            
        Returns:
            Delay with jitter added
        """
        jitter = delay * self.jitter_factor
        return delay + random.uniform(-jitter, jitter)
    
    def get_delay(self, attempt: int, error_type: Optional[str] = None) -> float:
        """Calculate delay with exponential backoff and jitter.
        
        Args:
            attempt: Attempt number (0-based)
            error_type: Type of error that occurred
            
        Returns:
            Delay in seconds
        """
        # Track error types
        if error_type:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Base exponential backoff
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        # Adjust based on error type and history
        if error_type == "rate_limit":
            # Increase delay more aggressively for rate limits
            rate_limit_count = self.error_counts.get("rate_limit", 0)
            if rate_limit_count > 3:
                delay = min(delay * 2.0, self.max_delay)  # Double delay for persistent rate limits
            else:
                delay = min(delay * 1.5, self.max_delay)  # 50% increase for initial rate limits
        elif error_type == "timeout":
            # Moderate increase for timeouts
            timeout_count = self.error_counts.get("timeout", 0)
            if timeout_count > 3:
                delay = min(delay * 1.5, self.max_delay)
        
        # Apply jitter
        final_delay = self.add_jitter(delay)
        
        # Ensure delay is within bounds
        final_delay = max(self.base_delay * 0.5, min(final_delay, self.max_delay))
        
        self.delay_history.append(final_delay)
        self.last_backoff = final_delay
        return final_delay
    
    def record_result(self, success: bool) -> None:
        """Update strategy based on result.
        
        Args:
            success: Whether the request succeeded
        """
        if success:
            self.success_streak += 1
            self.failure_streak = 0
            if self.success_streak >= 5:
                # Increase jitter on consistent success
                self.jitter_factor = min(self.jitter_factor * 1.5, self._max_jitter)
                self.success_streak = 0
        else:
            self.failure_streak += 1
            self.success_streak = 0
            if self.failure_streak >= 3:
                # Decrease jitter on consistent failure
                self.jitter_factor = max(self.jitter_factor * 0.5, self._min_jitter)
                self.failure_streak = 0
    
    def get_stats(self) -> Dict[str, float]:
        """Get backoff statistics.
        
        Returns:
            Dictionary of statistics
        """
        if not self.delay_history:
            return {
                "min_delay": 0.0,
                "max_delay": 0.0,
                "avg_delay": 0.0,
                "current_jitter": self.jitter_factor
            }
        
        return {
            "min_delay": min(self.delay_history),
            "max_delay": max(self.delay_history),
            "avg_delay": sum(self.delay_history) / len(self.delay_history),
            "current_jitter": self.jitter_factor
        }
    
    def reset(self) -> None:
        """Reset backoff state."""
        self.success_streak = 0
        self.failure_streak = 0
        self.jitter_factor = 0.1
        self.delay_history.clear()
        self.error_counts.clear()
        self.last_backoff = None
