import torch
from typing import Union


def deep_to(
    tensor: Union[torch.Tensor, dict, list],
    *args,
    **kwargs,
) -> Union[torch.Tensor, dict, list]:
    if isinstance(tensor, torch.Tensor):
        tensor = tensor.to(*args, **kwargs)
    elif isinstance(tensor, dict):
        for k, v in tensor.items():
            tensor[k] = deep_to(v, *args, **kwargs)
    elif isinstance(tensor, list):
        for i, v in enumerate(tensor):
            tensor[i] = deep_to(v, *args, **kwargs)
    elif isinstance(tensor, tuple):
        res = ()
        for v in tensor:
            res += (deep_to(v, *args, **kwargs),)
        tensor = res

    return tensor
