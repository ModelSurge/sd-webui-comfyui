import functools
import re
import sys

from lib_comfyui import ipc, global_state, default_workflow_types, external_code
from lib_comfyui.comfyui import type_conversion


__original_create_sampler = None
__original_re_param_code = None


@ipc.restrict_to_process('webui')
def apply_patches():
    from modules import sd_samplers, generation_parameters_copypaste
    global __original_create_sampler, __original_re_param_code

    __original_create_sampler = sd_samplers.create_sampler
    sd_samplers.create_sampler = functools.partial(create_sampler_hijack, original_function=sd_samplers.create_sampler)

    __original_re_param_code = generation_parameters_copypaste.re_param_code
    generation_parameters_copypaste.re_param_code = r'\s*([\w ]+):\s*("(?:\\.|[^\\"])+"|[^,]*)(?:,|$)'
    generation_parameters_copypaste.re_param = re.compile(generation_parameters_copypaste.re_param_code)


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
                fn=lambda p: setattr(global_state, attribute, p),
                inputs=[component]
            )


@ipc.restrict_to_process('webui')
def clear_patches():
    from modules import sd_samplers, generation_parameters_copypaste
    global __original_create_sampler, __original_re_param_code

    if __original_create_sampler is not None:
        sd_samplers.create_sampler = __original_create_sampler

    if __original_re_param_code is not None:
        generation_parameters_copypaste.re_param_code = __original_re_param_code
        generation_parameters_copypaste.re_param = re.compile(generation_parameters_copypaste.re_param_code)


@ipc.restrict_to_process('webui')
def create_sampler_hijack(name: str, model, original_function):
    sampler = original_function(name, model)
    sampler.sample_img2img = functools.partial(sample_img2img_hijack, original_function=sampler.sample_img2img)
    return sampler


@ipc.restrict_to_process('webui')
def sample_img2img_hijack(p, x, *args, original_function, **kwargs):
    from modules import processing
    workflow_type = default_workflow_types.preprocess_latent_workflow_type

    if not (
        isinstance(p, processing.StableDiffusionProcessingImg2Img) and
        external_code.is_workflow_type_enabled(workflow_type.get_ids("img2img")[0])
    ):
        return original_function(p, x, *args, **kwargs)

    print('preprocess_latent')
    processed_x = external_code.run_workflow(
        workflow_type=default_workflow_types.preprocess_latent_workflow_type,
        tab='img2img',
        batch_input=type_conversion.webui_latent_to_comfyui(x.to(device='cpu')),
        identity_on_error=True,
    )
    verify_singleton(processed_x)
    x = type_conversion.comfyui_latent_to_webui(processed_x[0]).to(device=x.device)
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
    tab = 'img2img' if is_img2img else 'txt2img'

    if not external_code.is_workflow_type_enabled(default_workflow_types.postprocess_latent_workflow_type.get_ids(tab)[0]):
        return x

    print('postprocess_latent')
    processed_x = external_code.run_workflow(
        workflow_type=default_workflow_types.postprocess_latent_workflow_type,
        tab=tab,
        batch_input=type_conversion.webui_latent_to_comfyui(x.to(device='cpu')),
        identity_on_error=True,
    )
    verify_singleton(processed_x)
    return type_conversion.comfyui_latent_to_webui(processed_x[0]).to(device=x.device)


def p_img2img_init(*args, original_function, p_ref, **kwargs):
    if not external_code.is_workflow_type_enabled(default_workflow_types.preprocess_workflow_type.get_ids("img2img")[0]):
        return original_function(*args, **kwargs)

    print('preprocess')
    processed_images = external_code.run_workflow(
        workflow_type=default_workflow_types.preprocess_workflow_type,
        tab='img2img',
        batch_input=type_conversion.webui_image_to_comfyui(p_ref.init_images),
        identity_on_error=True,
    )
    verify_singleton(processed_images)
    p_ref.init_images = type_conversion.comfyui_image_to_webui(processed_images[0])
    return original_function(*args, **kwargs)


def verify_singleton(l: list):
    if len(l) != 1:
        prefix = '\n[sd-webui-comfyui] '
        print(f'{prefix}The last ComfyUI workflow returned {len(l)} batches instead of 1.'
              f'{prefix}This is likely due to the workflow not having exactly 1 "To Webui" node.'
              f'{prefix}Please verify that the workflow is valid.', file=sys.stderr)
