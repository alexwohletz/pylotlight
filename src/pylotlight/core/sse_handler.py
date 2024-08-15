import asyncio
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from redis import Redis

router = APIRouter()
redis = Redis(host='redis', port=6379, db=1)

async def event_generator(request: Request):
    pubsub = redis.pubsub()
    pubsub.subscribe('sse_channel')
    try:
        while True:
            if await request.is_disconnected():
                break

            message = pubsub.get_message()
            if message and message['type'] == 'message':
                yield {
                    "event": "update",
                    "data": message['data'].decode('utf-8')
                }

            await asyncio.sleep(0.1)
    finally:
        pubsub.unsubscribe('sse_channel')

@router.get("/sse")
async def sse(request: Request):
    return EventSourceResponse(event_generator(request))