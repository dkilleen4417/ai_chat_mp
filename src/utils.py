"""
Utility functions for response metrics and token estimation
"""
import time
from typing import Dict, List, Any, Optional


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text using character-based approximation.
    Uses rough GPT tokenization estimate: ~4 characters per token.
    
    Args:
        text: Input text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Remove excessive whitespace and normalize
    normalized_text = ' '.join(text.split())
    
    # Rough estimation: 4 characters per token (GPT-style)
    estimated_tokens = len(normalized_text) / 4
    
    return max(1, int(round(estimated_tokens)))


def calculate_tokens_per_second(output_tokens: int, response_time: float) -> float:
    """
    Calculate tokens per second rate.
    
    Args:
        output_tokens: Number of output tokens
        response_time: Response time in seconds
        
    Returns:
        Tokens per second (0 if invalid inputs)
    """
    if response_time <= 0 or output_tokens <= 0:
        return 0.0
    
    return round(output_tokens / response_time, 1)


def format_response_metrics(metrics: Dict[str, Any]) -> str:
    """
    Format response metrics into display string.
    
    Args:
        metrics: Dictionary containing:
            - response_time: float (seconds)
            - input_tokens: int 
            - output_tokens: int
            - estimated: list of field names that are estimates
            
    Returns:
        Formatted metrics string
    """
    if not metrics:
        return ""
    
    response_time = metrics.get("response_time", 0)
    input_tokens = metrics.get("input_tokens", 0)
    output_tokens = metrics.get("output_tokens", 0)
    estimated_fields = metrics.get("estimated", [])
    
    # Calculate tokens per second
    tokens_per_sec = calculate_tokens_per_second(output_tokens, response_time)
    
    # Format time
    if response_time < 1:
        time_str = f"{response_time:.1f} sec"
    else:
        time_str = f"{int(round(response_time))} sec"
    
    # Format tokens per second
    if tokens_per_sec > 0:
        if tokens_per_sec >= 10:
            tps_str = f"{int(tokens_per_sec)} TPS"
        else:
            tps_str = f"{tokens_per_sec} TPS"
        # Add asterisk if either output tokens OR response time is estimated
        if "output_tokens" in estimated_fields or response_time <= 0:
            tps_str += "*"
    else:
        tps_str = "- TPS"
    
    # Format input tokens
    input_str = f"{input_tokens} tokens"
    if "input_tokens" in estimated_fields:
        input_str += "*"
    
    # Format output tokens  
    output_str = f"{output_tokens} tokens"
    if "output_tokens" in estimated_fields:
        output_str += "*"
    
    # Combine all metrics
    metrics_str = f"Time: {time_str}, Speed: {tps_str}, Input: {input_str}, Output: {output_str}"
    
    # Add estimation note if any fields are estimated
    if estimated_fields:
        metrics_str += " (* = estimated)"
    
    return metrics_str


class ResponseTimer:
    """Context manager for timing response generation"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time:
            end_time = self.end_time if self.end_time else time.time()
            return end_time - self.start_time
        return 0.0


def create_response_object(text: str, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create standardized response object with text and metrics.
    
    Args:
        text: Response text
        metrics: Optional metrics dictionary
        
    Returns:
        Standardized response object
    """
    return {
        "text": text,
        "metrics": metrics or {}
    }