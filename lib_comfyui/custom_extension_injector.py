import functools
import os
import inspect
import ast
import textwrap
from lib_comfyui import find_extensions, ipc

# This patching code was highly inspired by Sergei's monkey patch article.
# Source: https://medium.com/@chipiga86/python-monkey-patching-like-a-boss-87d7ddb8098e


def register_webui_extensions():
    node_paths, script_paths = find_extensions.get_extension_paths_to_load()
    register_custom_nodes(node_paths)
    register_custom_scripts(script_paths)


@ipc.restrict_to_process('comfyui')
def register_custom_nodes(custom_nodes_path_list):
    from folder_paths import add_model_folder_path
    for custom_nodes_path in custom_nodes_path_list:
        add_model_folder_path('custom_nodes', custom_nodes_path)


@ipc.restrict_to_process('comfyui')
def register_custom_scripts(custom_scripts_path_list):
    if not custom_scripts_path_list:
        return

    import server
    parsed_module = ast.parse(inspect.getsource(server.PromptServer))
    parsed_class = parsed_module.body[0]
    patch_prompt_server_init(parsed_class, custom_scripts_path_list)
    exec(compile(parsed_module, '<string>', 'exec'), server.__dict__)
    add_server__init__patch(functools.partial(patch_prompt_server_add_routes, custom_scripts_path_list=custom_scripts_path_list))


# patch for https://github.com/comfyanonymous/ComfyUI/blob/490771b7f495c95fb52875cf234fffc367162c7e/server.py#L123
def patch_prompt_server_init(parsed_class: ast.ClassDef, custom_scripts_path_list):
    """
    ComfyUI/serever.py

    ...
        @routes.get("/extensions")
        async def get_extensions(request):
            files = glob.glob(os.path.join(self.web_root, 'extensions/**/*.js'), recursive=True)
                <- add code right there
            return web.json_response(list(map(lambda f: "/" + os.path.relpath(f, self.web_root).replace("\\", "/"), files)))
    ...
    """
    init_ast_function = get_ast_function(parsed_class, '__init__')
    function_to_patch = get_ast_function(init_ast_function, 'get_extensions')
    for custom_scripts_path in custom_scripts_path_list:
        if not os.path.exists(os.path.join(custom_scripts_path, 'extensions')):
            continue

        code_patch = generate_prompt_server_init_code_patch(custom_scripts_path)
        extra_code = ast.parse(code_patch)
        function_to_patch.body[1:1] = extra_code.body


def generate_prompt_server_init_code_patch(custom_scripts_path):
    return textwrap.dedent(rf"""
        files.extend(os.path.join(self.web_root, "webui_scripts", "{os.path.basename(os.path.dirname(custom_scripts_path))}", os.path.relpath(f, r"{custom_scripts_path}")) 
        for f in glob.glob(r"{custom_scripts_path}/extensions/**/*.js", recursive=True))
    """)


# patch for https://github.com/comfyanonymous/ComfyUI/blob/6a7bc35db845179a26e62534f3d4b789151e52fe/server.py#L536
def patch_prompt_server_add_routes(self, *_, custom_scripts_path_list, **__):
    from aiohttp import web

    def add_routes_patch(*args, original_function, **kwargs):
        new_routes = [
            web.static(
                f"/webui_scripts/{os.path.basename(os.path.dirname(custom_scripts_path))}",
                fr"{custom_scripts_path}",
                follow_symlinks=True
            )
            for custom_scripts_path in custom_scripts_path_list
        ]
        self.app.add_routes(new_routes)
        original_function(*args, **kwargs)

    self.add_routes = functools.partial(add_routes_patch, original_function=self.add_routes)


def get_ast_function(parsed_object, function_name):
    res = [exp for exp in parsed_object.body if getattr(exp, 'name', None) == function_name]
    if not res:
        raise RuntimeError(f'Cannot find function {function_name} in parsed ast')

    return res[0]


@ipc.restrict_to_process('comfyui')
def add_server__init__patch(callback):
    import server
    original_init = server.PromptServer.__init__

    def patched_PromptServer__init__(*args, **kwargs):
        callback(*args, **kwargs)
        original_init(*args, **kwargs)

    server.PromptServer.__init__ = patched_PromptServer__init__
