"""
Shared retry utilities for Splunk troubleshooting agents.
"""

import asyncio
import logging
import random
from typing import Optional

from fastmcp import Context
from .config import RetryConfig

logger = logging.getLogger(__name__)

# Import OpenAI exceptions for retry logic
try:
    from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError
    OPENAI_EXCEPTIONS_AVAILABLE = True
except ImportError:
    OPENAI_EXCEPTIONS_AVAILABLE = False
    RateLimitError = Exception
    APIError = Exception
    APIConnectionError = Exception
    APITimeoutError = Exception


async def retry_with_exponential_backoff(
    func,
    retry_config: RetryConfig,
    ctx: Context,
    *args,
    **kwargs
):
    """
    Retry a function with exponential backoff for OpenAI rate limit errors.
    
    Args:
        func: The async function to retry
        retry_config: Configuration for retry behavior
        ctx: FastMCP context for progress reporting
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        The result of the function call
    
    Raises:
        The last exception if all retries are exhausted
    """
    last_exception = None
    
    for attempt in range(retry_config.max_retries + 1):
        try:
            logger.info(f"Attempt {attempt + 1}/{retry_config.max_retries + 1} for function {func.__name__}")
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"Function {func.__name__} succeeded after {attempt + 1} attempts")
                await ctx.info(f"✅ Operation succeeded after {attempt + 1} attempts")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if this is a retryable error
            is_rate_limit = False
            is_retryable = False
            suggested_delay = None
            
            if OPENAI_EXCEPTIONS_AVAILABLE:
                if isinstance(e, RateLimitError):
                    is_rate_limit = True
                    is_retryable = True
                    
                    # Try to extract suggested delay from error message
                    error_message = str(e)
                    if "Please try again in" in error_message:
                        try:
                            # Extract delay from message like "Please try again in 7.562s"
                            import re
                            match = re.search(r"try again in (\d+\.?\d*)s", error_message)
                            if match:
                                suggested_delay = float(match.group(1))
                                logger.info(f"API suggested delay: {suggested_delay}s")
                        except Exception:
                            pass
                
                elif isinstance(e, (APIConnectionError, APITimeoutError)):
                    is_retryable = True
                
                elif isinstance(e, APIError):
                    # Some API errors might be retryable (5xx status codes)
                    if hasattr(e, 'status_code') and e.status_code >= 500:
                        is_retryable = True
            else:
                # Fallback: check error message for common patterns
                error_str = str(e).lower()
                if any(pattern in error_str for pattern in ['rate limit', '429', 'too many requests']):
                    is_rate_limit = True
                    is_retryable = True
                elif any(pattern in error_str for pattern in ['connection', 'timeout', '5']):
                    is_retryable = True
            
            # Log the error
            if is_rate_limit:
                logger.warning(f"Rate limit error on attempt {attempt + 1}: {e}")
            elif is_retryable:
                logger.warning(f"Retryable error on attempt {attempt + 1}: {e}")
            else:
                logger.error(f"Non-retryable error on attempt {attempt + 1}: {e}")
                raise e
            
            # If this was the last attempt, raise the exception
            if attempt == retry_config.max_retries:
                logger.error(f"All {retry_config.max_retries + 1} attempts failed for {func.__name__}")
                raise e
            
            # Calculate delay for next attempt
            delay = retry_config.calculate_delay(attempt, suggested_delay)
            
            # Report retry to user
            if is_rate_limit:
                await ctx.info(f"⏳ Rate limit reached. Retrying in {delay:.1f}s... (attempt {attempt + 2}/{retry_config.max_retries + 1})")
            else:
                await ctx.info(f"🔄 Retrying in {delay:.1f}s due to temporary error... (attempt {attempt + 2}/{retry_config.max_retries + 1})")
            
            logger.info(f"Waiting {delay:.1f}s before retry {attempt + 2}")
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    raise last_exception 