import re
import launch
import os
import pkg_resources
import traceback


req_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")
req_re = re.compile('^([^=<>~]*)(?:([=<>~])=([^=<>~]*))?$')


with open(req_file) as file:
    for package in file:
        try:
            package = package.strip()
            match = req_re.search(package)
            if (version := match.group(3)) is not None:
                package_name, comparison, package_version = match.group(1, 2, 3)
                try:
                    installed_version = pkg_resources.get_distribution(package_name).version
                except Exception:
                    # package not installed, we still want to install it
                    pass
                else:
                    if comparison != '~' and eval(f'"{installed_version}" {comparison}= "{package_version}"'):
                        continue

                    launch.run_pip(f"install {package}", f"sd-webui-comfyui requirement: changing {package_name} version from {installed_version} to {package_version}")

            launch.run_pip(f"install {package}", f"sd-webui-comfyui requirement: {package}")
        except Exception as e:
            print(traceback.format_exception_only(e))
            print(f'Warning: Failed to install {package}.')
