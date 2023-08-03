import sys
from lib_comfyui import ipc


__base_dir = None
if ipc.current_process_id == 'webui':
    from modules import scripts
    __base_dir = scripts.basedir()


@ipc.run_in_process('webui')
def get_webui_base_dir():
    return __base_dir


class ComfyuiContext:
    def __init__(self):
        self.sys_path_to_add = get_webui_base_dir()

    def __enter__(self):
        self.original_sys_path = list(sys.path)
        sys.path.insert(0, self.sys_path_to_add)
        return self

    def __exit__(self, *args):
        sys.path.clear()
        sys.path.extend(self.original_sys_path)
