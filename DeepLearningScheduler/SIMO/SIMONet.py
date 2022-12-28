# coding: utf-8
"""
Adapt from
LaneNet model
https://arxiv.org/pdf/1807.01726.pdf
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from loss import DiscriminativeLoss
# from backbone.UNet import UNet_Encoder, UNet_Decoder
from backbone.ENet import ENet_Encoder, ENet_Decoder
from backbone.MLP import MLP_Decoder
from backbone.Segmentation import Segmentation_Decoder
from backbone.ObjectDetection import ObjectDetection_Decoder
# from backbone.deeplabv3_plus.deeplabv3plus import Deeplabv3plus_Encoder, Deeplabv3plus_Decoder

DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

class SIMONet(nn.Module):
    def __init__(self, in_ch = 3, arch="ENet"):
        super(SIMONet, self).__init__()
        self.no_of_instances = 3  # if you want to output RGB instance map, it should be 3.
        print("Use {} as shared feature extractor (encoder)".format(arch))
        self._arch = arch
        if self._arch == 'ENet':
            self._encoder = ENet_Encoder(in_ch)
            self._encoder.to(DEVICE)

            self._decoder_binary = ENet_Decoder(2)
            self._decoder_instance = ENet_Decoder(self.no_of_instances)
            self._decoder_binary.to(DEVICE)
            self._decoder_instance.to(DEVICE)
            self._decoder_steering = MLP_Decoder()
            self._decoder_steering.to(DEVICE)
            self._decoder_segmetation = Segmentation_Decoder(out_ch=2)
            self._decoder_objdet = ObjectDetection_Decoder(out_ch=2)
            # self._decoder_segmetation = ..
        else:
            raise NotImplementedError

        self.relu = nn.ReLU().to(DEVICE)
        self.sigmoid = nn.Sigmoid().to(DEVICE)

    def forward(self, input_tensor):
        if self._arch == 'ENet':
            c1, c2, c3 = self._encoder(input_tensor)
            lanedet_binary = self._decoder_binary(c3)
            lanedet_instance = self._decoder_instance(c3)
            steering_regression = self._decoder_steering(c3)

            segmentation = self._decoder_segmetation(c1, c2, c3)
            objdetdetection = self._decoder_objdet(c3)

        else:
            raise NotImplementedError

        binary_seg_ret = torch.argmax(F.softmax(lanedet_binary, dim=1), dim=1, keepdim=True)
        pix_embedding = self.sigmoid(lanedet_instance)

        return {
            'instance_seg_logits': pix_embedding,
            'binary_seg_pred': binary_seg_ret,
            'binary_seg_logits': lanedet_binary,
            'steering_regression': steering_regression,
            'segmentation': segmentation,
            'objdet_detection': objdetdetection,
        }

if __name__ == "__main__":
    # !!!: can only accept (1, 3, 224, 224) as input for now
    model = SIMONet().to(DEVICE)
    print(model)
    input = torch.randn(1, 3, 224, 224).to(DEVICE)
    output = model(input)
    from thop import profile
    from thop import clever_format
    flops, params = profile(model, inputs=(input, ))
    flops, params = clever_format([flops, params], "%.3f")
    print(flops, params)
    # print(output)