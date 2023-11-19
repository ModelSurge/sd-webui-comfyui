from lib_comfyui import external_code


sandbox_tab_workflow_type = external_code.WorkflowType(
    base_id='sandbox',
    display_name='ComfyUI',
    tabs='tab',
)
preprocess_workflow_type = external_code.WorkflowType(
    base_id='preprocess',
    display_name='Preprocess',
    tabs='img2img',
    default_workflow=external_code.AUTO_WORKFLOW,
    types='IMAGE',
)
preprocess_latent_workflow_type = external_code.WorkflowType(
    base_id='preprocess_latent',
    display_name='Preprocess (latent)',
    tabs='img2img',
    default_workflow=external_code.AUTO_WORKFLOW,
    types='LATENT',
)
postprocess_latent_workflow_type = external_code.WorkflowType(
    base_id='postprocess_latent',
    display_name='Postprocess (latent)',
    default_workflow=external_code.AUTO_WORKFLOW,
    types='LATENT',
)
postprocess_workflow_type = external_code.WorkflowType(
    base_id='postprocess',
    display_name='Postprocess',
    default_workflow=external_code.AUTO_WORKFLOW,
    types='IMAGE',
)
postprocess_image_workflow_type = external_code.WorkflowType(
    base_id='postprocess_image',
    display_name='Postprocess image',
    default_workflow=external_code.AUTO_WORKFLOW,
    types='IMAGE',
    max_amount_of_ToWebui_nodes=1,
)
before_save_image_workflow_type = external_code.WorkflowType(
    base_id='before_save_image',
    display_name='Before save image',
    default_workflow=external_code.AUTO_WORKFLOW,
    types='IMAGE',
    max_amount_of_ToWebui_nodes=1,
)


def add_default_workflow_types():
    workflow_types = [
        sandbox_tab_workflow_type,
        preprocess_workflow_type,
        preprocess_latent_workflow_type,
        postprocess_latent_workflow_type,
        postprocess_workflow_type,
        postprocess_image_workflow_type,
        before_save_image_workflow_type,
    ]

    for workflow_type in workflow_types:
        external_code.add_workflow_type(workflow_type)
