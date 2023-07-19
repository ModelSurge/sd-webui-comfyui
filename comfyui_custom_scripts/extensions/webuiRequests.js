import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


// https://stackoverflow.com/questions/105034/how-do-i-create-a-guid-uuid
function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });
}


const clientUuidForWebui = uuidv4();
var clientResponse = undefined;

const request_map = new Map([
    ['/webui_request_queue_prompt', async (json) => {
        function graphContainsAllNodeTypes(workflow, nodeTypes) {
            const workflowTypes = workflow.nodes.map(node => node.type);
            return nodeTypes.every(nodeType => workflowTypes.includes(nodeType));
        }

        const workflow = JSON.parse(localStorage.getItem("workflow"));

        // check if the graph contains the node types we want
        // if no node types are specified, run the workflow
        if(!json.expectedNodeTypes || graphContainsAllNodeTypes(workflow, json.expectedNodeTypes)) {
            await app.queuePrompt(json.queueFront ? -1 : 0, 1);
            clientResponse = 'queued_prompt_comfyui';
        }
    }],
    ['/send_workflow_to_webui', async (json) => {
        const workflow = localStorage.getItem("workflow");
        await api.fetchApi(json.request, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            cache: "no-store",
            body: JSON.stringify(workflow),
        });
    }],
]);


async function longPolling() {
    try {
        while(true) {
            const response = await api.fetchApi("/webui_request", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                cache: "no-store",
                body: JSON.stringify({
                    cid: clientUuidForWebui,
                    request: clientResponse,
                }),
            });
            clientResponse = undefined;
            const json = await response.json();
            console.log(`[sd-webui-comfyui] WEBUI REQUEST - ${json.request}`);
            await request_map.get(json.request)(json);
        }
    }
    catch (e) {
        console.log(e);
    }
    finally {
        setTimeout(longPolling, 100);
    }
}

longPolling();