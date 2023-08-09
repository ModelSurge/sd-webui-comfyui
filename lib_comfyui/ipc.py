import gc
import importlib
import sys
import time
import logging


def run_in_process(process_id):
    def annotation(function):
        def wrapper(*args, **kwargs):
            global current_process_id
            if process_id == current_process_id:
                return function(*args, **kwargs)
            else:
                start = time.time()
                res = current_callback_proxies[process_id].get(args=(function.__module__, function.__qualname__, args, kwargs))
                logging.debug(
                    '[sd-webui-comfyui] IPC call %s -> %s %s:\t%s',
                    current_process_id, process_id,
                    time.time() - start,
                    f'{function.__module__}.{function.__qualname__}(*{args}, **{kwargs})'
                )
                return res

        return wrapper

    return annotation


def restrict_to_process(process_id):
    def annotation(function):
        def wrapper(*args, **kwargs):
            global current_process_id
            if process_id != current_process_id:
                raise RuntimeError(f'Can only call function {function.__module__}.{function.__qualname__} from process {process_id}. Current process is {current_process_id}')

            return function(*args, **kwargs)

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
current_callback_listeners = {}
current_callback_proxies = {}


def start_callback_listeners():
    assert not callback_listeners_started()
    for callback_listener in current_callback_listeners.values():
        callback_listener.start()

    print('[sd-webui-comfyui]', 'Started callback listeners for process', current_process_id)


def stop_callback_listeners():
    assert callback_listeners_started()
    for callback_listener in current_callback_listeners.values():
        callback_listener.stop()

    current_callback_proxies.clear()
    current_callback_listeners.clear()
    gc.collect()

    print('[sd-webui-comfyui]', 'Stopped callback listeners for process', current_process_id)


def callback_listeners_started():
    return any(callback_listener.is_running() for callback_listener in current_callback_listeners.values())
