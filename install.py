import launch
import os
import pkg_resources
import re
import sys
import traceback


req_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "requirements.txt")
req_re = re.compile('^([^=<>~]*)\s*(?:([=<>~])=\s*([^=<>~]*))?$')


with open(req_file) as file:
    for package in file:
        try:
            package = package.strip()
            match = req_re.search(package)
            package_name = match.group(1)

            try:
                installed_version = pkg_resources.get_distribution(package_name).version
            except Exception:
                installed_version = None
                pass  # package not installed, we still want to install it

            package_already_installed = installed_version is not None
            install_info = f"sd-webui-comfyui requirement: {package}"
            comparison, required_version = match.group(2, 3)

            if package_already_installed:
                install_info = f"sd-webui-comfyui requirement: changing {package_name} version from {installed_version} to {required_version}"
                if (
                    comparison == '~' or
                    required_version is None or
                    eval(f'"{installed_version}" {comparison}= "{required_version}"')
                ):
                    continue

            launch.run_pip(f"install {package}", install_info)
        except Exception as e:
            print(traceback.format_exception_only(e))
            print(f'Failed to install sd-webui-comfyui requirement: {package}', file=sys.stderr)
