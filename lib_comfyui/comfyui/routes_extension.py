import asyncio
import json
from lib_comfyui import parallel_utils, ipc, global_state, comfyui_context, torch_utils, external_code
from lib_comfyui.comfyui.iframe_requests import ComfyuiIFrameRequests


def polling_server_patch(instance, loop):
    from aiohttp import web

    ComfyuiIFrameRequests.init_request_listener(loop)

    @instance.routes.post("/sd-webui-comfyui/webui_polling_server")
    async def webui_polling_server(response):
        response = await response.json()
        if 'webui_client_id' not in response:
            return web.json_response(status=422)
        if 'workflow_type_id' not in response:
            return web.json_response(status=422)
        if 'response' not in response:
            return web.json_response(status=422)

        webui_client_id = response['webui_client_id']
        workflow_type_id = response['workflow_type_id']

        if isinstance(response, dict) and 'error' in response['response']:
            print(f"[sd-webui-comfyui] Client {workflow_type_id}-{webui_client_id} encountered an error - \n{response['response']['error']}")

        response_value = response['response']

        await ComfyuiIFrameRequests.handle_response(response)

        if (
            response_value == 'register_cid' or
            webui_client_id not in ComfyuiIFrameRequests.workflow_type_ids or
            workflow_type_id not in ComfyuiIFrameRequests.workflow_type_ids[webui_client_id]
        ):
            ComfyuiIFrameRequests.add_client(workflow_type_id, webui_client_id)

        request = await ComfyuiIFrameRequests.create_client_request(workflow_type_id, webui_client_id)
        return web.json_response(request)


def workflow_type_ops_server_patch(instance, _loop):
    from aiohttp import web

    @instance.routes.get("/sd-webui-comfyui/default_workflow")
    async def get_default_workflow(request):
        params = request.rel_url.query
        workflow_type_id = params['workflow_type_id']

        try:
            res = web.json_response(json.loads(external_code.get_default_workflow_json(workflow_type_id)))
            return res
        except ValueError as e:
            return web.json_response(status=422, reason=str(e))


def add_server__init__patch(callback):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        original_init(self, loop, *args, **kwargs)
        callback(self, loop, *args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__


def patch_server_routes():
    add_server__init__patch(polling_server_patch)
    add_server__init__patch(workflow_type_ops_server_patch)
