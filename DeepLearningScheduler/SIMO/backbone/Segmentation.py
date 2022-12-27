# coding: utf-8
"""
Decoder for segmentation (fit by ENet)
"""

import torch
from torch.nn import init
from torch import nn


def weights_init_kaiming(m):
    classname = m.__class__.__name__
    # print(classname)
    if classname.find('Conv') != -1:
        init.kaiming_normal_(m.weight.data, a=0, mode='fan_in')
    elif classname.find('Linear') != -1:
        init.kaiming_normal_(m.weight.data, a=0, mode='fan_in')
    elif classname.find('BatchNorm') != -1:
        init.normal_(m.weight.data, 1.0, 0.02)
        init.constant_(m.bias.data, 0.0)


class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(DoubleConv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )

    def forward(self, input):
        return self.conv(input)

class Segmentation_Decoder(nn.Module):
    def __init__(self, out_ch):
        super(Segmentation_Decoder, self).__init__()
        self.n_classes = out_ch

        self.up1 = nn.ConvTranspose2d(128, 128, 1, stride=1)
        # self.up6 = nn.ConvTranspose2d(128, 128, 2, stride=2)
        self.conv1 = DoubleConv(256, 256)
        self.up2 = nn.ConvTranspose2d(256, 64, 2, stride=2) # [1, 64, 56, 56]
        self.conv2 = DoubleConv(128, 64)
        self.up3 = nn.ConvTranspose2d(64, 64, 2, stride=2) # [1, 64, 112, 112]
        self.up4 = nn.ConvTranspose2d(64, 64, 2, stride=2) # [1, 64, 224, 224]

        self.conv10 = nn.Conv2d(64, out_ch, 1)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                weights_init_kaiming(m)
            elif isinstance(m, nn.BatchNorm2d):
                weights_init_kaiming(m)

    def forward(self, c1, c2, c3):
        # c1: [1, 64, 56, 56]; c2: [1, 128, 28, 28]; c3: [1, 128, 28, 28]
        up_1 = self.up1(c3) # [1, 128, 28, 28]
        merge1 = torch.cat([up_1, c2], dim=1)
        c4 = self.conv1(merge1)
        up_2 = self.up2(c4) # [1, 256, 28, 28]
        merge2 = torch.cat([up_2, c1], dim=1)
        c5 = self.conv2(merge2) # [1, 64, 56, 56]

        c6 = self.up3(c5) # [1, 64, 112, 112]
        c7 = self.up4(c6) # [1, 64, 224, 224]
        c8 = self.conv10(c7) # [1, class_num, 224, 224]

        return c8