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

            if (node.name === 'FromWebui') {
                let outputs = iframeInfo.webuiIoTypes.outputs;
                if (typeof outputs === "string" || outputs instanceof String) {
                    outputs = [outputs];
                }
                const are_types_array = Array.isArray(outputs);
                for (const k in outputs) {
                    const v = outputs[k];
                    node.output_name.push(are_types_array ? v : k);
                    node.output_is_list.push(false);
                    node.output.push(v);
                }
            } else if (node.name === 'ToWebui') {
                let inputs = iframeInfo.webuiIoTypes.inputs;
                if (typeof inputs === "string" || inputs instanceof String) {
                    node.input.required[inputs] = [inputs];
                } else {
                    for (const k in inputs) {
                        const v = inputs[k];
                        node.input.required[k] = [v];
                    }
                }
            }
            console.log(node);
        }
    },
    async nodeCreated(node) {
        let iframeInfo = null;

        try {
            iframeInfo = await iframeRegisteredEvent;
        } catch {
            return;
        }

        let i = 0;
        const outputs = iframeInfo.webuiIoTypes.outputs;
        if (typeof outputs === "string" || outputs instanceof String) {
            i = 1;
        } else if (Array.isArray(outputs)) {
            i = outputs.length;
        } else {
            for (const k in outputs) { ++i; }
        }
        let j = 0;
        const inputs = iframeInfo.webuiIoTypes.outputs;
        if (typeof outputs === "string" || outputs instanceof String) {
            j = 1;
        } else if (Array.isArray(outputs)) {
            j = outputs.length;
        } else {
            for (const k in outputs) { ++j; }
        }
        node.size = [256, 48 + 16 * Math.max(i, j)];
    },
});
