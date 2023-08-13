from pathlib import Path
from lib_comfyui import external_code
from lib_comfyui.webui import settings


default_workflow = Path(settings.get_extension_base_dir(), 'workflows', 'default.json')
sandbox_tab_workflow_type = external_code.WorkflowType(
    base_id='sandbox',
    display_name='ComfyUI',
    tabs='tab',
)
preprocess_workflow_type = external_code.WorkflowType(
    base_id='preprocess',
    display_name='Preprocess',
    tabs='img2img',
    default_workflow=default_workflow,
    input_types='IMAGE',
    output_types='IMAGE',
)
preprocess_latent_workflow_type = external_code.WorkflowType(
    base_id='preprocess_latent',
    display_name='Preprocess (latent)',
    tabs='img2img',
    default_workflow=default_workflow,
    input_types='LATENT',
    output_types='LATENT',
)
postprocess_workflow_type = external_code.WorkflowType(
    base_id='postprocess',
    display_name='Postprocess',
    default_workflow=default_workflow,
    input_types='IMAGE',
    output_types='IMAGE',
)
postprocess_latent_workflow_type = external_code.WorkflowType(
    base_id='postprocess_latent',
    display_name='Postprocess (latent)',
    default_workflow=default_workflow,
    input_types='LATENT',
    output_types='LATENT',
)


def add_default_workflow_types():
    workflow_types = [
        sandbox_tab_workflow_type,
        postprocess_workflow_type,
        postprocess_latent_workflow_type,
        preprocess_workflow_type,
        preprocess_latent_workflow_type,
    ]

    for workflow_type in workflow_types:
        external_code.add_workflow_type(workflow_type)
