import json
import os
import uuid

import asyncio

from .publisher import publisher
from .consumer import consumer, IncomingMessage


class RPCClass:

    def __init__(self, loop=None, broker_url=os.getenv('BROKER_URL'), exchange_type=None, exchange_name=None,
                 queue_name=os.getenv('QUEUE_NAME'), routing_key=None, durable=False):
        self.connection = None
        self.channel = None
        self.queue_name = queue_name
        if not self.queue_name.__contains__('rpc'):
            self.queue_name += '_rpc'
        self.exchange_type = exchange_type
        self.broker_url = broker_url
        self.routing_key = routing_key
        self.exchange_name = exchange_name
        self.durable = durable
        self.futures = {}
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()

    async def connect(self):
        await consumer(loop=self.loop, callback=self.on_response, queue_name=self.queue_name, durable=True,
                       exchange_name=self.exchange_name, exchange_type=self.exchange_type, broker_url=self.broker_url)

    async def on_response(self, message: IncomingMessage):
        try:
            future = self.futures.pop(message.correlation_id)
            async with message.process():
                future.set_result(message.body)
        except:
            message.nack()

    async def call(self, target, model=None, key=None, value=None):
        correlation_id = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futures[correlation_id] = future
        data = {
            'op': 'get',
            'model': model,
            'key': key,
            'value': value
        }
        data = json.dumps(data)
        await publisher(data, routing_key=target, reply_to=self.queue_name, loop=self.loop,
                        exchange_type=self.exchange_type, exchange_name=self.exchange_name,
                        correlation_id=correlation_id, broker_url=self.broker_url)
        return json.loads(await future)
