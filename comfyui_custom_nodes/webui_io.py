from lib_comfyui import global_state
from lib_comfyui.comfyui.webui_io import NODE_DISPLAY_NAME_MAPPINGS


class AnyStr(str):
    def __ne__(self, _value: object) -> bool:
        return False

    def __eq__(self, _value: object) -> bool:
        return True


any_type = AnyStr("*")


class WebuiInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = (any_type, )
    FUNCTION = "get_images"

    CATEGORY = "webui"

    def get_images(self, void):
        return global_state.node_inputs,


class WebuiOutput:
    images = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": (any_type, ),
            },
        }
    RETURN_TYPES = ()
    FUNCTION = "set_images"

    CATEGORY = "webui"

    OUTPUT_NODE = True

    def set_images(self, images):
        global_state.node_outputs += [images]
        return ()


NODE_CLASS_MAPPINGS = {
    "FromWebui": WebuiInput,
    "ToWebui": WebuiOutput,
}
