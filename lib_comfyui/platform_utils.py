import platform


def is_windows():
    return 'windows' in platform.system().lower()
