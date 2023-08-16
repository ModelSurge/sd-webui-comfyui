from lib_comfyui.webui import settings


def register_comfyui(fast_api):
    from starlette.requests import Request
    from starlette.responses import StreamingResponse
    from starlette.background import BackgroundTask
    from fastapi import WebSocket
    import httpx
    import websockets
    import asyncio
    from starlette.websockets import WebSocketDisconnect
    from websockets.exceptions import ConnectionClosedOK

    # Constants & Configuration
    comfyui_target_url = f"http://localhost:{settings.get_port()}/"
    client = httpx.AsyncClient(base_url=comfyui_target_url)
    ws_client_url = http_to_ws(comfyui_target_url)
    proxy_path = "/sd-webui-comfyui/comfyui-proxy"

    async def aiter_raw_patched(response):
        """Patch URLs for reverse proxying."""
        async for chunk in response.aiter_raw():
            # Adjust these URL modifications as necessary
            modifications = [
                (b'from "/scripts/', b'from "/sd-webui-comfyui/comfyui-proxy/scripts/'),
                (b'/favicon', b'/sd-webui-comfyui/comfyui-proxy/favicon'),
                (b'from "/extensions/', b'from "/sd-webui-comfyui/comfyui-proxy/extensions/'),
                (b'from "/webui_scripts/', b'from "/sd-webui-comfyui/comfyui-proxy/webui_scripts/'),
                (b'sd-webui-comfyui/comfyui-proxy/sd-webui-comfyui/comfyui-proxy', b'sd-webui-comfyui/comfyui-proxy'),
            ]
            for original, modified in modifications:
                chunk = chunk.replace(original, modified)
            yield chunk

    async def reverse_proxy(request: Request):
        """Proxy incoming requests to another server."""
        base_path = request.url.path.replace(proxy_path, "")
        url = httpx.URL(path=base_path, query=request.url.query.encode("utf-8"))
        rp_req = client.build_request(request.method, url, headers=request.headers.raw, content=await request.body())
        rp_resp = await client.send(rp_req, stream=True)
        return StreamingResponse(
            aiter_raw_patched(rp_resp),
            status_code=rp_resp.status_code,
            headers=rp_resp.headers,
            background=BackgroundTask(rp_resp.aclose),
        )

    fast_api.add_route(f"{proxy_path}/{{path:path}}", reverse_proxy, ["GET", "POST", "PUT", "DELETE"])

    @fast_api.websocket(f"{proxy_path}/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Websocket endpoint to proxy incoming WS requests."""
        await websocket.accept()
        async with websockets.connect(ws_client_url) as ws_server:

            async def listen_to_client():
                """Forward messages from client to server."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        await ws_server.send(data)
                except WebSocketDisconnect:
                    await ws_server.close()

            async def listen_to_server():
                """Forward messages from server to client."""
                try:
                    while True:
                        data = await ws_server.recv()
                        await websocket.send_text(data)
                except ConnectionClosedOK:
                    pass

            await asyncio.gather(listen_to_client(), listen_to_server())

    print("[sd-webui-comfyui]", "Created reverse proxy to comfyui server at", )


def http_to_ws(url: str) -> str:
    """Convert http or https URL to its websocket equivalent."""
    from urllib.parse import urlparse, urlunparse

    parsed_url = urlparse(url)
    ws_scheme = 'wss' if parsed_url.scheme == 'https' else 'ws'
    ws_url = parsed_url._replace(scheme=ws_scheme)
    return urlunparse(ws_url) + "ws"
