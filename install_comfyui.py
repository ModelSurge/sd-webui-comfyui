import os
import sys


default_install_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ComfyUI')


def main(install_location):
    import git
    git_repo_url = 'https://github.com/comfyanonymous/ComfyUI.git'
    os.mkdir(install_location)
    git.Repo.clone_from(git_repo_url, install_location)


def update(install_location):
    print("[sd-webui-comfyui]", f"Updating comfyui at {install_location}...")
    import git
    repo = git.Repo(install_location)
    current = repo.head.commit
    repo.remotes.origin.pull()
    if current == repo.head.commit:
        print("[sd-webui-comfyui", "Already up to date.")
    else:
        print("[sd-webui-comfyui]", "Done updating comfyui.")


if __name__ == '__main__':
    install_location = default_install_location
    if len(sys.argv) > 1:
        inistall_location = sys.argv[1]

    main(install_location)
