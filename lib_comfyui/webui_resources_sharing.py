from modules import sd_models, paths

def share_webui_folder_paths():
    from folder_paths import add_model_folder_path
    add_model_folder_path('checkpoints', sd_models.model_path)
    add_model_folder_path('loras', str(Path(paths.models_path) / 'Lora'))
