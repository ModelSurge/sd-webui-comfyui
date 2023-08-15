import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


const POLLING_TIMEOUT = 500;


const appReadyEvent = new Promise(async (resolve) => {
    const appReadyOrRecursiveSetTimeout = () => {
        if (app.graph && window.name) {
            resolve();
        }
        else {
            setTimeout(appReadyOrRecursiveSetTimeout, POLLING_TIMEOUT);
        }
    };
    appReadyOrRecursiveSetTimeout();
});

const iframeRegisteredEvent = new Promise(async (resolve, reject) => {
    const searchParams = new URLSearchParams(window.location.search);
    const workflowTypeId = searchParams.get("workflowTypeId");
    const webuiClientId = searchParams.get("webuiClientId");

    if (!workflowTypeId || !webuiClientId) {
        reject("Cannot identify comfyui client: search params missing.");
    }
    else {
        const workflowTypeInfo = await fetchWorkflowTypeInfo(workflowTypeId);
        resolve({
            workflowTypeId,
            webuiClientId,
            ...workflowTypeInfo,
        });
    }
});

async function fetchWorkflowTypeInfo(workflowTypeId) {
    const response = await api.fetchApi("/sd-webui-comfyui/workflow_type?" + new URLSearchParams({
        workflowTypeId,
    }), {
        method: "GET",
        headers: {"Content-Type": "application/json"},
        cache: "no-store",
    });
    return await response.json();
}


export {
    iframeRegisteredEvent,
    appReadyEvent,
}
