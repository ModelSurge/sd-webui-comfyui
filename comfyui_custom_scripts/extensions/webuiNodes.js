import { app } from "/scripts/app.js";


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
        let display_name_patched = false;

        window.addEventListener("message", (event) => {
            const data = event.data;
            if (display_name_patched || !data || !data.workflowTypeId) {
                return;
            }

            nodeData.display_name = `${data.workflowTypeDisplayName}: ${nodeData.display_name}`;
            node.title = nodeData.display_name;
            display_name_patched = true;
        });
    },
};

app.registerExtension(ext);
