import aiohttp
from typing import Any
import json
from bot.api.http import handle_error, make_post_request
from bot.utils.scripts import convert_to_url_encoded_format


async def login(
    http_client: aiohttp.ClientSession, tg_web_data: str
) -> Any | None:
    response_text = ""
    try:
        data = convert_to_url_encoded_format(tg_web_data)        
        data={
            "initData":data,
            "platform":"android"
        }
        response = await http_client.post(url='https://tg-bot-tap.laborx.io/api/v1/auth/validate-init/v2', data=data)
        response_text = await response.text()
        response.raise_for_status()
        response_json = json.loads(response_text)
        return response_json
    except Exception as error:
        await handle_error(error, response_text, 'getting Access Token')
        return None
