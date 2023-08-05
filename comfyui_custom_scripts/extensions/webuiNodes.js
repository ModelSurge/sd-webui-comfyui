import { app } from "/scripts/app.js";
import { iframeRegisteredEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiRequests.js";


function createVoidWidget(node, name) {
    const widget = {
        type: "customtext",
        name,
        get value() {
            return `${Math.random()}{Date.now()}`;
        },
        set value(x) {},
    };
    widget.parent = node;
    node.addCustomWidget(widget);

    return widget;
}

const ext = {
    name: "sd-webui-comfyui",
    async getCustomWidgets(app) {
        return {
            VOID(node, inputName) {
                createVoidWidget(node, inputName);
            },
        };
    },
    async beforeRegisterNodeDef(node, nodeData) {
        const iframeInfo = await iframeRegisteredEvent;

        if (!iframeInfo.webuiIoNodeNames.includes(nodeData.name)) {
            return;
        }

        nodeData.display_name = `${nodeData.display_name} - ${iframeInfo.workflowTypeDisplayName}`;
        node.title = nodeData.display_name;
    },
};

app.registerExtension(ext);
