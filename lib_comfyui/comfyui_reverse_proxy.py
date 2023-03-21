import os
import sys
import shutil
import subprocess
import threading
import time
import socket
import importlib
from lib_comfyui import argv_conversion, webui_settings
importlib.reload(argv_conversion)
importlib.reload(webui_settings)


extension_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
process = None


def start():
    comfyui_argv = list(sys.argv)
    argv_conversion.set_comfyui_argv(comfyui_argv)
    port = comfyui_argv[comfyui_argv.index('--port') + 1]

    npx_executable = shutil.which('npx')
    if npx_executable is None:
        return

    threading.Thread(target=on_create_local_tunnel, args=(port, npx_executable, ), daemon=True).start()


def on_create_local_tunnel(port, npx_executable):
    global process
    if process is not None:
        return

    wait_for_comfyui_started(int(port))

    print("Launching localtunnel...")
    process = subprocess.Popen(
        [npx_executable, 'lt', "--port", port, "--local-host", '127.0.0.1'],
        cwd=extension_root,
        stdout=subprocess.PIPE)
    for line in process.stdout:
        line = line.decode()
        if line.startswith('your url is:'):
            webui_settings.set_comfyui_url(line.split('your url is:')[1].strip())
        print(line, end='')


# src: https://github.com/comfyanonymous/ComfyUI/blob/master/notebooks/comfyui_colab.ipynb
def wait_for_comfyui_started(port):
    while True:
        time.sleep(0.5)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            break
        sock.close()


def stop():
    global process
    if process is None:
        return

    process.terminate()
    process = None
