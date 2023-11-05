import os
import sys


default_install_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ComfyUI', 'custom_nodes', 'ComfyUI-Manager')


def main(install_location):
    import git
    git_repo_url = 'https://github.com/ltdrdata/ComfyUI-Manager.git'
    os.mkdir(install_location)
    git.Repo.clone_from(git_repo_url, install_location)


if __name__ == '__main__':
    install_location = default_install_location
    if len(sys.argv) > 1:
        inistall_location = sys.argv[1]

    main(install_location)
