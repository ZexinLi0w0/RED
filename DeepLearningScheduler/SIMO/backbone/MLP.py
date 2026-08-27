# coding: utf-8
import torch
from torch.nn import init
from torch import nn
import torch.nn.functional as F
from torch.autograd import Variable
from runtime_device import configure_torch_device

DEVICE = configure_torch_device()


def _adaptive_avg_pool2d_exact(x, output_size):
    """Portable adaptive average pooling for MPS non-divisible dimensions.

    PyTorch's MPS backend currently rejects adaptive pooling when an input
    dimension is not divisible by the requested output dimension. The slices
    below implement the same floor/ceil bin boundaries as adaptive average
    pooling while keeping the tensor on the accelerator.
    """
    output_height, output_width = output_size
    input_height, input_width = x.shape[-2:]
    rows = []
    for output_row in range(output_height):
        height_start = output_row * input_height // output_height
        height_end = (
            (output_row + 1) * input_height + output_height - 1
        ) // output_height
        columns = []
        for output_column in range(output_width):
            width_start = output_column * input_width // output_width
            width_end = (
                (output_column + 1) * input_width + output_width - 1
            ) // output_width
            columns.append(
                x[..., height_start:height_end, width_start:width_end].mean(
                    dim=(-2, -1)
                )
            )
        rows.append(torch.stack(columns, dim=-1))
    return torch.stack(rows, dim=-2)

def weights_init_kaiming(m):
    classname = m.__class__.__name__
    #print(classname)
    if classname.find('Conv') != -1:
        init.kaiming_normal_(m.weight.data, a=0, mode='fan_in')
    elif classname.find('Linear') != -1:
        init.kaiming_normal_(m.weight.data, a=0, mode='fan_in')
    elif classname.find('BatchNorm') != -1:
        init.normal_(m.weight.data, 1.0, 0.02)
        init.constant_(m.bias.data, 0.0)

class MLP_Decoder(nn.Module):
    def __init__(self, output: int = 1, dropout: float = 0.5) -> None:
        super().__init__()

        # for loss function
        self.criteria = nn.MSELoss(reduction='mean')

        self.avgpool = nn.AdaptiveAvgPool2d((6, 6))
        self.mlp = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(128 * 6 * 6, 1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, output),
        )

        for m in self.mlp:
            if isinstance(m, nn.Conv2d):
                weights_init_kaiming(m)
            elif isinstance(m, nn.BatchNorm2d):
                weights_init_kaiming(m)


    def forward(self, x: torch.Tensor) -> torch.Tensor:
        self.beta_x = 1.0 / 0.0382
        if x.device.type == "mps" and (
            x.shape[-2] % 6 != 0 or x.shape[-1] % 6 != 0
        ):
            x = _adaptive_avg_pool2d_exact(x, (6, 6))
        else:
            x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.mlp(x)
        # (0.0382 * x): [-1.57, 1.57]
        x = self.beta_x * torch.tanh(1.0 / self.beta_x * x)
        return x
