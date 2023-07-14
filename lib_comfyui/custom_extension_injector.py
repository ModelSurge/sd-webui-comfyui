import os
import inspect
import ast
import textwrap


webui_custom_nodes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'comfyui_custom_nodes')
webui_custom_scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'comfyui_custom_scripts')
webui_extensions_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def register_webui_extensions():
    register_custom_nodes()
    register_custom_scripts()


def register_custom_nodes():
    from folder_paths import add_model_folder_path
    add_model_folder_path('custom_nodes', webui_custom_nodes_path)


def register_custom_scripts():
    import server

    m = ast.parse(source(server.PromptServer))
    patch_prompt_server_init(m)
    patch_prompt_server_add_routes(m)
    exec(compile(m, '<string>', 'exec'), server.__dict__)


def patch_prompt_server_init(m):
    init_ast_function = get_ast_function(m.body[0], '__init__')
    function_to_patch = get_ast_function(init_ast_function, 'get_extensions')
    extra_code = ast.parse(textwrap.dedent(rf'''
        files.extend(
            os.path.join(self.web_root, "webui_scripts", "sd-webui-comfyui", os.path.relpath(f, r"{webui_custom_scripts_path}"))
            for f in glob.glob(r"{webui_custom_scripts_path}/extensions/**/*.js", recursive=True))
    '''))
    function_to_patch.body[1:1] = extra_code.body


def patch_prompt_server_add_routes(m):
    add_routes_ast_function = get_ast_function(m.body[0], 'add_routes')
    extra_line_of_code = ast.parse(rf'web.static("/webui_scripts/sd-webui-comfyui", r"{webui_custom_scripts_path}", follow_symlinks=True)')
    add_routes_ast_function.body[1].value.args[0].elts.insert(0, extra_line_of_code.body[0].value)


def get_ast_function(m, function_name):
    res = [exp for exp in m.body if getattr(exp, 'name', None) == function_name]

    if not res:
        raise RuntimeError(f'Cannot find function {function_name} in parsed ast')

    return res[0]


def source(o):
    s = inspect.getsource(o).split('\n')
    indent = len(s[0]) - len(s[0].lstrip())
    return '\n'.join(i[indent:] for i in s)
