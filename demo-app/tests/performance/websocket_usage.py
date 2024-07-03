import asyncio
import datetime
import json
import time

import websockets


async def client1(client_id: int):
    async with websockets.connect(f"ws://127.0.0.1:8080/ws/{client_id}") as websocket:
        round_trips = 0
        start = time.time_ns()
        message = json.dumps({"stoks": "HUFUSD", "quantity": client_id})
        await websocket.send(message)
        while True:
            await websocket.recv()
            round_trips += 1
            if (round_trips % 10) == 0:
                end = time.time_ns()
                duration = (end - start) / 1000000000
                print("C1 rate: ", round_trips / duration, " round trips per second")
                await websocket.close_connection()
            await websocket.send(message)


async def client2(client_id: int):
    async with websockets.connect(f"ws://127.0.0.1:8080/ws/{client_id}") as websocket:
        round_trips = 0
        start = time.time_ns()
        message = json.dumps({"stoks": "HUFUSD", "quantity": client_id})
        await websocket.send(message)
        while True:
            await websocket.recv()
            round_trips += 1
            if (round_trips % 10) == 0:
                end = time.time_ns()
                duration = (end - start) / 1000000000
                print("C2 rate: ", round_trips / duration, " round trips per second")
                await websocket.close_connection()
            await websocket.send(message)


async def main():
    task1 = asyncio.create_task(
        client1(client_id=int(datetime.datetime.now().timestamp() * 1000))
    )
    task2 = asyncio.create_task(
        client2(client_id=int(datetime.datetime.now().timestamp() * 1000))
    )
    await asyncio.gather(task1, task2)


asyncio.run(main())
