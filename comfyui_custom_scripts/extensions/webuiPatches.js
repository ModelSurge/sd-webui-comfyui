import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { iframeRegisteredEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiEvents.js";
import { getTypesLength } from "/webui_scripts/sd-webui-comfyui/extensions/webuiTypes.js";


async function patchUiEnv(iframeInfo) {
    if (iframeInfo.workflowTypeId.endsWith('_txt2img') || iframeInfo.workflowTypeId.endsWith('_img2img')) {
        const menuToHide = document.querySelector('.comfy-menu');
        menuToHide.style.display = 'none';
        patchSavingMechanism();
    }

    await patchDefaultGraph(iframeInfo);
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

async function patchDefaultGraph(iframeInfo) {
    // preserve the normal default graph
    if (!iframeInfo.defaultWorkflow) {
        return;
    }

    app.original_loadGraphData = app.loadGraphData;
    const doLoadGraphData = graphData => {
        if (graphData !== "auto") {
            return app.original_loadGraphData(graphData);
        }

        app.graph.clear();

        const from_webui = LiteGraph.createNode("FromWebui");
        const to_webui = LiteGraph.createNode("ToWebui");

        app.graph.add(from_webui);
        app.graph.add(to_webui);

        const typesLength = getTypesLength(iframeInfo.webuiIoTypes.outputs);
        for (let i = 0; i < typesLength; ++i) {
            from_webui.connect(i, to_webui, i);
        }

        app.graph.arrange();
    };

    app.loadGraphData = (graphData) => {
        if (graphData) {
            return doLoadGraphData(graphData);
        }
        else {
            return doLoadGraphData(iframeInfo.defaultWorkflow);
        }
    };

    app.loadGraphData();
}


export {
    patchUiEnv,
}
