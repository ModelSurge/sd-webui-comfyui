from lib_comfyui import global_state


class StaticProperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, *args):
        return self.f()


class FromWebui:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "void": ("VOID", ),
            },
        }

    @StaticProperty
    def RETURN_TYPES():
        return global_state.current_workflow_input_types

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
        global_state.batch_output_args += [outputs]
        return ()


NODE_CLASS_MAPPINGS = {
    "FromWebui": FromWebui,
    "ToWebui": ToWebui,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FromWebui": 'From Webui',
    "ToWebui": 'To Webui',
}
