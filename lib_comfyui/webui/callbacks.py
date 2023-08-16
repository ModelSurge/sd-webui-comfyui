from urllib.parse import urlparse, urlunparse

from lib_comfyui import comfyui_process, ipc, global_state, external_code
from lib_comfyui.webui import tab, settings, workflow_patcher, reverse_proxy
from websockets.exceptions import ConnectionClosedOK


@ipc.restrict_to_process('webui')
def register_callbacks():
    from modules import script_callbacks
    script_callbacks.on_ui_tabs(on_ui_tabs)
    script_callbacks.on_ui_settings(on_ui_settings)
    script_callbacks.on_after_component(on_after_component)
    script_callbacks.on_app_started(on_app_started)
    script_callbacks.on_script_unloaded(on_script_unloaded)


@ipc.restrict_to_process('webui')
def on_ui_tabs():
    return tab.create_tab()


@ipc.restrict_to_process('webui')
def on_ui_settings():
    return settings.create_section()


@ipc.restrict_to_process('webui')
def on_after_component(*args, **kwargs):
    return workflow_patcher.watch_prompts(*args, **kwargs)


@ipc.restrict_to_process('webui')
def on_app_started(_gr_root, fast_api):
    comfyui_process.start()
    reverse_proxy.register_comfyui(fast_api)

    # from starlette.requests import Request
    # from starlette.responses import StreamingResponse
    # from starlette.background import BackgroundTask
    #
    # import httpx
    #
    # client = httpx.AsyncClient(base_url=settings.get_comfyui_client_url())
    #
    # async def reverse_proxy(request: Request):
    #     base_path = request.url.path.split("/")
    #     base_path = "/".join(base_path[:1] + base_path[3:])
    #     url = httpx.URL(
    #         path=base_path,
    #         query=request.url.query.encode("utf-8"),
    #     )
    #     rp_req = client.build_request(
    #         request.method,
    #         url,
    #         headers=request.headers.raw,
    #         content=await request.body(),
    #     )
    #
    #     async def aiter_raw_patched():
    #         async for chunk in rp_resp.aiter_raw():
    #             # Adjust this URL modification as necessary:
    #             modified_chunk = chunk.replace(
    #                 b'from "/scripts/', b'from "/sd-webui-comfyui/comfyui-proxy/scripts/'
    #             )
    #             modified_chunk = modified_chunk.replace(
    #                 b'/favicon', b'/sd-webui-comfyui/comfyui-proxy/favicon'
    #             )
    #             modified_chunk = modified_chunk.replace(
    #                 b'from "/extensions/', b'from "/sd-webui-comfyui/comfyui-proxy/extensions/'
    #             )
    #             modified_chunk = modified_chunk.replace(
    #                 b'from "/webui_scripts/', b'from "/sd-webui-comfyui/comfyui-proxy/webui_scripts/'
    #             )
    #             modified_chunk = modified_chunk.replace(
    #                 b'sd-webui-comfyui/comfyui-proxy/sd-webui-comfyui/comfyui-proxy', b'sd-webui-comfyui/comfyui-proxy'
    #             )
    #             yield modified_chunk
    #
    #     rp_resp = await client.send(rp_req, stream=True)
    #     return StreamingResponse(
    #         aiter_raw_patched(),
    #         status_code=rp_resp.status_code,
    #         headers=rp_resp.headers,
    #         background=BackgroundTask(rp_resp.aclose),
    #     )
    #
    # fast_api.add_route("/sd-webui-comfyui/comfyui-proxy/{path:path}", reverse_proxy, ["GET", "POST", "PUT", "DELETE"])
    #
    # from fastapi import WebSocket
    # import websockets
    # import asyncio
    #
    # def http_to_ws(url: str) -> str:
    #     parsed_url = urlparse(url)
    #
    #     if parsed_url.scheme == 'https':
    #         ws_scheme = 'wss'
    #     else:
    #         ws_scheme = 'ws'
    #
    #     ws_url = parsed_url._replace(scheme=ws_scheme)
    #     return urlunparse(ws_url) + "ws"
    #
    # ws_client_url = http_to_ws(settings.get_comfyui_client_url())
    #
    # @fast_api.websocket("/sd-webui-comfyui/comfyui-proxy/ws")
    # async def websocket_endpoint(websocket: WebSocket):
    #     await websocket.accept()
    #
    #     async with websockets.connect(ws_client_url) as ws_server:
    #         from starlette.websockets import WebSocketDisconnect
    #
    #         async def listen_to_client():
    #             while True:
    #                 try:
    #                     data = await websocket.receive_text()
    #                     await ws_server.send_text(data)
    #                 except WebSocketDisconnect:
    #                     await ws_server.close()
    #                     break
    #
    #         async def listen_to_server():
    #             while True:
    #                 try:
    #                     data = await ws_server.recv()
    #                     await websocket.send_text(data)
    #                 except ConnectionClosedOK:
    #                     break
    #
    #         await asyncio.gather(listen_to_client(), listen_to_server())

@ipc.restrict_to_process('webui')
def on_script_unloaded():
    comfyui_process.stop()
    workflow_patcher.clear_patches()
    global_state.is_ui_instantiated = False
    external_code.clear_workflow_types()
