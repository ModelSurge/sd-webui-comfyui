import functools
import torch
import torchvision.transforms.functional as F
from lib_comfyui import ipc, global_state, default_workflow_types, external_code


__original_create_sampler = None


@ipc.restrict_to_process('webui')
def apply_patches():
    from modules import sd_samplers
    global __original_create_sampler

    __original_create_sampler = sd_samplers.create_sampler
    sd_samplers.create_sampler = functools.partial(create_sampler_hijack, original_function=sd_samplers.create_sampler)


@ipc.restrict_to_process('webui')
def watch_prompts(component, **kwargs):
    possible_elem_ids = {
        f'{tab}{negative}_prompt': bool(negative)
        for tab in ('txt2img', 'img2img')
        for negative in ('', '_neg')
    }
    event_listeners = ('change', 'input', 'blur')

    elem_id = getattr(component, 'elem_id', None)
    if elem_id in possible_elem_ids:
        attribute = f'last_{"negative" if possible_elem_ids[elem_id] else "positive"}_prompt'
        for event_listener in event_listeners:
            getattr(component, event_listener)(
                fn = lambda p: setattr(global_state, attribute, p),
                inputs=[component]
            )


@ipc.restrict_to_process('webui')
def clear_patches():
    from modules import sd_samplers
    global __original_create_sampler

    sd_samplers.create_sampler = __original_create_sampler


@ipc.restrict_to_process('webui')
def create_sampler_hijack(name: str, model, original_function):
    sampler = original_function(name, model)
    sampler.sample_img2img = functools.partial(sample_img2img_hijack, original_function=sampler.sample_img2img)
    return sampler


@ipc.restrict_to_process('webui')
def sample_img2img_hijack(p, x, *args, original_function, **kwargs):
    if getattr(global_state, 'enabled', True):
        preprocessed_x = external_code.run_workflow(
            workflow_type=default_workflow_types.preprocess_latent_workflow_type,
            tab='img2img',
            batch_input=x.to(device='cpu'),
        )
        x = torch.stack(preprocessed_x).to(device=x.device) if isinstance(preprocessed_x, list) else preprocessed_x.to(device=x.device)

    return original_function(p, x, *args, **kwargs)


@ipc.restrict_to_process('webui')
def patch_processing(p):
    from modules import processing

    p.sd_webui_comfyui_patches = getattr(p, 'sd_webui_comfyui_patches', set())
    is_img2img = isinstance(p, processing.StableDiffusionProcessingImg2Img)

    if 'sample' not in p.sd_webui_comfyui_patches:
        p.sample = functools.partial(p_sample_patch, original_function=p.sample, is_img2img=is_img2img)
        p.sd_webui_comfyui_patches.add('sample')

    if is_img2img and 'init' not in p.sd_webui_comfyui_patches:
        p.init = functools.partial(p_img2img_init, original_function=p.init, p_ref=p)
        p.sd_webui_comfyui_patches.add('init')


def p_sample_patch(*args, original_function, is_img2img, **kwargs):
    x = original_function(*args, **kwargs)
    if getattr(global_state, 'enabled', True):
        postprocessed_x = external_code.run_workflow(
            workflow_type=default_workflow_types.postprocess_latent_workflow_type,
            tab='img2img' if is_img2img else 'txt2img',
            batch_input=x.to(device='cpu'),
        )
        x = torch.stack(postprocessed_x).to(device=x.device) if isinstance(postprocessed_x, list) else postprocessed_x.to(device=x.device)

    return x


def p_img2img_init(*args, original_function, p_ref, **kwargs):
    if getattr(global_state, 'enabled', True):
        preprocessed_images = external_code.run_workflow(
            workflow_type=default_workflow_types.preprocess_workflow_type,
            tab='img2img',
            batch_input=[F.pil_to_tensor(image) / 255 for image in p_ref.init_images],
        )
        p_ref.init_images = [F.to_pil_image(image_tensor) for image_tensor in preprocessed_images]

    return original_function(*args, **kwargs)
