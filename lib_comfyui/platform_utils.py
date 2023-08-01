import platform


def is_unix():
    return 'wsl' in platform.release().lower()
