from lib_comfyui.private.external_code import *

# /!\ IMPORTANT /!\
# Do NOT import the `lib_comfyui.private.external_code` module directly.
# To use the external_code module, please import this file, which is located at `lib_comfyui/external_code.py`.
# The actual implementation of the module is located under `lib_comfyui.private` for a good reason.
# This is because if you import the private module directly, you will redefine a copy of the classes defined there.
# This will create unexpected issues with type checking and state inconsistency, among other unpredictable behavior.
# -> Again, instead, please use the current module located at `lib_comfyui/external_code.py`.
# This will make sure to reuse the global python module cache.
