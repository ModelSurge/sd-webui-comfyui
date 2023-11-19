import unittest
from unittest.mock import patch
from tests.utils import setup_test_env
setup_test_env()

from lib_comfyui import external_code, global_state


class TestRunWorkflowBasicFunctionality(unittest.TestCase):
    def setUp(self) -> None:
        setattr(global_state, 'enabled_workflow_type_ids', {
            'test_tab': True,
        })

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_valid_workflow_with_dict_types(self, mock_start_workflow, _):
        mock_start_workflow.return_value = [{"key1": 0, "key2": 1}]
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types={"key1": 'IMAGE', "key2": 'LATENT'},
        )
        batch_input = {"key1": "value", "key2": 123}

        result = external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_called_once_with(
            batch_input_args=("value", 123),
            workflow_type_id="test_tab",
            workflow_input_types=('IMAGE', 'LATENT'),
            queue_front=True,
        )
        self.assertEqual(result, mock_start_workflow.return_value)

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_valid_workflow_with_tuple_types(self, mock_start_workflow, _):
        mock_start_workflow.return_value = [{"key1": 0, "key2": 1}]
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types=("IMAGE", "LATENT"),
        )
        batch_input = ("value", 123)

        result = external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_called_once_with(
            batch_input_args=("value", 123),
            workflow_type_id="test_tab",
            workflow_input_types=('IMAGE', 'LATENT'),
            queue_front=True,
        )
        self.assertEqual(result, [tuple(batch.values()) for batch in mock_start_workflow.return_value])

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch('lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync')
    def test_valid_workflow_with_str_types(self, mock_start_workflow, _):
        mock_start_workflow.return_value = [{"key1": 0}]
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types="IMAGE",
        )
        batch_input = "value"

        result = external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_called_once_with(
            batch_input_args=("value",),
            workflow_type_id="test_tab",
            workflow_input_types=('IMAGE',),
            queue_front=True,
        )
        self.assertEqual(result, [next(iter(batch.values())) for batch in mock_start_workflow.return_value])

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch('lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync')
    def test_workflow_type_not_on_tab(self, mock_start_workflow, _):
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types="IMAGE",
        )
        batch_input = "value"

        with self.assertRaises(ValueError):
            external_code.run_workflow(workflow_type, "not_tab", batch_input)

        mock_start_workflow.assert_not_called()

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_workflow_type_not_enabled(self, mock_start_workflow, _):
        setattr(global_state, 'enabled_workflow_type_ids', {})

        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types="IMAGE",
        )
        batch_input = "value"

        with self.assertRaises(RuntimeError):
            external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_not_called()

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_multiple_outputs(self, mock_start_workflow, _):
        mock_start_workflow.return_value = [{"key1": 0, "key2": 1}, {"key1": 2, "key2": 3}]

        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types={"key1": 'IMAGE', "key2": 'LATENT'},
        )
        batch_input = {"key1": "value", "key2": 123}

        result = external_code.run_workflow(workflow_type, "tab", batch_input)

        self.assertEqual(result, mock_start_workflow.return_value)


class TestRunWorkflowInputValidation(unittest.TestCase):
    def setUp(self) -> None:
        setattr(global_state, 'enabled_workflow_type_ids', {
            'test_tab': True,
        })

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_batch_input_mismatch_dict(self, mock_start_workflow, _):
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types={"key1": 'IMAGE', "key2": 'LATENT'},
        )
        batch_input = {"key1": "value"}

        with self.assertRaises(TypeError):
            external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_not_called()

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_batch_input_mismatch_tuple(self, mock_start_workflow, _):
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types=(str, int)
        )
        batch_input = ("value",)

        with self.assertRaises(TypeError):
            external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_not_called()

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_identity_on_error(self, mock_start_workflow, _):
        mock_start_workflow.side_effect = RuntimeError("Failed to execute workflow")
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types="IMAGE"
        )
        batch_input = "value"

        # Testing identity_on_error=True
        result = external_code.run_workflow(workflow_type, "tab", batch_input, identity_on_error=True)
        self.assertEqual(result, [batch_input])

        # Testing identity_on_error=False (the default value)
        with self.assertRaises(RuntimeError):
            external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_called_with(
            batch_input_args=("value",),
            workflow_type_id="test_tab",
            workflow_input_types=('IMAGE',),
            queue_front=True,
        )

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_multiple_candidate_ids(self, mock_start_workflow, _):
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types="IMAGE"
        )
        batch_input = "value"

        with patch.object(workflow_type, "get_ids", return_value=["id1", "id2"]):
            with self.assertRaises(AssertionError):
                external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_not_called()

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_invalid_batch_input_type(self, mock_start_workflow, _):
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types={"key1": 'IMAGE', "key2": 'LATENT'},
        )
        batch_input = ["Looking for a missing semi-colon? Here, you take this one with you --> ;", 123]

        with self.assertRaises(TypeError):
            external_code.run_workflow(workflow_type, "tab", batch_input)

        mock_start_workflow.assert_not_called()


class TestRunWorkflowExecutionBehavior(unittest.TestCase):
    def setUp(self) -> None:
        setattr(global_state, 'enabled_workflow_type_ids', {
            'test_tab': True,
        })

    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.validate_amount_of_nodes_or_throw")
    @patch("lib_comfyui.comfyui.iframe_requests.ComfyuiIFrameRequests.start_workflow_sync")
    def test_large_batch_input(self, mock_start_workflow, _):
        workflow_type = external_code.WorkflowType(
            base_id="test",
            display_name="Test Tab",
            tabs="tab",
            types=("IMAGE",) * 1000
        )
        batch_input = ("value",) * 1000
        external_code.run_workflow(workflow_type, "tab", batch_input)
        mock_start_workflow.assert_called_once()


if __name__ == '__main__':
    unittest.main()
