import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


const request_map = new Map([
    ['/webui_request_queue_prompt', async (json) => {
        function graphContainsAllNodeTypes(workflow, nodeTypes) {
            const workflowTypes = workflow.nodes.map(node => node.type);
            return nodeTypes.every(nodeType => workflowTypes.includes(nodeType));
        }

        const workflow = JSON.parse(localStorage.getItem("workflow"));

        // check if the graph contains the node types we want
        // if no node types are specified, run the workflow
        console.log('worklow');
        if(!json.expectedNodeTypes || graphContainsAllNodeTypes(workflow, json.expectedNodeTypes)) {
            console.log('sending to webui');
            await app.queuePrompt(json.queueFront ? -1 : 0, 1);
            api.fetchApi('/webui_prompt_queued', { cache: "no-store" } );
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
            const response = await api.fetchApi("/webui_request", { cache: "no-store" });
            const json = await response.json();
            await request_map.get(json.request)(json);
        }
    }
    catch (e) {
        console.log(e);
    }
    finally {
        setTimeout(longPolling, 0);
    }
}

longPolling();