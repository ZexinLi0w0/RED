# coding: utf-8
import torch
from torch.nn import init
from torch import nn
import torch.nn.functional as F
from torch.autograd import Variable

DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

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
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.mlp(x)
        # (0.0382 * x): [-1.57, 1.57]
        x = self.beta_x * torch.tanh(1.0 / self.beta_x * x)
        return x