import os
import git
import modules.scripts as scripts


automatic_install_location = os.path.join(scripts.basedir(), 'lib_comfyui', 'ComfyUI')


def main(install_location):
    git_repo_url = 'https://github.com/comfyanonymous/ComfyUI.git'
    os.mkdir(install_location)
    git.Repo.clone_from(git_repo_url, install_location)


if __name__ == '__main__':
    main(os.path.join(scripts.basedir(), 'lib_comfyui', 'ComfyUI'))
