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
    FUNCTION = "get_images"

    CATEGORY = "webui"

    @staticmethod
    def get_images(void):
        return global_state.node_inputs,


class WebuiOutput:
    images = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
        }
    RETURN_TYPES = ()
    FUNCTION = "update_global_state"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    @staticmethod
    def update_global_state(**outputs):
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
