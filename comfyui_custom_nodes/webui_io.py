from lib_comfyui import global_state


class WebuiInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "get_node_inputs"

    CATEGORY = "webui"

    @staticmethod
    def get_node_inputs(void):
        return global_state.node_input_args


class WebuiOutput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
        }
    RETURN_TYPES = ()
    FUNCTION = "extend_node_outputs"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    @staticmethod
    def extend_node_outputs(**outputs):
        global_state.node_outputs += [outputs]
        return ()


NODE_CLASS_MAPPINGS = {
    "FromWebui": WebuiInput,
    "ToWebui": WebuiOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FromWebui": 'From Webui',
    "ToWebui": 'To Webui',
}
