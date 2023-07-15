# sd-webui-comfyui
## Overview
sd-webui-comfyui is an extension for [Automatic1111's stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) that embeds [ComfyUI](https://github.com/comfyanonymous/ComfyUI) in its own tab. This allows to create ComfyUI nodes that interact directly with some parts of the webui's normal pipeline.

![ezgif com-video-to-gif(1)](https://user-images.githubusercontent.com/34081873/226529347-23e61102-cf83-457e-b94c-89337fd38c4d.gif)

## Features
- [x] Load comfyui directly into the webui
- [x] Support for [loading custom nodes from other webui extensions](https://github.com/ModelSurge/sd-webui-comfyui/wiki/Developing-custom-nodes-from-webui-extensions)
- [ ] Nodes for pre/post-processing image generations in the webui. 
- [x] Webui node: [`Load Webui Checkpoint`](https://github.com/ModelSurge/sd-webui-comfyui/wiki/Webui-Nodes)
- [ ] Webui node: `Latent Webui Noise Generator`
- [ ] Webui node: `Webui Prompt Parser`

For a full overview of all the advantageous features this extension adds to ComfyUI, check out the [wiki page](https://github.com/ModelSurge/sd-webui-comfyui/wiki). 

## Installation
1) Go to Extensions > Install from URL
2) Paste `https://github.com/ModelSurge/sd-webui-comfyui` in the `URL for extension's git repository` text field
3) Click the `Install` button
4) Restart the webui
5) Go to the `ComfyUI` tab, and follow the instructions

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
