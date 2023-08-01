import importlib
import sys
from lib_comfyui import parallel_utils, platform_utils


def confine_to(process_id):
    def annotation(function):
        def wrapper(*args, **kwargs):
            global current_process_id
            if process_id == current_process_id:
                return function(*args, **kwargs)
            else:
                return current_process_queues[process_id].get(args=(function.__module__, function.__qualname__, args, kwargs))

        return wrapper

    return annotation


def call_fully_qualified(module_name, qualified_name, args, kwargs):
    module_parts = module_name.split('.')
    try:
        module = sys.modules[module_parts[0]]
        for part in module_parts[1:]:
            module = getattr(module, part)
    except (AttributeError, KeyError):
        source_module = module_parts[-1]
        module = importlib.import_module(module_name, source_module)

    function = module
    for name in qualified_name.split('.'):
        function = getattr(function, name)
    return function(*args, **kwargs)


current_process_id = 'webui'
current_process_callback_listeners = {
    'webui': parallel_utils.CallbackWatcher(parallel_utils.CallbackQueue(call_fully_qualified)),
}


def get_current_process_queues():
    return {k: v.queue for k, v in current_process_callback_listeners.items()}


current_process_queues = {
    'comfyui': parallel_utils.CallbackQueue(call_fully_qualified)
}


def start_callback_listeners():
    for callback_listener in current_process_callback_listeners.values():
        callback_listener.start()


def stop_callback_listeners():
    for callback_listener in current_process_callback_listeners.values():
        callback_listener.stop()
