from pathlib import Path
from lib_comfyui import comfyui_context, external_code


default_workflows_dir = Path(comfyui_context.get_webui_base_dir(), 'workflows', 'default')
sandbox_tab_workflow = external_code.Workflow(
    base_id='sandbox',
    display_name='ComfyUI',
    tabs='tab',
)
preprocess_latent_workflow = external_code.Workflow(
    base_id='preprocess_latent',
    display_name='Preprocess (latent)',
    tabs='img2img',
    default_workflow=default_workflows_dir / 'preprocess_latent.json',
)
postprocess_workflow = external_code.Workflow(
    base_id='postprocess',
    display_name='Postprocess',
    default_workflow=default_workflows_dir / 'postprocess.json',
)


def add_default_workflows():
    workflows = [
        sandbox_tab_workflow,
        postprocess_workflow,
        preprocess_latent_workflow,
    ]

    for workflow in workflows:
        external_code.add_workflow(workflow)
