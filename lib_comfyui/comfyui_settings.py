from modules import shared


def add_settings():
    section = ('comfy_ui', "ComfyUI")
    shared.opts.add_option("comfyui_install_location", shared.OptionInfo(
        '', "ComfyUI install location", section=section))
