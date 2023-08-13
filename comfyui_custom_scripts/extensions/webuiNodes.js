import { app } from "/scripts/app.js";
import { iframeRegisteredEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiRequests.js";


function createVoidWidget(node, name) {
    const widget = {
        type: "customtext",
        name,
        get value() {
            return `${Math.random()}${Date.now()}`;
        },
        set value(x) {},
    };
    widget.parent = node;
    node.addCustomWidget(widget);

    return widget;
}

app.registerExtension({
    name: "sd-webui-comfyui",
    async getCustomWidgets(app) {
        return {
            VOID(node, inputName) {
                createVoidWidget(node, inputName);
            },
        };
    },
    async nodeCreated(node) {
        let iframeInfo = null;
        try {
            iframeInfo = await iframeRegisteredEvent;
        } catch {
            return;
        }

        if (!iframeInfo.webuiIoNodeNames.includes(node.type)) {
            return;
        }

        if (node.type.includes('From')) {
            node.outputs[0].type = iframeInfo.webuiIoTypes.outputs[0];
        } else if (node.type.includes('To')) {
            node.inputs[0].type = iframeInfo.webuiIoTypes.inputs[0];
        }
    },
    async addCustomNodeDefs(defs) {
        let iframeInfo = null;

        try {
            iframeInfo = await iframeRegisteredEvent;
        } catch {}

        if (!iframeInfo) {
            return;
        }

        const nodes = iframeInfo.webuiIoNodeNames.map(name => defs[name]);
        for (const node of nodes) {
            node.display_name = `${node.display_name} - ${iframeInfo.workflowTypeDisplayName}`;
        }
    },
});

app.registerExtension({
    name: "webui_io.WebuiInput",
});
