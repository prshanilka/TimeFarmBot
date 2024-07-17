import asyncio
import heapq
import math
from random import randint
from time import time
from datetime import datetime, timedelta, timezone
from bot.api.http import handle_error, make_post_request

import aiohttp
from aiohttp_proxy import ProxyConnector
from bot.api.auth import login
from bot.api.farm import claim_farm, start_farm
from bot.api.info import get_info
from pyrogram import Client
import json
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

    async def get_task_list(self,http_client: aiohttp.ClientSession,) -> list:
        res=await http_client.get(url="https://tg-bot-tap.laborx.io/api/v1/tasks")
        response_text = await res.text()
        response_json = json.loads(response_text)
        task_list=[]
        for i in response_json:
            # if 'submission' not in i:
            task_list.append(i['id'])
        logger.info(task_list)
        return task_list
    async def submit_claim(self,http_client: aiohttp.ClientSession,task_list :list ) -> None:
        if '668fbec8647177930d0ac0bc' in task_list:
            bind_wallet_url=f'https://tg-bot-tap.laborx.io/api/v1/me/ton/info'
            wallet_json= {"address":"UQAatGc8y2TtYjnSxb1jaCstvo4HdDAyIGv6G05Bncfl5lPH"}
            res =  await make_post_request(http_client,bind_wallet_url,wallet_json,"钱包信息更新")
        for i in task_list:
            sub_url = f'https://tg-bot-tap.laborx.io/api/v1/tasks/{i}/submissions'
            claim_url2 = f'https://tg-bot-tap.laborx.io/api/v1/tasks/{i}/claims'
            res = await http_client.post(url=sub_url,json={})
            text=res.text()
            logger.info(text)
            # if "OK" in text or res.status ==400:
            response2_json =  await http_client.post(
                url=claim_url2,
                json={})
            logger.info(response2_json.text())
        return None   
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
                task_list=await self.get_task_list(http_client=http_client)
                if len(task_list)>1:
                    await self.submit_claim(task_list=task_list,http_client=http_client)
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

