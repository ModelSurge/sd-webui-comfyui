import { app } from "/scripts/app.js";


const POLLING_TIMEOUT = 500;


const iframeRegisteredEvent = new Promise((resolve, reject) => {
    let resolved = false;
    const timeout = setTimeout(() => {
        reject('Cannot identify comfyui client: the webui host did not make a request on time.');
    }, 2000);
    window.addEventListener("message", event => {
        const data = event.data;
        if (resolved || !data || !data.workflowTypeId) {
            return;
        }

        clearTimeout(timeout);
        event.source.postMessage(data.workflowTypeId, event.origin);
        console.log(`[sd-webui-comfyui][comfyui] REGISTERED WORKFLOW TYPE ID - "${data.workflowTypeDisplayName}" (${data.workflowTypeId}) - ${data.webuiClientId}`);
        resolved = true;
        resolve(data);
    });
});

const appReadyEvent = new Promise(resolve => {
    const appReadyOrRecursiveSetTimeout = () => {
        if (app.graph) {
            resolve();
        }
        else {
            setTimeout(appReadyOrRecursiveSetTimeout, POLLING_TIMEOUT);
        }
    };
    appReadyOrRecursiveSetTimeout();
});


export {
    iframeRegisteredEvent,
    appReadyEvent,
}