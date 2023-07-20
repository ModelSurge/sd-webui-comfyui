import asyncio


class PollingServer:
    def __init__(self):
        self.clients = {}

    def __contains__(self, item):
        return item in self.clients

    def register_new_client(self, cid):
        self.clients[cid] = RequestHandler()

    def send(self, cid, request):
        return asyncio.run(self.clients[cid].send(request))

    async def handle_response(self, response):
        await self.clients[response['cid']].handle_response(response)

    async def handle_request(self, cid):
        await self.clients[cid].handle_request()


class RequestHandler:
    def __init__(self):
        self.request_queue = asyncio.Queue()
        self.answer_queue = asyncio.Queue()

    async def send(self, request):
        await self.request_queue.put(request)
        return await self.answer_queue.get()

    async def handle_request(self):
        return await self.request_queue.get()

    async def handle_response(self, response):
        await self.answer_queue.put(response)


polling_server = PollingServer()


async def simulated_server_call(response):
    if 'cid' not in response:
        raise ValueError('400 - Missing cid in response')  # 400

    cid = response['cid']

    if cid not in polling_server:
        polling_server.register_new_client(cid)
    else:
        if 'error_code' in response:
            print(f"[sd-webui-comfyui] Client {cid} encountered an error:\n{response['error_code']}")
        await polling_server.handle_response(response)
    await polling_server.handle_request(cid)


async def simulated_client(cid, delay, error=False):
    await asyncio.sleep(delay)
    response = {
        'cid': cid,
        'response_data': f'Response from client {cid}',
        'error_code': 'CLIENT_ERROR' if error else None,
    }
    await simulated_server_call(response)


async def main():
    # Run two client tasks concurrently with different delays and one with an error
    tasks = [
        simulated_client(cid=1, delay=2),
        simulated_client(cid=2, delay=3),
        simulated_client(cid=3, delay=1, error=True)
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    q = asyncio.Event()

    async def halt_until_signal():
        await asyncio.sleep(3)
        await q.wait()
        print('unhalted')

    async def stop_halting():
        q.set()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(halt_until_signal(), stop_halting()))
    print('hi')

