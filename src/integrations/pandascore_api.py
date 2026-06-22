from typing import Any

from aiohttp import ClientError
from aiohttp import ClientResponseError
from aiohttp import ClientSession

from src.core.config import settings
from src.core.logger import log
from src.decorators import api_retry_decorator
from src.schemas.exceptions.integration import FailedResponseCodeException
from src.schemas.exceptions.integration import UnexpectedResponseException

from .make_request import make_request


@api_retry_decorator(attempts=settings.api.attempts_for_retry)
async def get_list_matches(
    aiohttp_session: ClientSession,
    url: str = f"{settings.api.base_url}/matches",
    per_page: int = settings.api.per_page,
    page: int = 1,
) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {settings.api.api_token}"}
    params = {
        "page": page,
        "per_page": per_page,
        "sort": "-modified_at",
    }
    try:
        result = await make_request(
            url=url, params=params, headers=headers, aiohttp_session=aiohttp_session
        )
    except ClientResponseError as e:
        log.error("Failed response: code=%s, detail=%s", e.status, e.message)
        raise FailedResponseCodeException(e.status, e.message) from e
    except ClientError as e:
        log.error("Request to PandaScore failed: %s", e)
        raise UnexpectedResponseException(e) from e

    return result
