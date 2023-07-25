import sys
import modules.scripts as scripts
from lib_comfyui import ipc


base_dir = scripts.basedir()


@ipc.confine_to('webui')
def get_webui_base_dir():
    return base_dir


class ComfyuiContext:
    def __init__(self):
        self.sys_path_to_add = base_dir

    def __enter__(self):
        self.original_sys_path = list(sys.path)
        sys.path.insert(0, self.sys_path_to_add)
        return self

    def __exit__(self, *args):
        sys.path.clear()
        sys.path.extend(self.original_sys_path)
