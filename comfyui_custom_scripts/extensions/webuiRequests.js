import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { patchUiEnv } from "/webui_scripts/sd-webui-comfyui/extensions/webuiPatches.js";
import { iframeRegisteredEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiEvents.js";


async function setupWebuiRequestsEnvironment() {
    const iframeInfo = await iframeRegisteredEvent;
    console.log(`[sd-webui-comfyui][comfyui] REGISTERED WORKFLOW TYPE ID - "${iframeInfo.workflowTypeDisplayName}" (${iframeInfo.workflowTypeId}) / ${iframeInfo.webuiClientId}`);

    await patchUiEnv(iframeInfo.workflowTypeId);
    const clientResponse = "register_cid";
    console.log(`[sd-webui-comfyui][comfyui] INIT WS - ${clientResponse}`);

    function addWebuiRequestListener(type, callback, options) {
        api.addEventListener(`webui_${type}`, async (data) => {
            api.fetchApi("/sd-webui-comfyui/webui_ws_response", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                cache: "no-store",
                body: JSON.stringify({response: await callback(params)}),
            });
            console.log(`[sd-webui-comfyui] WEBUI REQUEST - ${iframeInfo.workflowTypeId} - ${type}`);
        }, options);
    };

    webuiRequests.forEach((request, type) => addWebuiRequestListener(type, request));

    await registerClientToWebui(iframeInfo.workflowTypeId, iframeInfo.webuiClientId, window.name);
}

async function registerClientToWebui(workflowTypeId, webuiClientId, sid) {
    await api.fetchApi("/sd-webui-comfyui/webui_register_client", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        cache: "no-store",
        body: JSON.stringify({
            workflowTypeId,
            webuiClientId,
            sid,
        }),
    });
}

const webuiRequests = new Map([
    ["queue_prompt", async (json) => {
            await app.queuePrompt(json.queueFront ? -1 : 0, 1);
    }],
    ["serialize_graph", (json) => {
            console.log("got request! Serialize graph");
            return app.graph.original_serialize();
    }],
    ["set_workflow", (json) => {
            app.loadGraphData(json.workflow);
    }],
]);

setupWebuiRequestsEnvironment();
