import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


const POLLING_TIMEOUT = 500;


const request_map = new Map([
    ['/sd-webui-comfyui/webui_request_queue_prompt', async (json) => {
        const workflow = app.graph.serialize();
        await app.queuePrompt(json.queueFront ? -1 : 0, 1);
        return 'queued_prompt_comfyui';
    }],
    ['/sd-webui-comfyui/send_workflow_to_webui', async (json) => {
        return localStorage.getItem("workflow");
    }],
]);

async function longPolling(thisWorkflowTypeId, webuiClientKey, startupResponse) {
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
                    workflow_type_id: thisWorkflowTypeId,
                    webui_client_id: webuiClientKey,
                    request: clientResponse,
                }),
            });
            const json = await response.json();
            console.log(`[sd-webui-comfyui] WEBUI REQUEST - ${thisWorkflowTypeId} - ${json.request}`);
            clientResponse = await request_map.get(json.request)(json);
        }
    }
    catch (e) {
        console.log(e);
        clientResponse = {error: e};
    }
    finally {
        setTimeout(() => {
            longPolling(thisWorkflowTypeId, webuiClientKey, clientResponse);
        }, 100);
    }
}


function onElementDomIdRegistered(callback) {
    let thisWorkflowTypeId = undefined;
    let webuiClientKey = undefined;

    window.addEventListener("message", (event) => {
        if(event.data.length > 100) return;
        if(thisWorkflowTypeId) {
            event.source.postMessage(thisWorkflowTypeId, event.origin);
            return;
        };
        const messageData = event.data.split('.');
        thisWorkflowTypeId = messageData[0];
        webuiClientKey = messageData[1];
        console.log(`[sd-webui-comfyui][comfyui] REGISTERED WORKFLOW TYPE ID - ${thisWorkflowTypeId}/${webuiClientKey}`);
        event.source.postMessage(thisWorkflowTypeId, event.origin);
        patchUiEnv(thisWorkflowTypeId);
        const clientResponse = 'register_cid';
        console.log(`[sd-webui-comfyui][comfyui] INIT LONG POLLING SERVER - ${clientResponse}`);
        callback(thisWorkflowTypeId, webuiClientKey, clientResponse);
    });
}

function patchUiEnv(thisWorkflowTypeId) {
    if(thisWorkflowTypeId !== 'sandbox_tab') {
        const menuToHide = document.querySelector('.comfy-menu');
        menuToHide.style.display = 'none';
        patchSavingMechanism();
        loadDefaultGraph(thisWorkflowTypeId);
    }
}

function patchSavingMechanism() {
    if(app.graph === undefined) {
        setTimeout(patchSavingMechanism, POLLING_TIMEOUT);
        return;
    }

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

async function loadDefaultGraph(workflowTypeId) {
    const response = await api.fetchApi("/sd-webui-comfyui/default_workflow?" + new URLSearchParams({
        workflow_type_id: workflowTypeId,
    }), {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
        cache: "no-store",
    });
    const response_json = await response.json();
    if (response_json === null) {
        return;
    }
    app.loadGraphData(response_json);
}

onElementDomIdRegistered(longPolling);
