import aiohttp
from typing import Any
from bot.api.http import handle_error, make_post_request


async def get_tasks(
    http_client: aiohttp.ClientSession,
) -> dict[Any, Any] | Any:
    response_json = await make_post_request(
        http_client,
        'https://api.hamsterkombat.io/clicker/list-tasks',
        {},
        'getting Tasks',
    )
    tasks = response_json.get('tasks')
    return tasks


async def start_farm(http_client: aiohttp.ClientSession) -> dict[Any, Any]:
    response_json = await make_post_request(
        http_client,
        'https://tg-bot-tap.laborx.io/api/v1/farming/start',
        {},
        'start farm',
    )
    return response_json

async def claim_farm(
    http_client: aiohttp.ClientSession,
) -> dict[Any, Any]:
    response_json = await make_post_request(
        http_client,
        'https://tg-bot-tap.laborx.io/api/v1/farming/finish',
        {},
        'claim farm',
    )
    return response_json

