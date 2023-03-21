import sys
import os
import importlib
from modules import shared
from torch import multiprocessing
from modules import script_callbacks
from lib_comfyui import async_comfyui_loader, webui_settings, argv_conversion
importlib.reload(webui_settings)
importlib.reload(async_comfyui_loader)


process = None


def start():
    install_location = webui_settings.get_install_location()
    if not os.path.exists(install_location):
        return

    should_share = '--share' in sys.argv or '--ngrok' in sys.argv
    if should_share:
        start_comfyui_localtunnel()

    model_queue = multiprocessing.Queue()
    start_comfyui_process(model_queue, install_location)

    def on_model_loaded(model):
        model_queue.put(model.sd_model_checkpoint)

    script_callbacks.on_model_loaded(on_model_loaded)
    if shared.sd_model is not None:
        on_model_loaded(shared.sd_model)


def start_comfyui_process(model_queue, install_location):
    global process
    original_sys_path = list(sys.path)
    sys_path_to_add = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    try:
        sys.path.insert(0, sys_path_to_add)
        process = multiprocessing.Process(target=async_comfyui_loader.main, args=(model_queue, install_location), daemon=True)
        process.start()
    finally:
        sys.path.clear()
        sys.path.extend(original_sys_path)


def start_comfyui_localtunnel():
    comfyui_argv = list(sys.argv)
    argv_conversion.set_comfyui_argv(comfyui_argv)
    port = comfyui_argv[comfyui_argv.index('--port') + 1]

    import shutil
    local_tunnel = shutil.which('lt')
    if local_tunnel is None:
        return

    import subprocess
    import threading
    import time
    import socket

    def on_create_local_tunnel(int_port):
        while True:
            time.sleep(0.5)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', int_port))
            if result == 0:
                break
            sock.close()

        print("Launching localtunnel...")
        p = subprocess.Popen([local_tunnel, "--port", port, "--local-host", '127.0.0.1'], stdout=subprocess.PIPE)
        for line in p.stdout:
            line = line.decode()
            if line.startswith('your url is:'):
                webui_settings.set_comfyui_url(line.split('your url is:')[1].strip())
            print(line, end='')

    threading.Thread(target=on_create_local_tunnel, args=(int(port),), daemon=True).start()


def stop():
    global process
    if process is None:
        return

    process.terminate()
    process = None
