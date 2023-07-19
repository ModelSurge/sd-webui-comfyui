import importlib
import sys
from lib_comfyui import parallel_utils


def confine_to(process_id):
    def annotation(function):
        def wrapper(*args, **kwargs):
            global current_process_id
            if process_id == current_process_id:
                return function(*args, **kwargs)
            else:
                return process_queues[process_id].get(args=(function.__module__, function.__qualname__, args, kwargs))

        return wrapper

    return annotation


def call_fully_qualified(module_name, qualified_name, args, kwargs):
    module_parts = module_name.split('.')
    try:
        module = sys.modules[module_parts[0]]
        for part in module_parts[1:]:
            module = getattr(module_parts, part)
    except AttributeError:
        source_module = module_parts[-1]
        module = importlib.import_module(module_name, source_module)

    function = module
    for name in qualified_name.split('.'):
        function = getattr(function, name)
    return function(*args, **kwargs)


current_process_id = 'webui'
process_callback_listeners = {
    'webui': parallel_utils.ProducerHandler(parallel_utils.SynchronizingQueue(call_fully_qualified)),
}
process_queues = {}


def get_process_queues():
    return {k: v.queue for k, v in process_callback_listeners.items()}


def start_process_queues():
    for callback_listener in process_callback_listeners.values():
        callback_listener.start()


def stop_process_queues():
    for callback_listener in process_callback_listeners.values():
        callback_listener.stop()
