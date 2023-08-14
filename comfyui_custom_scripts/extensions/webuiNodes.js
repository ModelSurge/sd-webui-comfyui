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
                for (const k in iframeInfo.webuiIoTypes.outputs) {
                    node.output_name.push(k);
                    node.output_is_list.push(false);
                    node.output.push(iframeInfo.webuiIoTypes.outputs[k]);
                }
            } else if (node.name === 'ToWebui') {
                for (const k in iframeInfo.webuiIoTypes.inputs) {
                    node.input.required[k] = [iframeInfo.webuiIoTypes.inputs[k]];
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
        for (const k in iframeInfo.webuiIoTypes.outputs) { ++i; }
        node.size = [256, 48 + 16 * i];
    },
});

app.registerExtension({
    name: "webui_io.WebuiInput",
});
