import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const request_map = new Map([
    ['/sd-webui-comfyui/webui_request_queue_prompt', async (json) => {
        function graphContainsPreciselyTheseNodeTypes(workflow, nodeTypes) {
            const workflowTypes = workflow.nodes.map(node => node.type);
            return nodeTypes.every(nodeType => {
                const amountInWorkflow = workflowTypes.reduce((accumulator, currentValue) => {
                    if (currentValue === nodeType.type) {
                        return accumulator + 1;
                    }
                    else {
                        return accumulator;
                    }
                }, 0);
                return amountInWorkflow == nodeType.count
            });
        }

        const workflow = JSON.parse(localStorage.getItem("workflow"));

        // check if the graph contains the node types we want
        // if no node types are specified, run the workflow
        if(!json.requiredNodeTypes || graphContainsPreciselyTheseNodeTypes(workflow, json.requiredNodeTypes)) {
            await app.queuePrompt(json.queueFront ? -1 : 0, 1);
            return 'queued_prompt_comfyui';
        }
    }],
    ['/sd-webui-comfyui/send_workflow_to_webui', async (json) => {
        return localStorage.getItem("workflow");
    }],
]);

async function longPolling(clientIdForWebui, startupResponse) {
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
                    cid: clientIdForWebui,
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
            longPolling(clientIdForWebui, clientResponse);
        }, 100);
    }
}


function onElementDomIdRegistered(callback) {
    let clientIdForWebui = undefined;

    window.addEventListener("message", (event) => {
        if(event.data.length > 50) return;
        if(clientIdForWebui) {
            event.source.postMessage(clientIdForWebui, event.origin);
            return;
        };
        clientIdForWebui = event.data;
        console.log(`[sd-webui-comfyui][comfyui] REGISTERED ELEMENT TAG ID - ${event.data}`);
        event.source.postMessage(clientIdForWebui, event.origin);
        hijackUiEnv(clientIdForWebui);
        const clientResponse = 'register_cid';
        console.log(`[sd-webui-comfyui][comfyui] INIT LONG POLLING SERVER - ${clientResponse}`);
        callback(event.data, clientResponse);
    });
}

function hijackUiEnv(clientIdForWebui) {
    const embededWorkflowFrameIds = [
        'comfyui_postprocess_txt2img',
        'comfyui_postprocess_img2img',
    ];
    if(embededWorkflowFrameIds.includes(clientIdForWebui)) {
        const menuToHide = document.querySelector('.comfy-menu');
        menuToHide.style.display = 'none';
        const original_localStorage_setItem = localStorage.setItem;
        localStorage.setItem = (item, data, ...args) => {
            if(item !== 'workflow' || clientIdForWebui === 'comfyui_general_tab') {
                return original_localStorage_setItem(item, data, ...args);
            }
            return;
        }
        fetch('/webui_scripts/sd-webui-comfyui/default_workflows/postprocess.json')
            .then(response => response.json())
            .then(data => app.loadGraphData(data));
    }
}

onElementDomIdRegistered(longPolling);