import atexit
import inspect
import os
import signal
import subprocess
import sys
from lib_comfyui import ipc, torch_utils, argv_conversion, parallel_utils
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
        return

    ipc.current_callback_listeners = {'webui': parallel_utils.CallbackWatcher(ipc.call_fully_qualified, 'webui')}
    ipc.current_callback_proxies = {'comfyui': parallel_utils.CallbackProxy('comfyui')}
    ipc.start_callback_listeners()
    atexit.register(stop)
    start_comfyui_process(install_location)


@ipc.restrict_to_process('webui')
def start_comfyui_process(install_location):
    global comfyui_process

    comfyui_env = os.environ.copy()
    comfyui_env['SD_WEBUI_COMFYUI_MAIN'] = install_location
    python_path = comfyui_env.get('PYTHONPATH', '').split(os.pathsep)
    python_path.insert(1, os.path.dirname(os.path.dirname(__file__)))
    python_path.insert(1, install_location)
    comfyui_env['PYTHONPATH'] = os.pathsep.join(python_path)

    args = [sys.executable, inspect.getfile(pre_main)] + argv_conversion.get_comfyui_args()

    comfyui_process = subprocess.Popen(
        args=args,
        executable=sys.executable,
        env=comfyui_env,
    )


def stop():
    atexit.unregister(stop)
    stop_comfyui_process()
    ipc.stop_callback_listeners()


@ipc.restrict_to_process('webui')
def stop_comfyui_process():
    global comfyui_process
    if comfyui_process is None:
        return

    send_sigint_to_comfyui()
    comfyui_process.wait()
    comfyui_process = None


@ipc.run_in_process('comfyui')
def send_sigint_to_comfyui():
    import _thread
    _thread.interrupt_main()


# remove this when comfyui starts using subprocess with an isolated venv
def restore_webui_sigint_handler():
    def sigint_handler(sig, frame):
        exit()

    print('[sd-webui-comfyui]', 'restoring graceful SIGINT handler for the webui process')
    signal.signal(signal.SIGINT, sigint_handler)
