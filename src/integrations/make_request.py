from typing import Any

from aiohttp import ClientSession

from src.core.logger import log
from src.schemas.exceptions.integration import InvalidFormatResponse


async def make_request(
    url: str,
    params: dict[str, str | int],
    headers: dict[str, str],
    aiohttp_session: ClientSession,
) -> Any:
    async with aiohttp_session.get(url, headers=headers, params=params) as response:
        response.raise_for_status()
        if "application/json" not in response.content_type:
            log.error("Invalid format response. Expected JSON.")
            raise InvalidFormatResponse

        return await response.json()
