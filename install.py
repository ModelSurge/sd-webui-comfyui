import os
import subprocess
import shutil


extension_root = os.path.dirname(os.path.realpath(__file__))
package_json = os.path.join(extension_root, 'package.json')


def install_localtunnel():
    if not os.path.exists(package_json):
        subprocess.run('npm install localtunnel', cwd=extension_root, shell=True)


npm_executable = shutil.which('npm')
if npm_executable is None:
    print('[ComfyUI] cannot find npm. Sharing through localtunnel disabled.')
else:
    install_localtunnel()
