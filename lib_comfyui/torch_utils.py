import torch
from typing import Union


def deep_to(
    tensor: Union[torch.Tensor, dict, list],
    device: torch.device,
) -> Union[torch.Tensor, dict, list]:
    if isinstance(tensor, torch.Tensor):
        tensor = tensor.to(device=device)
    elif isinstance(tensor, dict):
        for k, v in tensor.items():
            tensor[k] = deep_to(v, device=device)
    elif isinstance(tensor, list):
        for i, v in enumerate(tensor):
            tensor[i] = deep_to(v, device=device)
    elif isinstance(tensor, tuple):
        res = ()
        for v in tensor:
            res += (deep_to(v, device=device),)
        tensor = res

    return tensor
