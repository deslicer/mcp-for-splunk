"""
Shared configuration classes for Splunk troubleshooting agents.
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for OpenAI agent settings."""

    api_key: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4000

    @classmethod
    def from_environment(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )

        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
        )


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    @classmethod
    def from_environment(cls) -> "RetryConfig":
        """Load retry configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            base_delay=float(os.getenv("OPENAI_RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("OPENAI_RETRY_MAX_DELAY", "60.0")),
            exponential_base=float(os.getenv("OPENAI_RETRY_EXPONENTIAL_BASE", "2.0")),
            jitter=os.getenv("OPENAI_RETRY_JITTER", "true").lower() == "true",
        )

    def calculate_delay(self, attempt: int, suggested_delay: float | None = None) -> float:
        """Calculate delay for the given attempt number."""
        import random

        if suggested_delay is not None:
            # Use the delay suggested by the API (from rate limit headers)
            delay = suggested_delay
        else:
            # Calculate exponential backoff delay
            delay = self.base_delay * (self.exponential_base**attempt)

        # Cap the delay at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay
