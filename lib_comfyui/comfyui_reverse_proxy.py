import multiprocessing
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


process = None


def start():
    global process

    comfyui_argv = list(sys.argv)
    argv_conversion.set_comfyui_argv(comfyui_argv)
    port = comfyui_argv[comfyui_argv.index('--port') + 1]

    local_tunnel = shutil.which('lt')
    if local_tunnel is None:
        return

    def on_create_local_tunnel(int_port):
        global process
        if process is not None:
            return

        while True:
            time.sleep(0.5)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', int_port))
            if result == 0:
                break
            sock.close()

        print("Launching localtunnel...")
        process = subprocess.Popen([local_tunnel, "--port", port, "--local-host", '127.0.0.1'], stdout=subprocess.PIPE)
        for line in process.stdout:
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
