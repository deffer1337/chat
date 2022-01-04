#!/usr/bin/env python3
import json
from typing import Dict

from aiohttp import web


class WSChat:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.conns = {}
        self.clients = {}

    async def main_page(self, request):
        return web.FileResponse('templates/index_.html')

    async def broadcast(self, message: Dict, to: str = None) -> None:
        """
        :param message: Message which need send and looks like
        `{'mtype': 'INIT', 'id': 'ABCDEFGH'}` — initialization, sent when the user logs in
            - `id`: user id
        `{'mtype': 'TEXT', 'id': 'IDFROM', 'to': 'IDTO', 'text': 'message text'}` — send message
            - `id`: sender id
            - `to`: reciver id
            - `text`: message text
        `{'mtype': 'MSG', 'id': 'IDFROM', 'text': 'message'}` — message with text `text` from user `id`
        `{'mtype': 'DM', 'id': 'IDFROM', 'text': 'message'}` — «private» message with text `text` from user `id`
        `{'mtype': 'USER_ENTER', 'id': 'USERID'}` — service message «User `id` entered the chat»
        `{'mtype': 'USER_LEAVE', 'id': 'USERID'}` — service message «User `id` leaved the chat»
        :param to: When need send private message
        """
        for client, id in self.clients.items():
            try:
                if message['id'] != id and (not to or id == to):
                    await client.send_json(message)
            except ConnectionResetError:
                pass

    async def websocket_handler(self, request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.data == 'ping':
                await ws.pong()
                continue
            data = json.loads(msg.data)
            if data['mtype'] == 'INIT':
                self.clients[ws] = data['id']
                await self.broadcast({'mtype': 'USER_ENTER', 'id': f'{data["id"]}'})
            elif data['mtype'] == 'TEXT':
                if data['to']:
                    await self.broadcast({'mtype': 'DM', 'id': f'{data["id"]}', 'text': f'{data["text"]}'}, data['to'])
                else:
                    await self.broadcast({'mtype': 'MSG', 'id': f'{data["id"]}', 'text': f'{data["text"]}'})
        else:
            await ws.close()
            await self.broadcast({'mtype': 'USER_LEAVE', 'id': f'{self.clients[ws]}'})
            self.clients.pop(ws)

        return ws

    def run(self):
        app = web.Application()
        app.router.add_get('/', self.main_page)
        app.router.add_get('/chat', self.websocket_handler)
        web.run_app(app, host=self.host, port=self.port)


if __name__ == '__main__':
    WSChat().run()
