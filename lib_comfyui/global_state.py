from types import ModuleType

from lib_comfyui import ipc
import sys


class GlobalState(ModuleType):
    __state = {}

    def __init__(self, glob):
        super().__init__(__name__)
        for k, v in glob.items():
            setattr(self, k, v)

    @ipc.confine_to('webui')
    @staticmethod
    def getattr(item):
        try:
            return GlobalState.__state[item]
        except KeyError:
            raise AttributeError

    @ipc.confine_to('webui')
    @staticmethod
    def setattr(item, value):
        GlobalState.__state[item] = value

    @ipc.confine_to('webui')
    @staticmethod
    def delattr(item):
        del GlobalState.__state[item]

    def __getattr__(self, item):
        return GlobalState.getattr(item)

    def __setattr__(self, item, value):
        GlobalState.setattr(item, value)

    def __delattr__(self, item):
        GlobalState.delattr(item)


sys.modules[__name__] = GlobalState(globals())
