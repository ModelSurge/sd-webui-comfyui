import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { patchUiEnv } from "/webui_scripts/sd-webui-comfyui/extensions/webuiPatches.js";
import { iframeRegisteredEvent, appReadyEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiEvents.js";


async function setupWebuiRequestsEnvironment() {
    const iframeInfo = await iframeRegisteredEvent;
    await appReadyEvent;
    await patchUiEnv(iframeInfo);

    function addWebuiRequestListener(type, callback, options) {
        api.addEventListener(`webui_${type}`, async (data) => {
            api.fetchApi("/sd-webui-comfyui/webui_ws_response", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                cache: "no-store",
                body: JSON.stringify({response: await callback(data)}),
            });
            console.log(`[sd-webui-comfyui] WEBUI REQUEST - ${iframeInfo.workflowTypeId} - ${type}`);
        }, options);
    };

    webuiRequests.forEach((request, type) => addWebuiRequestListener(type, request));
    await registerClientToWebui(iframeInfo.workflowTypeId, iframeInfo.webuiClientId, window.name);
    console.log(`[sd-webui-comfyui][comfyui] INITIALIZED WS - ${iframeInfo.displayName}`);
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
        await app.queuePrompt(json.detail.queueFront ? -1 : 0, 1);
    }],
    ["serialize_graph", (json) => {
        return app.graph.original_serialize();
    }],
    ["set_workflow", (json) => {
        app.loadGraphData(json.detail.workflow);
    }],
]);

setupWebuiRequestsEnvironment();
