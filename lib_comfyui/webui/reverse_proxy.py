from lib_comfyui.webui import settings
from lib_comfyui import ipc, global_state


@ipc.restrict_to_process("webui")
def create_comfyui_proxy(fast_api):
    if not (global_state.enabled and global_state.reverse_proxy_enabled):
        return

    comfyui_url = settings.get_comfyui_server_url()
    proxy_route = settings.get_comfyui_reverse_proxy_route()

    create_http_reverse_proxy(fast_api, comfyui_url, proxy_route)
    create_ws_reverse_proxy(fast_api, comfyui_url, proxy_route)
    print("[sd-webui-comfyui]", f"Created a reverse proxy route to ComfyUI: {proxy_route}")


def create_http_reverse_proxy(fast_api, comfyui_url, proxy_route):
    from starlette.requests import Request
    from starlette.responses import StreamingResponse, Response
    from starlette.background import BackgroundTask
    import httpx

    web_client = httpx.AsyncClient(base_url=comfyui_url)

    # src: https://github.com/tiangolo/fastapi/issues/1788#issuecomment-1071222163
    async def reverse_proxy(request: Request):
        base_path = request.url.path.replace(proxy_route, "", 1)
        url = httpx.URL(path=base_path, query=request.url.query.encode("utf-8"))
        rp_req = web_client.build_request(request.method, url, headers=request.headers.raw, content=await request.body())
        try:
            rp_resp = await web_client.send(rp_req, stream=True)
        except httpx.ConnectError:
            return Response(status_code=404)
        else:
            return StreamingResponse(
                async_iter_raw_patched(rp_resp, proxy_route),
                status_code=rp_resp.status_code,
                headers=rp_resp.headers,
                background=BackgroundTask(rp_resp.aclose),
            )

    fast_api.add_route(f"{proxy_route}/{{path:path}}", reverse_proxy, ["GET", "POST", "PUT", "DELETE"])


async def async_iter_raw_patched(response, proxy_route):
    proxy_route_bytes = proxy_route.encode("utf-8")
    import_paths_to_patch = [
        "/scripts/",
        "/extensions/",
        "/webui_scripts/"
    ]
    patches = [
        (b'/favicon', proxy_route_bytes + b'/favicon'),
        *(
            (
                b'from "' + import_path.encode("utf-8"),
                b'from "' + proxy_route_bytes + import_path.encode("utf-8"),
            )
            for import_path in import_paths_to_patch
        ),
    ]

    async for chunk in response.aiter_raw():
        for substring, replacement in patches:
            chunk = chunk.replace(substring, replacement)
        yield chunk


def create_ws_reverse_proxy(fast_api, comfyui_url, proxy_route):
    from fastapi import WebSocket
    import websockets
    import asyncio
    from starlette.websockets import WebSocketDisconnect
    from websockets.exceptions import ConnectionClosedOK

    ws_comfyui_url = http_to_ws(comfyui_url)

    @fast_api.websocket(f"{proxy_route}/ws")
    async def websocket_endpoint(ws_client: WebSocket):
        await ws_client.accept()
        async with websockets.connect(ws_comfyui_url) as ws_server:

            async def listen_to_client():
                try:
                    while True:
                        data = await ws_client.receive_text()
                        await ws_server.send(data)
                except WebSocketDisconnect:
                    await ws_server.close()

            async def listen_to_server():
                try:
                    while True:
                        data = await ws_server.recv()
                        await ws_client.send_text(data)
                except ConnectionClosedOK:
                    pass

            await asyncio.gather(listen_to_client(), listen_to_server())


def http_to_ws(url: str) -> str:
    from urllib.parse import urlparse, urlunparse

    parsed_url = urlparse(url)
    ws_scheme = 'wss' if parsed_url.scheme == 'https' else 'ws'
    ws_url = parsed_url._replace(scheme=ws_scheme)
    return f"{urlunparse(ws_url)}/ws"
