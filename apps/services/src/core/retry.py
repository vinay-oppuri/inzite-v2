import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ExternalAPIError(Exception):
    """Retryable error from an external API."""


def resilient_call(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 8,
):
    """
    Retry an external API call when ExternalAPIError is raised.

    Example:
        @resilient_call()
        async def fetch_data():
            ...
    """
    logger.debug("Creating retry wrapper")

    def decorator(func):
        logger.debug("Decorating %s with retry wrapper", func.__name__)

        def log_retry(retry_state):
            logger.debug("Logging retry attempt")
            error = retry_state.outcome.exception()

            logger.warning(
                "Retrying %s after attempt %s because of: %s",
                func.__name__,
                retry_state.attempt_number,
                error,
            )

        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=min_wait,
                max=max_wait,
            ),
            retry=retry_if_exception_type(ExternalAPIError),
            before_sleep=log_retry,
            reraise=True,
        )(func)

    return decorator
