import os
import inspect
import ast
import textwrap

webui_custom_nodes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'comfyui_custom_nodes')
webui_custom_scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'comfyui_custom_scripts')


def register_webui_extensions():
    register_custom_nodes()
    register_custom_scripts()


def register_custom_nodes():
    from folder_paths import add_model_folder_path
    add_model_folder_path('custom_nodes', webui_custom_nodes_path)


# This patching code was highly inspired by this article:
# Source: https://medium.com/@chipiga86/python-monkey-patching-like-a-boss-87d7ddb8098e
def register_custom_scripts():
    import server

    parsed_module = ast.parse(textwrap.dedent(inspect.getsource(server.PromptServer)))
    parsed_class = parsed_module.body[0]
    patch_prompt_server_init(parsed_class)
    patch_prompt_server_add_routes(parsed_class)
    exec(compile(parsed_module, '<string>', 'exec'), server.__dict__)


def patch_prompt_server_init(parsed_class: ast.ClassDef):
    init_ast_function = get_ast_function(parsed_class, '__init__')
    function_to_patch = get_ast_function(init_ast_function, 'get_extensions')
    extra_code = ast.parse(textwrap.dedent(rf'''
        files.extend(
            os.path.join(self.web_root, "webui_scripts", "sd-webui-comfyui", os.path.relpath(f, r"{webui_custom_scripts_path}"))
            for f in glob.glob(r"{webui_custom_scripts_path}/extensions/**/*.js", recursive=True))
    '''))
    function_to_patch.body[1:1] = extra_code.body


def patch_prompt_server_add_routes(parsed_class: ast.ClassDef):
    add_routes_ast_function = get_ast_function(parsed_class, 'add_routes')
    extra_line_of_code = ast.parse(rf'web.static("/webui_scripts/sd-webui-comfyui", r"{webui_custom_scripts_path}", follow_symlinks=True)')
    add_routes_ast_function.body[1].value.args[0].elts.insert(0, extra_line_of_code.body[0].value)


def get_ast_function(parsed_object, function_name: str):
    res = [exp for exp in parsed_object.body if getattr(exp, 'name', None) == function_name]

    if not res:
        raise RuntimeError(f'Cannot find function {function_name} in parsed ast')

    return res[0]
