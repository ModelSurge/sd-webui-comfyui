import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { appReadyEvent, iframeRegisteredEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiEvents.js";


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

    // preserve the normal default graph
    if (!defaultGraph) {
        return;
    }

    const iframeInfo = await iframeRegisteredEvent;

    app.original_loadGraphData = app.loadGraphData;
    app.loadGraphData = (graphData) => {
        if (graphData) {
            return app.original_loadGraphData(graphData);
        }

        if (defaultGraph !== "auto") {
            return app.original_loadGraphData(defaultGraph);
        }

        app.graph.clear();

        const from_webui = LiteGraph.createNode("FromWebui");
        const to_webui = LiteGraph.createNode("ToWebui");

        app.graph.add(from_webui);
        app.graph.add(to_webui);

        let outputs = iframeInfo.webuiIoTypes.outputs;
        if (typeof outputs === "string" || outputs instanceof String) {
            outputs = [outputs];
        } else if (!Array.isArray(outputs)) {
            outputs = Object.keys(outputs);
        }
        console.log(outputs);
        for (let i in outputs) {
            i = parseInt(i);
            from_webui.connect(i, to_webui, i);
        }

        app.graph.arrange();
    };

    app.loadGraphData();
}


export {
    patchUiEnv,
}
