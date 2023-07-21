import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const startup_workflow = localStorage.getItem('workflow');

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

async function longPolling(thisClientId, webuiClientKey, startupResponse) {
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
                    cid: thisClientId,
                    key: webuiClientKey,
                    request: clientResponse,
                }),
            });
            const json = await response.json();
            console.log(`[sd-webui-comfyui] WEBUI REQUEST - ${json.request}`);
            clientResponse = await request_map.get(json.request)(json);
        }
    }
    catch (e) {
        console.log(e);
        clientResponse = {error: e};
    }
    finally {
        setTimeout(() => {
            longPolling(thisClientId, webuiClientKey, clientResponse);
        }, 100);
    }
}


function onElementDomIdRegistered(callback) {
    let thisClientId = undefined;
    let webuiClientKey = undefined;

    window.addEventListener("message", (event) => {
        if(event.data.length > 100) return;
        if(thisClientId) {
            event.source.postMessage(thisClientId, event.origin);
            return;
        };
        const messageData = event.data.split('.');
        thisClientId = messageData[0];
        webuiClientKey = messageData[1];
        console.log(`[sd-webui-comfyui][comfyui] REGISTERED ELEMENT TAG ID - ${thisClientId}/${webuiClientKey}`);
        event.source.postMessage(thisClientId, event.origin);
        hijackUiEnv(thisClientId);
        const clientResponse = 'register_cid';
        console.log(`[sd-webui-comfyui][comfyui] INIT LONG POLLING SERVER - ${clientResponse}`);
        callback(thisClientId, webuiClientKey, clientResponse);
    });
}

function hijackUiEnv(thisClientId) {
    const embededWorkflowFrameIds = [
        'comfyui_postprocess_txt2img',
        'comfyui_postprocess_img2img',
    ];
    if(embededWorkflowFrameIds.includes(thisClientId)) {
        const menuToHide = document.querySelector('.comfy-menu');
        menuToHide.style.display = 'none';
        hijackLocalStorage(thisClientId, embededWorkflowFrameIds);
        setTimeout(() => fetch('/webui_scripts/sd-webui-comfyui/default_workflows/postprocess.json')
            .then(response => response.json())
            .then(data => app.loadGraphData(data)), 500);
    }
    else {
        // ComfyUI has an interval for setting the local storage, but we have many ComfyUI's in parallel, so we restore
        // the prvious correct state here for the tab
        setTimeout(() => app.loadGraphData(JSON.parse(startup_workflow)), 500);
    }
}

function hijackLocalStorage(thisClientId, embededWorkflowFrameIds) {
    const original_localStorage_setItem = localStorage.setItem;
    localStorage.setItem = (item, data, ...args) => {
        if(item === 'workflow' && ! embededWorkflowFrameIds.includes(thisClientId)) {
            return original_localStorage_setItem(item, data, ...args);
        }
        return;
    }
}

onElementDomIdRegistered(longPolling);