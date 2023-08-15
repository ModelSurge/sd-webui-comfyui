import asyncio
import json
from lib_comfyui import external_code
from lib_comfyui.comfyui.iframe_requests import ComfyuiIFrameRequests


def patch_server_routes():
    add_server__init__patch(websocket_handler_patch)
    add_server__init__patch(workflow_type_ops_server_patch)


def add_server__init__patch(callback):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(self, loop: asyncio.AbstractEventLoop, *args, **kwargs):
        original_init(self, loop, *args, **kwargs)
        callback(self, loop, *args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__


def websocket_handler_patch(instance, _loop):
    from aiohttp import web

    ComfyuiIFrameRequests.server_instance = instance

    @instance.routes.post("/sd-webui-comfyui/webui_register_client")
    async def webui_register_client(request):
        request = await request.json()

        ComfyuiIFrameRequests.register_client(request)

        return web.json_response()

    @instance.routes.post("/sd-webui-comfyui/webui_ws_response")
    async def webui_ws_response(response):
        response = await response.json()

        ComfyuiIFrameRequests.handle_response(response['response'] if 'response' in response else response)

        return web.json_response(status=200)


def workflow_type_ops_server_patch(instance, _loop):
    from aiohttp import web

    @instance.routes.get("/sd-webui-comfyui/workflow_type")
    async def get_workflow_type(request):
        workflow_type_id = request.rel_url.query.get("workflowTypeId", None)
        workflow_type = next(iter(
            workflow_type
            for workflow_type in external_code.get_workflow_types()
            if workflow_type_id in workflow_type.get_ids()
        ))
        return web.json_response({
            "displayName": workflow_type.display_name,
            "webuiIoTypes": {
                "inputs": list(workflow_type.input_types) if isinstance(workflow_type.input_types, tuple) else workflow_type.input_types,
                "outputs": list(workflow_type.types) if isinstance(workflow_type.types, tuple) else workflow_type.types,
            },
            "defaultWorkflow": json.loads(external_code.get_default_workflow_json(workflow_type_id))
        })
