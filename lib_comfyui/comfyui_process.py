import atexit
import inspect
import os
import signal
import subprocess
import sys
from lib_comfyui import ipc, torch_utils, argv_conversion, ipc_callback
from lib_comfyui.webui import settings
from lib_comfyui.comfyui import pre_main


comfyui_process = None


@ipc.restrict_to_process('webui')
def start():
    from modules import shared

    if not getattr(shared.opts, 'comfyui_enabled', True):
        return

    install_location = settings.get_install_location()
    if not os.path.exists(install_location):
        print('[sd-webui-comfyui]', f'could not find ComfyUI under directory "{install_location}". The server will NOT be started.', file=sys.stderr)
        return

    ipc.current_callback_listeners = {'webui': ipc_callback.CallbackWatcher(ipc.call_fully_qualified, 'webui')}
    ipc.current_callback_proxies = {'comfyui': ipc_callback.CallbackProxy('comfyui')}
    ipc.start_callback_listeners()
    atexit.register(stop)
    start_comfyui_process(install_location)


@ipc.restrict_to_process('webui')
def start_comfyui_process(comfyui_install_location):
    global comfyui_process

    comfyui_env = os.environ.copy()
    python_path = [p for p in comfyui_env.get('PYTHONPATH', '').split(os.pathsep) if p]
    python_path[1:1] = (comfyui_install_location, settings.get_extension_base_dir())
    comfyui_env['PYTHONPATH'] = os.pathsep.join(python_path)

    args = [sys.executable, inspect.getfile(pre_main)] + argv_conversion.get_comfyui_args()

    comfyui_process = subprocess.Popen(
        args=args,
        executable=sys.executable,
        cwd=comfyui_install_location,
        env=comfyui_env,
    )


@ipc.restrict_to_process('webui')
def stop():
    atexit.unregister(stop)
    stop_comfyui_process()
    ipc.stop_callback_listeners()


@ipc.restrict_to_process('webui')
def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    print('[sd-webui-comfyui]', 'Attempting to gracefully terminate the ComfyUI server...')
    comfyui_process.terminate()
    try:
        comfyui_process.wait(5)
        print('[sd-webui-comfyui]', 'Comfyui server was gracefully terminated')
    except subprocess.TimeoutExpired:
        print('[sd-webui-comfyui]', 'Graceful termination timed out. Killing the ComfyUI server...')
        comfyui_process.kill()
        print('[sd-webui-comfyui]', 'Comfyui server was killed')
    comfyui_process = None


# remove this when comfyui starts using subprocess with an isolated venv
@ipc.restrict_to_process('webui')
def restore_webui_sigint_handler():
    return
    def sigint_handler(sig, frame):
        exit()

    print('[sd-webui-comfyui]', 'restoring graceful SIGINT handler for the webui process')
    signal.signal(signal.SIGINT, sigint_handler)
