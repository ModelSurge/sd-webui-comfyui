import unittest
from tests.utils import setup_test_env
setup_test_env()
import sys
from lib_comfyui import external_code


class ImportlibTest(unittest.TestCase):
    def test_importlib_uses_modules_cache(self):
        WorkflowType = external_code.WorkflowType
        del sys.modules['lib_comfyui.external_code']
        comfyui_api = importlib.import_module('lib_comfyui.external_code', 'external_code')

        self.assertIs(WorkflowType, comfyui_api.WorkflowType)


if __name__ == '__main__':
    unittest.main()
