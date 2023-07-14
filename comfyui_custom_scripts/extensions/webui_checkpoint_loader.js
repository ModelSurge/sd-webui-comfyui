import { app } from "/scripts/app.js";


function addHiddenMultilineWidget(node, name, app) {
	const widget = {
		type: "customtext",
		name,
		get value() {
			return this.inputEl.value;
		},
		set value(x) {
			this.inputEl.value = x;
		},
		draw: function (ctx, _, widgetWidth, y, widgetHeight) {},
	};
	widget.inputEl = document.createElement("textarea");
	widget.inputEl.classList.add('hidden-multiline-input');
	widget.inputEl.style.display = 'none';
	widget.inputEl.value = '';
	widget.inputEl.placeholder = '';
	widget.parent = node;
	document.body.appendChild(widget.inputEl);

	node.addCustomWidget(widget);

	node.onRemoved = function () {
		// When removing this node we need to remove the input from the DOM
		for (let y in this.widgets) {
			if (this.widgets[y].inputEl) {
				this.widgets[y].inputEl.remove();
			}
		}
	};

	return { minWidth: 400, minHeight: 200, widget };
}


const ext = {
	// Unique name for the extension
	name: "WebuiCheckpointLoader",
	async init(app) {
		// Any initial setup to run as soon as the page loads
	},
	async setup(app) {
		// Any setup to run after the app is created
	},
	async addCustomNodeDefs(defs, app) {
		// Add custom node definitions
		// These definitions will be configured and registered automatically
		// defs is a lookup core nodes, add yours into this
	},
	async getCustomWidgets(app) {
		// Return custom widget types
		// See ComfyWidgets for widget examples

        const webuiModelChangedEvent = {
            onWebuiModelChanged: (func) => {

            },
        };
		return {
            VOID(node, inputName, inputData, app) {
                const things = addHiddenMultilineWidget(node, inputName, app);
                const widget = things.widget;
                webuiModelChangedEvent.onWebuiModelChanged(() => {
                    if(widget.inputEl.value === '') {
                        widget.inputEl.value = '_';
                    }
                    else {
                        widget.inputEl.value = '';
                    }
                });
                return
            },
		}
	},
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		// Run custom logic before a node definition is registered with the graph
		// This fires for every node definition
	},
	async registerCustomNodes(app) {
		// Register any custom node implementations here allowing for more flexibility than a custom node def
	},
	loadedGraphNode(node, app) {
		// Fires for each node when loading/dragging/etc a workflow json or png
		// If you break something in the backend and want to patch workflows in the frontend
		// This is the place to do this
		// This fires for every node on each load
	},
	nodeCreated(node, app) {
		// Fires every time a node is constructed
		// You can modify widgets/add handlers/etc here
	}
};

app.registerExtension(ext);
