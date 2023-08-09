import os
import pickle
import subprocess
import sys


def setup_test_env():
    extension_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if extension_root not in sys.path:
        sys.path.append(extension_root)

def worker_args(*args, **kwargs):
    return args, kwargs


def subprocess_worker(args):
    args, kwargs = args
    return run_subprocess(*args, **kwargs)


def run_subprocess(file, func, *args, **kwargs):
    # Read the source of the current file
    with open(file, 'r') as f:
        current_file_source = f.read()

    with open(__file__, 'r') as f:
        utils_source_file = f.read()

    args = f"pickle.loads({pickle.dumps(args)})"
    kwargs = f"pickle.loads({pickle.dumps(kwargs)})"
    dump_func_call_source = f"pickle.dumps({func.__name__}(*{args}, **{kwargs}))"

    # Craft the command to include the entire current file source, function definition, and function execution
    command = [
        sys.executable,
        '-c',
        '\n'.join([
            '__name__ += ".subprocess"',
            current_file_source,
            utils_source_file,
            f'sys.stdout.buffer.write({dump_func_call_source})',
        ]),
    ]

    # Start the subprocess with stdout piped
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Get the output and wait for the subprocess to finish
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Subprocess failed with error code {proc.returncode} and message: {err.decode('utf-8')}")

    # Convert the pickled stdout data back to a Python object
    return pickle.loads(out)
