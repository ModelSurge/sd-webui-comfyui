import os
import git


def main():
    git_repo_url = 'https://github.com/comfyanonymous/ComfyUI.git'
    install_location = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib_comfyui', 'ComfyUI')
    os.mkdir(install_location)
    git.Repo.clone_from(git_repo_url, install_location)


if __name__ == '__main__':
    main()
