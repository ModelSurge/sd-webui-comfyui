import unittest
import importlib
importlib.import_module('extensions.sd-webui-comfyui.tests.utils', 'utils').setup_test_env()


class TestExternalCodeWorking(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_true(self):
        self.assertTrue(True)
