import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


const POLLING_TIMEOUT = 500;


const request_map = new Map([
    ['/sd-webui-comfyui/webui_request_timeout', async (json) => {
        return 'timeout';
    }],
    ['/sd-webui-comfyui/webui_request_queue_prompt', async (json) => {
        const workflow = app.graph.serialize();
        await app.queuePrompt(json.queueFront ? -1 : 0, 1);
        return 'queued_prompt_comfyui';
    }],
    ['/sd-webui-comfyui/webui_request_serialize_graph', async (json) => {
        return app.graph.original_serialize();
    }],
    ['/sd-webui-comfyui/webui_request_set_workflow', async (json) => {
        app.loadGraphData(json.workflow);
        return 'success';
    }],
]);

async function longPolling(workflowTypeId, webuiClientKey, startupResponse) {
    let clientResponse = startupResponse;

    try {
        while(true) {
            const response = await api.fetchApi("/sd-webui-comfyui/webui_polling_server", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                cache: "no-store",
                body: JSON.stringify({
                    workflow_type_id: workflowTypeId,
                    webui_client_id: webuiClientKey,
                    response: clientResponse,
                }),
            });
            const json = await response.json();
            if (json.request !== '/sd-webui-comfyui/webui_request_timeout') {
                console.log(`[sd-webui-comfyui] WEBUI REQUEST - ${workflowTypeId} - ${json.request}`);
            }
            clientResponse = await request_map.get(json.request)(json);
        }
    }
    catch (e) {
        console.error(e);
        clientResponse = {error: e};
    }
    finally {
        setTimeout(() => {
            longPolling(workflowTypeId, webuiClientKey, clientResponse);
        }, 100);
    }
}

async function onElementDomIdRegistered(callback) {
    const iframeInfo = await iframeRegisteredEvent;
    console.log(`[sd-webui-comfyui][comfyui] REGISTERED WORKFLOW TYPE ID - "${iframeInfo.workflowTypeDisplayName}" (${iframeInfo.workflowTypeId}) / ${iframeInfo.webuiClientId}`);

    event.source.postMessage(iframeInfo.workflowTypeId, event.origin);
    await patchUiEnv(iframeInfo.workflowTypeId);
    const clientResponse = 'register_cid';
    console.log(`[sd-webui-comfyui][comfyui] INIT LONG POLLING SERVER - ${clientResponse}`);
    await callback(iframeInfo.workflowTypeId, iframeInfo.webuiClientId, clientResponse);
}

async function patchUiEnv(workflowTypeId) {
    await appReadyEvent;

    if (workflowTypeId.endsWith('_txt2img') || workflowTypeId.endsWith('_img2img')) {
        const menuToHide = document.querySelector('.comfy-menu');
        menuToHide.style.display = 'none';
        patchSavingMechanism();
    }

    await patchDefaultGraph(workflowTypeId);
}

function patchSavingMechanism() {
    app.graph.original_serialize = app.graph.serialize;
    app.graph.patched_serialize = () => JSON.parse(localStorage.getItem('workflow'));
    app.graph.serialize = app.graph.patched_serialize;

    app.original_graphToPrompt = app.graphToPrompt;
    app.patched_graphToPrompt = () => {
        app.graph.serialize = app.graph.original_serialize;
        const result = app.original_graphToPrompt();
        app.graph.serialize = app.graph.patched_serialize;
        return result;
    };
    app.graphToPrompt = app.patched_graphToPrompt;

    const saveButton = document.querySelector('#comfy-save-button');
    saveButton.removeAttribute('id');
    const comfyParent = saveButton.parentElement;
    const muahahaButton = document.createElement('button');
    muahahaButton.setAttribute('id', 'comfy-save-button');
    comfyParent.appendChild(muahahaButton);
    muahahaButton.click = () => {
        app.graph.serialize = app.graph.original_serialize;
        saveButton.click();
        app.graph.serialize = app.graph.patched_serialize;
    };
}

async function patchDefaultGraph(workflowTypeId) {
    const response = await api.fetchApi("/sd-webui-comfyui/default_workflow?" + new URLSearchParams({
        workflow_type_id: workflowTypeId,
    }), {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
        cache: "no-store",
    });
    const defaultGraph = await response.json();
    if (!defaultGraph) {
        return;
    }

    app.original_loadGraphData = app.loadGraphData;
    app.loadGraphData = (graphData) => {
        if (!graphData) {
            return app.original_loadGraphData(defaultGraph);
        } else {
            return app.original_loadGraphData(graphData);
        }
    };

    app.loadGraphData();
}

const iframeRegisteredEvent = new Promise(resolve => {
    let resolved = false;
    window.addEventListener("message", event => {
        const data = event.data;
        if (resolved || !data || !data.workflowTypeId) {
            return;
        }

        resolved = true;
        resolve(data);
    });
});

const appReadyEvent = new Promise(resolve => {
    const appReadyOrRecursiveSetTimeout = () => {
        if (app.graph) {
            resolve();
        } else {
            setTimeout(appReadyOrRecursiveSetTimeout, POLLING_TIMEOUT);
        }
    };
    appReadyOrRecursiveSetTimeout();
});

onElementDomIdRegistered(longPolling);

export {
    iframeRegisteredEvent,
}
