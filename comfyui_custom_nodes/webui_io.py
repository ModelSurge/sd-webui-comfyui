from lib_comfyui import global_state


class AnyType(str):
    def __ne__(self, _) -> bool:
        return False


class AnyReturnTypes(tuple):
    def __init__(self):
        super().__init__()

    def __getitem__(self, _):
        return AnyType()


class FromWebui:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }
    RETURN_TYPES = AnyReturnTypes()
    RETURN_NAMES = ()
    FUNCTION = "get_node_inputs"

    CATEGORY = "webui"

    @staticmethod
    def get_node_inputs(void):
        return global_state.node_input_args


class ToWebui:
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
    "FromWebui": FromWebui,
    "ToWebui": ToWebui,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FromWebui": 'From Webui',
    "ToWebui": 'To Webui',
}
