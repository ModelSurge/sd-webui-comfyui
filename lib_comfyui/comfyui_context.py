import sys
import os


class ComfyuiContext:
    def __init__(self):
        self.original_sys_path = list(sys.path)
        self.sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    def __enter__(self):
        sys.path.insert(0, self.sys_path_to_add)
        return self

    def __exit__(self, *args):
        sys.path.clear()
        sys.path.extend(self.original_sys_path)
