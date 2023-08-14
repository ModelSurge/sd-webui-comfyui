def fix_path():
    import sys
    from pathlib import Path

    extension_path = str(Path(__file__).parent.parent.parent)
    if extension_path not in sys.path:
        sys.path.append(extension_path)


fix_path()
from .api import *
