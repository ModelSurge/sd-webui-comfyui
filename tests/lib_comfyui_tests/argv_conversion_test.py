import unittest
from lib_comfyui import argv_conversion


class DeduplicateArgvTest(unittest.TestCase):
    def setUp(self):
        self.argv = []
        self.expected_argv = []

    def tearDown(self):
        self.argv = []
        self.expected_argv = []

    def assert_deduplicated_equal_expected(self):
        argv_conversion.deduplicate_comfyui_args(self.argv)
        self.assertEqual(self.argv, self.expected_argv)

    def test_port_deduplicated(self):
        self.argv.extend(['--port', '1234', '--port', '5678'])
        self.expected_argv.extend(['--port', '1234'])
        self.assert_deduplicated_equal_expected()

    def test_port_mixed_deduplicated(self):
        self.argv.extend(['--port', '1234', '--port', '5678', '--comfyui-use-split-cross-attention', '--lowvram', '--port', '8765'])
        self.expected_argv.extend(['--port', '1234', '--comfyui-use-split-cross-attention', '--lowvram'])
        self.assert_deduplicated_equal_expected()

    def test_lowvram_deduplicated(self):
        self.argv.extend(['--lowvram', '--lowvram'])
        self.expected_argv.extend(['--lowvram'])
        self.assert_deduplicated_equal_expected()

    def test_lowvram_mixed_deduplicated(self):
        self.argv.extend(['--lowvram', '--port', '1234', '--lowvram', '--comfyui-use-split-cross-attention', '--lowvram'])
        self.expected_argv.extend(['--lowvram', '--port', '1234', '--comfyui-use-split-cross-attention'])
        self.assert_deduplicated_equal_expected()
