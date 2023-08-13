import functools
import sys

import torch
import torchvision.transforms.functional as F
from lib_comfyui import ipc, global_state, default_workflow_types, external_code
from lib_comfyui.comfyui import webui_io


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
    event_listeners = ('change', 'blur')

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
    processed_x = external_code.run_workflow(
        workflow_type=default_workflow_types.preprocess_latent_workflow_type,
        tab='img2img',
        batch_input=webui_io.webui_latent_to_comfyui(x).to(device='cpu'),
    )
    verify_singleton(processed_x)
    return original_function(p, webui_io.comfyui_latent_to_webui(processed_x[0]).to(device=x.device), *args, **kwargs)


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
    processed_x = external_code.run_workflow(
        workflow_type=default_workflow_types.postprocess_latent_workflow_type,
        tab='img2img' if is_img2img else 'txt2img',
        batch_input=webui_io.webui_latent_to_comfyui(x.to(device='cpu')),
    )
    verify_singleton(processed_x)
    return webui_io.comfyui_latent_to_webui(processed_x[0]).to(device=x.device)


def p_img2img_init(*args, original_function, p_ref, **kwargs):
    processed_images = external_code.run_workflow(
        workflow_type=default_workflow_types.preprocess_workflow_type,
        tab='img2img',
        batch_input=torch.stack([webui_io.webui_image_to_comfyui(image) for image in p_ref.init_images]),
    )
    verify_singleton(processed_images)
    p_ref.init_images = webui_io.comfyui_image_to_webui(processed_images[0])
    return original_function(*args, **kwargs)


def verify_singleton(l: list):
    if len(l) != 1:
        prefix = '\n[sd-webui-comfyui] '
        print(f'{prefix}The last ComfyUI workflow returned {len(l)} batches instead of 1.'
              f'{prefix}This is likely due to the workflow not having exactly 1 "To Webui" node.'
              f'{prefix}Please verify that the workflow is valid.', file=sys.stderr)
