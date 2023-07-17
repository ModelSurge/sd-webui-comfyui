import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";


function createVoidWidget(node, name) {
    const widget = {
        i: 0,
        type: "customtext",
        name,
        get value() {
            widget.requestUpdate();
            return `${widget.i}`;
        },
        set value(x) {},
        requestUpdate() {
            widget.i++;
        }
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
};

app.registerExtension(ext);
