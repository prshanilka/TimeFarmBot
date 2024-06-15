
import aiohttp
from typing import Any
import json
from bot.api.http import handle_error, make_post_request


async def get_info(
    http_client: aiohttp.ClientSession,
) -> dict[Any, Any] | Any:
    try:
        response = await http_client.get(url="https://tg-bot-tap.laborx.io/api/v1/farming/info")
        response_text = await response.text()
        response.raise_for_status()
        response_json = json.loads(response_text)
        return response_json
    except Exception as error:
        await handle_error(error, response_text, "getting user info failed")
        return {}