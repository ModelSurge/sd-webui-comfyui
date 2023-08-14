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
        }
    },
    async nodeCreated(node) {
        let iframeInfo = null;
        let output_type = null;
        let input_type = null;

        try {
            iframeInfo = await iframeRegisteredEvent;
            output_type = iframeInfo.webuiIoTypes.outputs[0];
            input_type = iframeInfo.webuiIoTypes.inputs[0];
        } catch {
            output_type = undefined;
            input_type = undefined;
        }

        if (node.type.includes('From')) {
            node.outputs[0].type = output_type;
            if (output_type === input_type) {
                for (const link of node.outputs[0].links) {
                    if (output_type === undefined) {
                        node.disconnectInput(link.target_slot);
                    }
                    app.graph.links[link].type = output_type;
                }
            }
        } else if (node.type.includes('To')) {
            node.inputs[0].type = input_type;
            app.graph.links[node.inputs[0].link].type = input_type;
        }
    },
});

app.registerExtension({
    name: "webui_io.WebuiInput",
});
