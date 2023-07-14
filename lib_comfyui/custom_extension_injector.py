import os
import inspect
import ast
import textwrap
from lib_comfyui.find_extensions import get_extension_paths_to_load


webui_custom_nodes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'comfyui_custom_nodes')
webui_custom_scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'comfyui_custom_scripts')
webui_extensions_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def register_webui_extensions():
    node_paths, script_paths = get_extension_paths_to_load()
    register_custom_nodes(node_paths)
    register_custom_scripts(script_paths)


def register_custom_nodes(custom_nodes_path_list):
    from folder_paths import add_model_folder_path
    for custom_nodes_path in custom_nodes_path_list:
        add_model_folder_path('custom_nodes', custom_nodes_path)


def register_custom_scripts(custom_scripts_path_list):
    if not custom_scripts_path_list:
        return
    import server
    m = ast.parse(source(server.PromptServer))
    patch_prompt_server_init(m, custom_scripts_path_list)
    patch_prompt_server_add_routes(m, custom_scripts_path_list)
    exec(compile(m, '<string>', 'exec'), server.__dict__)


def patch_prompt_server_init(m, custom_scripts_path_list):
    init_ast_function = get_ast_function(m.body[0], '__init__')
    function_to_patch = get_ast_function(init_ast_function, 'get_extensions')
    code_patch = generate_prompt_server_init_code_patch(custom_scripts_path_list)
    extra_code = ast.parse(textwrap.dedent(code_patch))
    function_to_patch.body[1:1] = extra_code.body


def generate_prompt_server_init_code_patch(custom_scripts_path_list):
    return '\\n'.join(
        [rf'''
            files.extend(
                os.path.join(self.web_root, "webui-scripts", "{os.path.basename(os.path.dirname(custom_scripts_path))}", os.path.relpath(f, r"{custom_scripts_path}"))
                for f in glob.glob(r"{custom_scripts_path}/extensions/**/*.js", recursive=True))
        '''
            for custom_scripts_path in custom_scripts_path_list])


def patch_prompt_server_add_routes(m, custom_scripts_path_list):
    add_routes_ast_function = get_ast_function(m.body[0], 'add_routes')
    code_patch = generate_prompt_server_add_routes_code_patch(custom_scripts_path_list)
    extra_line_of_code = ast.parse(code_patch)
    add_routes_ast_function.body[1].value.args[0].elts.insert(0, extra_line_of_code.body[0].value)


def generate_prompt_server_add_routes_code_patch(custom_scripts_path_list):
    return '\\n'.join(
        [rf'web.static("/webui-scripts/{os.path.basename(os.path.dirname(custom_scripts_path))}", r"{custom_scripts_path}", follow_symlinks=True)'
            for custom_scripts_path in custom_scripts_path_list])


def get_ast_function(m, function_name):
    res = [exp for exp in m.body if getattr(exp, 'name', None) == function_name]

    if not res:
        raise RuntimeError(f'Cannot find function {function_name} in parsed ast')

    return res[0]


def source(o):
    s = inspect.getsource(o).split('\n')
    indent = len(s[0]) - len(s[0].lstrip())
    return '\n'.join(i[indent:] for i in s)
