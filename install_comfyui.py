import os
import sys
import git


default_install_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ComfyUI')


def main(install_location):
    git_repo_url = 'https://github.com/comfyanonymous/ComfyUI.git'
    os.mkdir(install_location)
    git.Repo.clone_from(git_repo_url, install_location)


if __name__ == '__main__':
    install_location = default_install_location
    if len(sys.argv) > 1:
        inistall_location = sys.argv[1]

    main(install_location)
