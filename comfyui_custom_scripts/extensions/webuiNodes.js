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

            if (node.name.includes('From')) {
                node.output[0] = iframeInfo.webuiIoTypes.outputs[0];
            } else if (node.name.includes('To')) {
                node.input.required.output[0] = iframeInfo.webuiIoTypes.inputs[0];
            }
        }
    },
    async nodeCreated(node) {
        let iframeInfo = null;
        try {
            iframeInfo = await iframeRegisteredEvent;
        } catch {
            // TODO: disconnect nodes and patch their connection types to be `undefined`
            return;
        }

        if (!iframeInfo.webuiIoNodeNames.includes(node.type)) {
            return;
        }

        const output_type = iframeInfo.webuiIoTypes.outputs[0];
        const input_type = iframeInfo.webuiIoTypes.inputs[0];

        if (node.type.includes('From')) {
            node.outputs[0].type = output_type;
            if (output_type == input_type) {
                for (const link of node.outputs[0].links) {
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
