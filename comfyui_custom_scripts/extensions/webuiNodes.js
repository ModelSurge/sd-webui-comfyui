import { app } from "/scripts/app.js";
import { iframeRegisteredEvent } from "/webui_scripts/sd-webui-comfyui/extensions/webuiRequests.js";


const webuiIoNodeNames = [
    'FromWebui',
    'ToWebui',
];


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
    async addCustomNodeDefs(defs) {
        let iframeInfo = null;

        try {
            iframeInfo = await iframeRegisteredEvent;
        } catch {
            return;
        }

        const nodes = webuiIoNodeNames.map(name => defs[name]);
        for (const node of nodes) {
            node.display_name = `${node.display_name} - ${iframeInfo.workflowTypeDisplayName}`;

            if (node.name.includes('From')) {
                node.output[0] = iframeInfo.webuiIoTypes.outputs[0];
            } else if (node.name.includes('To')) {
                node.input.required.output[0] = iframeInfo.webuiIoTypes.inputs[0];
            }
            console.log(node);
        }
    },
    async nodeCreated(node) {
        node.size = [256, 64];
    },
});

app.registerExtension({
    name: "webui_io.WebuiInput",
});
