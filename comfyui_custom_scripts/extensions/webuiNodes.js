import { app } from "/scripts/app.js";
import { iframeRegisteredEvent } from "/extensions/webui_scripts/sd-webui-comfyui/extensions/webuiEvents.js";
import { isString, getTypesLength } from "/extensions/webui_scripts/sd-webui-comfyui/extensions/webuiTypes.js";


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
        }
        catch {
            return;
        }

        const nodes = webuiIoNodeNames.map(name => defs[name]);
        for (const node of nodes) {
            node.display_name = `${node.display_name} - ${iframeInfo.displayName}`;

            if (node.name === 'FromWebui') {
                let outputs = iframeInfo.webuiIoTypes.outputs;
                if (isString(outputs)) {
                    outputs = [outputs];
                }
                const are_types_array = Array.isArray(outputs);
                for (const k in outputs) {
                    const v = outputs[k];
                    node.output_name.push(are_types_array ? v : k);
                    node.output_is_list.push(false);
                    node.output.push(v);
                }
            }
            else if (node.name === 'ToWebui') {
                let inputs = iframeInfo.webuiIoTypes.inputs;
                if (isString(inputs)) {
                    node.input.required[inputs] = [inputs];
                }
                else {
                    for (const k in inputs) {
                        const v = inputs[k];
                        node.input.required[k] = [v];
                    }
                }
            }
        }
    },
    async nodeCreated(node) {
        let iframeInfo = null;

        try {
            iframeInfo = await iframeRegisteredEvent;
        } catch {
            return;
        }

        if (!webuiIoNodeNames.includes(node.type)) {
            return;
        }

        const maxIoLength = Math.max(
            getTypesLength(iframeInfo.webuiIoTypes.outputs),
            getTypesLength(iframeInfo.webuiIoTypes.inputs),
        );
        // 260 and 40 are empirical values that seem to work
        node.size = [260, 40 + distanceBetweenIoSlots * maxIoLength];
    },
    async setup() {
        app.loadGraphData();
    },
});

const webuiIoNodeNames = [
    'FromWebui',
    'ToWebui',
];

const distanceBetweenIoSlots = 20;
