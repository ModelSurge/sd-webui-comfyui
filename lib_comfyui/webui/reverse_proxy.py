from lib_comfyui.webui import settings


def register_comfyui(fast_api):
    if not settings.is_reverse_proxy_enabled():
        return

    from starlette.requests import Request
    from starlette.responses import StreamingResponse
    from starlette.background import BackgroundTask
    from fastapi import WebSocket
    import httpx
    import websockets
    import asyncio
    from starlette.websockets import WebSocketDisconnect
    from websockets.exceptions import ConnectionClosedOK

    comfyui_url = settings.get_comfyui_server_url()

    proxy_route = settings.get_comfyui_reverse_proxy_route()
    proxy_route_bytes = bytes(proxy_route, "utf-8")

    async def async_iter_raw_patched(response):
        async for chunk in response.aiter_raw():
            replacements = [
                (b'/favicon', proxy_route_bytes + b'/favicon'),
                (b'from "/scripts/', b'from "' + proxy_route_bytes + b'/scripts/'),
                (b'from "/extensions/', b'from "' + proxy_route_bytes + b'/extensions/'),
                (b'from "/webui_scripts/', b'from "' + proxy_route_bytes + b'/webui_scripts/'),
                (proxy_route_bytes * 2, proxy_route_bytes),
            ]
            for substring, replacement in replacements:
                chunk = chunk.replace(substring, replacement)
            yield chunk

    web_client = httpx.AsyncClient(base_url=comfyui_url)

    async def reverse_proxy(request: Request):
        """Proxy incoming requests to another server."""
        base_path = request.url.path.replace(proxy_route, "", 1)
        url = httpx.URL(path=base_path, query=request.url.query.encode("utf-8"))
        rp_req = web_client.build_request(request.method, url, headers=request.headers.raw, content=await request.body())
        rp_resp = await web_client.send(rp_req, stream=True)
        return StreamingResponse(
            async_iter_raw_patched(rp_resp),
            status_code=rp_resp.status_code,
            headers=rp_resp.headers,
            background=BackgroundTask(rp_resp.aclose),
        )

    fast_api.add_route(f"{proxy_route}/{{path:path}}", reverse_proxy, ["GET", "POST", "PUT", "DELETE"])

    ws_comfyui_url = http_to_ws(comfyui_url)

    @fast_api.websocket(f"{proxy_route}/ws")
    async def websocket_endpoint(ws_client: WebSocket):
        """Websocket endpoint to proxy incoming WS requests."""
        await ws_client.accept()
        async with websockets.connect(ws_comfyui_url) as ws_server:

            async def listen_to_client():
                """Forward messages from client to server."""
                try:
                    while True:
                        data = await ws_client.receive_text()
                        await ws_server.send(data)
                except WebSocketDisconnect:
                    await ws_server.close()

            async def listen_to_server():
                """Forward messages from server to client."""
                try:
                    while True:
                        data = await ws_server.recv()
                        await ws_client.send_text(data)
                except ConnectionClosedOK:
                    pass

            await asyncio.gather(listen_to_client(), listen_to_server())

    print("[sd-webui-comfyui]", f"Created a reverse proxy route to ComfyUI: {proxy_route}")


def http_to_ws(url: str) -> str:
    """Convert http or https URL to its websocket equivalent."""
    from urllib.parse import urlparse, urlunparse

    parsed_url = urlparse(url)
    ws_scheme = 'wss' if parsed_url.scheme == 'https' else 'ws'
    ws_url = parsed_url._replace(scheme=ws_scheme)
    return urlunparse(ws_url) + "ws"
