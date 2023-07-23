import platform


def is_wsl():
    return 'wsl' in platform.release().lower()


def is_unsupported_platform():
    return is_wsl()
