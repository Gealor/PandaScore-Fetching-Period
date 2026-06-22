import asyncio
from functools import wraps

from src.core.config import settings
from src.core.logger import log


def api_retry_decorator(attempts: int = settings.api.attempts_for_retry):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, attempts+1):
                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    log.warning(
                        "Error %s occurred during execution of '%s' (attempt %d/%d): %s",
                        type(e).__name__,
                        func.__name__,
                        attempt,
                        attempts,
                        e,
                    )
                    if attempt == attempts:
                        log.error(
                            "All %d attempts to execute '%s' failed.",
                            attempts,
                            func.__name__
                        )
                        raise

                    sleep_time = settings.api.backoff_factor ** attempt
                    await asyncio.sleep(sleep_time)
                else:
                    return result
        return wrapper
    return decorator

