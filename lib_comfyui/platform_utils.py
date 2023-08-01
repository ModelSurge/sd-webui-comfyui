import platform


def is_unix():
    return 'windows' not in platform.system().lower()
