# sd-webui-comfyui
## Overview
sd-webui-comfyui is an extension for [Automatic1111's stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) that embeds [ComfyUI](https://github.com/comfyanonymous/ComfyUI) workflows in different sections of the normal pipeline of the webui. This allows to create ComfyUI nodes that interact directly with some parts of the webui's normal pipeline.

![front-page-gif](/resources/front-page.gif)

## Features
- Use ComfyUI directly into the Webui
- Support for [loading custom nodes from other Webui extensions](https://github.com/ModelSurge/sd-webui-comfyui/wiki/Developing-custom-nodes-from-webui-extensions)
- Integration of [ComfyUI workflows](https://github.com/ModelSurge/sd-webui-comfyui/wiki/Developing-custom-workflow-types) directly into the Webui's pipeline, such as `preprocess`, `preprocess (latent)`, `unet`, `postprocess (latent)`, `postprocess`, `transformer text encode`, etc. 
- Webui nodes for sharing resources and data, such as the model, the prompt, etc.

For a full overview of all the advantageous features this extension adds to ComfyUI and to the Webui, check out the [wiki page](https://github.com/ModelSurge/sd-webui-comfyui/wiki). 

## Supported versions
- A1111's Webui >= `V1.5.1`
- ComfyUI == `Latest`

## Installation
1) Go to Extensions > Available
2) Click the `Load from:` button
3) Enter "ComfyUI" in the search bar
4) Click the `Install` button of the ComfyUI Tab cell
5) Restart the webui
6) Go to the `ComfyUI` tab, and follow the instructions

## Contributing
We welcome contributions from anyone who is interested in improving sd-webui-comfyui. If you would like to contribute, please follow these steps:

1) Fork the repository and create a new branch for your feature or bug fix.
2) Implement your changes, adding any necessary documentation and tests.
3) Submit a pull request.
4) We will review your contribution as soon as possible and provide feedback.

## License
MIT

## Contact
If you have any questions or concerns, please leave an issue, or start a thread in the discussions.

Thank you for your interest!
