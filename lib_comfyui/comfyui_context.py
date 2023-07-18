import sys
import modules.scripts as scripts
base_dir = scripts.basedir()


class ComfyuiContext:
    def __init__(self):
        self.original_sys_path = list(sys.path)
        self.sys_path_to_add = base_dir

    def __enter__(self):
        sys.path.insert(0, self.sys_path_to_add)
        return self

    def __exit__(self, *args):
        sys.path.clear()
        sys.path.extend(self.original_sys_path)
