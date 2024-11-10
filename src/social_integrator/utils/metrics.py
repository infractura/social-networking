import time
from typing import Dict, Any, Optional, List
from collections import defaultdict

class RetryMetricsCollector:
    """Collects and analyzes retry-related metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.retry_counts: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.error_types: Dict[str, int] = defaultdict(int)
        self.total_requests = 0
        self.total_attempts = 0
        self.failed_requests = 0
        self.retry_intervals: List[float] = []
        self.consecutive_failures = 0
        self.last_success_time: Optional[float] = None
        self._request_history: List[Dict[str, Any]] = []
        self._max_retry_per_request: Dict[str, int] = {}
    
    def record_attempt(
        self,
        request_id: str,
        response_time: float,
        error_type: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """Record metrics for an attempt.
        
        Args:
            request_id: Unique request identifier
            response_time: Response time in seconds
            error_type: Type of error if failed
            retry_count: Number of retries for this request
        """
        # Update retry count for the request
        self._max_retry_per_request[request_id] = max(
            self._max_retry_per_request.get(request_id, 0),
            retry_count
        )
        self.retry_counts[request_id] = retry_count
        
        self.response_times[request_id].append(response_time)
        
        # Record in history
        self._request_history.append({
            'request_id': request_id,
            'response_time': response_time,
            'error_type': error_type,
            'retry_count': retry_count,
            'timestamp': time.monotonic()
        })
        
        # Update counters
        self.total_attempts += 1
        if request_id not in self.response_times or len(self.response_times[request_id]) == 1:
            self.total_requests += 1
        
        if error_type:
            self.error_types[error_type] += 1
            self.failed_requests += 1
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
            self.last_success_time = time.monotonic()
    
    def record_retry_interval(self, interval: float) -> None:
        """Record time between retries.
        
        Args:
            interval: Time between attempts in seconds
        """
        self.retry_intervals.append(interval)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics.
        
        Returns:
            Dictionary of metrics
        """
        # Calculate success rate based on total attempts
        success_rate = 1.0
        if self.total_attempts > 0:
            success_rate = 1.0 - (self.failed_requests / self.total_attempts)
        
        # Calculate average retries per request using max retries per request
        avg_retries = 0.0
        if self._max_retry_per_request:
            avg_retries = sum(self._max_retry_per_request.values()) / len(self._max_retry_per_request)
        
        # Calculate average response time
        avg_response_time = 0.0
        if self.response_times:
            total_time = sum(
                sum(times) / len(times)
                for times in self.response_times.values()
            )
            avg_response_time = total_time / len(self.response_times)
        
        # Calculate average retry interval
        avg_retry_interval = 0.0
        if self.retry_intervals:
            avg_retry_interval = sum(self.retry_intervals) / len(self.retry_intervals)
        
        # Calculate time since last success
        time_since_success = None
        if self.last_success_time:
            time_since_success = time.monotonic() - self.last_success_time
        
        return {
            "success_rate": success_rate,
            "avg_retries": avg_retries,
            "avg_response_time": avg_response_time,
            "error_distribution": dict(self.error_types),
            "avg_retry_interval": avg_retry_interval,
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success": time_since_success,
            "total_requests": self.total_requests,
            "total_attempts": self.total_attempts,
            "failed_requests": self.failed_requests
        }
    
    def get_error_distribution(self) -> Dict[str, float]:
        """Get distribution of error types.
        
        Returns:
            Dictionary mapping error types to their frequencies
        """
        total_errors = sum(self.error_types.values())
        if total_errors == 0:
            return {}
        
        return {
            error_type: count / total_errors
            for error_type, count in self.error_types.items()
        }
    
    def get_retry_distribution(self) -> Dict[int, int]:
        """Get distribution of retry counts.
        
        Returns:
            Dictionary mapping retry counts to their frequencies
        """
        retry_dist: Dict[int, int] = defaultdict(int)
        # Initialize with zero for all retry counts up to max
        max_retries = max(self._max_retry_per_request.values(), default=0)
        for i in range(max_retries + 1):
            retry_dist[i] = 0
            
        # Count actual retry occurrences
        for count in self._max_retry_per_request.values():
            retry_dist[count] += 1
        return dict(retry_dist)
