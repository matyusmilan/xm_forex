import json

import aiohttp
import asyncio


async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('ws://127.0.0.1:8080/ws') as ws:
            # await for messages and send messages
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print(f'SERVER says - {msg.data}')
                    text = input('PRESS ENTER')
                    oder_input = {"stoks": "DMKEUR", "quantity": "100"}
                    await ws.send_json(oder_input)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

asyncio.run(main())
