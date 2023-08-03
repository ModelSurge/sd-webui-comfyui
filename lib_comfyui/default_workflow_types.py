from pathlib import Path
from lib_comfyui import comfyui_context, external_code


default_workflows_dir = Path(comfyui_context.get_webui_base_dir(), 'workflows', 'default')
sandbox_tab_workflow_type = external_code.WorkflowType(
    base_id='sandbox',
    display_name='ComfyUI',
    tabs='tab',
)
preprocess_workflow_type = external_code.WorkflowType(
    base_id='preprocess',
    display_name='Preprocess',
    tabs='img2img',
    default_workflow=default_workflows_dir / 'process_image.json',
)
preprocess_latent_workflow_type = external_code.WorkflowType(
    base_id='preprocess_latent',
    display_name='Preprocess (latent)',
    tabs='img2img',
    default_workflow=default_workflows_dir / 'process_latent.json',
)
postprocess_workflow_type = external_code.WorkflowType(
    base_id='postprocess',
    display_name='Postprocess',
    default_workflow=default_workflows_dir / 'process_image.json',
)
postprocess_latent_workflow_type = external_code.WorkflowType(
    base_id='postprocess_latent',
    display_name='Postprocess (latent)',
    default_workflow=default_workflows_dir / 'process_latent.json',
)


def add_default_workflow_types():
    workflow_types = [
        sandbox_tab_workflow_type,
        preprocess_workflow_type,
        preprocess_latent_workflow_type,
        postprocess_workflow_type,
        postprocess_latent_workflow_type,
    ]

    for workflow_type in workflow_types:
        external_code.add_workflow_type(workflow_type)
