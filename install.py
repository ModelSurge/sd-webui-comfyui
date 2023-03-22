import os
import subprocess
import shutil


extension_root = os.path.dirname(os.path.realpath(__file__))


def install_localtunnel():
    subprocess.run('npm install', cwd=extension_root, shell=True)


npm_executable = shutil.which('npm')
if npm_executable is None:
    print('[ComfyUI] cannot find npm. Sharing through localtunnel disabled.')
else:
    install_localtunnel()
