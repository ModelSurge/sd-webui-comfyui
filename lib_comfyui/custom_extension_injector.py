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
    patch_prompt_server_add_routes(parsed_class, custom_scripts_path_list)
    exec(compile(parsed_module, '<string>', 'exec'), server.__dict__)


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


# patch for https://github.com/comfyanonymous/ComfyUI/blob/490771b7f495c95fb52875cf234fffc367162c7e/server.py#L487
def patch_prompt_server_add_routes(parsed_class: ast.ClassDef, custom_scripts_path_list):
    """
    ComfyUI/serever.py

    ...
        def add_routes(self):
            self.app.add_routes(self.routes)
            self.app.add_routes([
                    <- add code right there in the list
                web.static('/', self.web_root, follow_symlinks=True),
            ])
    ...
    """
    add_routes_ast_function = get_ast_function(parsed_class, 'add_routes')
    for custom_scripts_path in custom_scripts_path_list:
        code_patch = generate_prompt_server_add_routes_code_patch(custom_scripts_path)
        extra_line_of_code = ast.parse(code_patch)
        try:
            add_routes_ast_function.body[2].value.args[0].elts[0:0] = [extra_line_of_code.body[0].value]
        except:
            raise RuntimeError("Cannot patch comfyui as it is not up to date")


def generate_prompt_server_add_routes_code_patch(custom_scripts_path):
    return rf'web.static("/webui_scripts/{os.path.basename(os.path.dirname(custom_scripts_path))}", r"{custom_scripts_path}", follow_symlinks=True)'


def get_ast_function(parsed_object, function_name):
    res = [exp for exp in parsed_object.body if getattr(exp, 'name', None) == function_name]
    if not res:
        raise RuntimeError(f'Cannot find function {function_name} in parsed ast')

    return res[0]
