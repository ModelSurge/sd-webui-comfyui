import os
import sys

def setup_test_env():
    extension_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if extension_root not in sys.path:
        sys.path.append(extension_root)
