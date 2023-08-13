import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { appReadyEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiEvents.js";


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


export {
    patchUiEnv,
}