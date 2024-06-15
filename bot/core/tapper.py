import asyncio
import heapq
import math
from random import randint
from time import time
from datetime import datetime, timedelta, timezone

import aiohttp
from aiohttp_proxy import ProxyConnector
from bot.api.auth import login
from bot.api.farm import claim_farm, start_farm
from bot.api.info import get_info
from pyrogram import Client

from bot.config import settings
from bot.utils.logger import logger
from bot.exceptions import InvalidSession

from bot.utils.scripts import get_headers, is_jwt_valid
from bot.utils.tg_web_data import get_tg_web_data
from bot.utils.proxy import check_proxy


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def run(self, proxy: str | None) -> None:
        token = ""
        sleep_time=0
        headers = get_headers(name=self.tg_client.name)

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        http_client = aiohttp.ClientSession(
            headers=headers, connector=proxy_conn
        )

        if proxy:
            await check_proxy(
                http_client=http_client,
                proxy=proxy,
                session_name=self.session_name,
            )

        tg_web_data = await get_tg_web_data(
            tg_client=self.tg_client,
            proxy=proxy,
            session_name=self.session_name,
        )

        while True:
            try:
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = (
                        ProxyConnector().from_url(proxy) if proxy else None
                    )

                    http_client = aiohttp.ClientSession(
                        headers=headers, connector=proxy_conn
                    )
                    http_client.headers[
                        'Authorization'
                    ] = f'Bearer {token}'


                if not is_jwt_valid(http_client.headers.get("Authorization", "")):
                    # Remove the Authorization header if it exists
                    if "Authorization" in http_client.headers:
                        del http_client.headers["Authorization"]

                    # Attempt to log in and get new authentication data
                    login_data = await login(http_client=http_client, tg_web_data=tg_web_data)
                    token = login_data.get('token')
                    http_client.headers[
                        'Authorization'
                    ] = f'Bearer {token}'
                    logger.info(
                        f'Your current balance is: { login_data.get("balanceInfo").get("balance")}')

                    # Check if the new Authorization token is present in the headers
                    if not http_client.headers.get("Authorization"):
                        logger.error(
                            f"{self.session_name} | Failed to fetch token | Sleeping for 60s")
                        await asyncio.sleep(delay=60)
                        continue


                info = await get_info(http_client=http_client)

                if info.get("activeFarmingStartedAt") is None:
                    f_info = await start_farm(http_client=http_client)
                    sleep_time= f_info.get("farmingDurationInSec")
                else:
                    startedAt=info.get("activeFarmingStartedAt")
                    farmingDurationInSec=int(info.get("farmingDurationInSec"))
                    farm_start_time = datetime.fromisoformat(startedAt.replace("Z", "+00:00"))
                    farm_end_time = farm_start_time + timedelta(seconds=farmingDurationInSec)

                    current_time = datetime.now(timezone.utc)
                    if current_time > farm_end_time:
                        await claim_farm(http_client=http_client)
                        sleep_between_clicks = randint(
                        a=settings.SLEEP_BETWEEN_TAP[0],
                        b=settings.SLEEP_BETWEEN_TAP[1],
                        )
                        logger.info(f'Sleep {sleep_between_clicks}s')
                        await asyncio.sleep(delay=sleep_between_clicks)
                        continue
                    else:
                        remaining_time = farm_end_time - datetime.now(timezone.utc)
                        sleep_time=math.ceil(remaining_time.total_seconds())
                await http_client.close()
                if proxy_conn:
                    if not proxy_conn.closed:
                        proxy_conn.close()

                logger.info(
                    f'{self.session_name} | Sleep {sleep_time:,}s'
                )
                await asyncio.sleep(delay=sleep_time)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f'{self.session_name} | Unknown error: {error}')
                await asyncio.sleep(delay=3)

            else:
                sleep_between_clicks = randint(
                    a=settings.SLEEP_BETWEEN_TAP[0],
                    b=settings.SLEEP_BETWEEN_TAP[1],
                )
                logger.info(f'Sleep {sleep_between_clicks}s')
                await asyncio.sleep(delay=sleep_between_clicks)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f'{tg_client.name} | Invalid Session')
