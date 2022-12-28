# coding: utf-8
"""
Adapt from
LaneNet model
https://arxiv.org/pdf/1807.01726.pdf
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import argparse
import sys
import glob
import cv2
import numpy as np

from loss import DiscriminativeLoss
# from backbone.UNet import UNet_Encoder, UNet_Decoder
from backbone.ENet import ENet_Encoder, ENet_Decoder
from backbone.MLP import MLP_Decoder
from backbone.Segmentation import Segmentation_Decoder
from backbone.ObjectDetection import ObjectDetection_Decoder
# from backbone.deeplabv3_plus.deeplabv3plus import Deeplabv3plus_Encoder, Deeplabv3plus_Decoder

from utils.general import non_max_suppression, scale_coords

DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

def resize_img(img0, new_shape=(736, 1280), color=(114, 114, 114)):
    shape = img0.shape[:2]
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

    unpad_shape = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - unpad_shape[0], new_shape[0] - unpad_shape[1]  # wh padding

    img = cv2.resize(img0, unpad_shape, interpolation=cv2.INTER_LINEAR)

    dw, dh = dw/2, dh/2
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

    return img

class SIMONet(nn.Module):
    def __init__(self, in_ch = 3, arch="ENet"):
        super(SIMONet, self).__init__()
        self.no_of_instances = 3  # if you want to output RGB instance map, it should be 3.
        print("Use {} as shared feature extractor (encoder)".format(arch))
        self._arch = arch
        if self._arch == 'ENet':
            self._encoder = ENet_Encoder(in_ch)
            self._encoder.to(DEVICE)

            '''
                binary lane detection: use ENet decoder
                ENet: https://arxiv.org/pdf/1606.02147.pdf
            '''
            self._decoder_binary = ENet_Decoder(2)
            '''
                instance lane detection: use ENet decoder
                ENet: https://arxiv.org/pdf/1606.02147.pdf
            '''
            self._decoder_instance = ENet_Decoder(self.no_of_instances)
            '''
                steering regression: use MLP followed by AveragePooling
                AutoPilot: https://arxiv.org/pdf/1604.07316.pdf
            '''
            self._decoder_steering = MLP_Decoder()
            '''
                segmentation: adapt UNet decoder in this case
                UNet: https://arxiv.org/pdf/1505.04597.pdf
            '''
            self._decoder_segmetation = Segmentation_Decoder(out_ch=2)


            io_params = {
                    "num_cls": 1,
                    "anchors": [[[12, 18], [37, 49], [52, 132]],
                        [[115, 73], [119, 199], [242, 238]]]}
            '''
                object detection: adapt YOLO-Fastest decoder in this case
                YOLO: https://arxiv.org/abs/1506.02640
            '''
            self._decoder_objdet = ObjectDetection_Decoder(io_params=io_params)

            self._decoder_binary.to(DEVICE)
            self._decoder_instance.to(DEVICE)
            self._decoder_steering.to(DEVICE)
            self._decoder_steering.to(DEVICE)
            self._decoder_objdet.to(DEVICE)
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

    # adapt from YOLO-Fastest
    def detect(self, args):
        from config.config import params

        io_params = params["io_params"]
        names = io_params["names"]
        colors = [[np.random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

        # model = YoloFastest(io_params).cuda()
        #
        # ckpt = torch.load(args.weights)
        # model.load_state_dict(ckpt)
        #
        # # warm up
        # img = torch.zeros((1, 3, 640, 640)).cuda()
        # _ = model(img)

        def _preprocess(img_path):
            print(img_path)

            img0 = cv2.imread(img_path)
            img = resize_img(img0, new_shape=(224, 224))
            img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB
            img = np.ascontiguousarray(img)

            img = torch.from_numpy(img).cuda().float() / 255.0

            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            return img0, img

        img_lists = glob.glob(args.root_dir + '*.jpg')
        for img_path in img_lists:
            raw_img, img = _preprocess(img_path)
            pred = self.forward(img)['objdet_detection']

            out = []
            strides = io_params["strides"]
            for i, pred_s in enumerate(pred):
                pred_s = pred_s[0]  # 第一个batch

                (_, h, w) = pred_s.shape
                out_channel = io_params["num_cls"] + 5
                pred_s = pred_s.view(1, 3, out_channel, h, w).permute(0, 1, 3, 4, 2).contiguous()

                yv, xv = torch.meshgrid([torch.arange(h), torch.arange(w)])
                grid = torch.stack((xv, yv), 2).view((1, 1, h, w, 2)).float().to(pred_s.device)

                # bbox
                anchors = io_params["anchors"][i]
                anchors = torch.tensor(anchors).float().view(3, -1, 2)
                anchors = anchors.clone().view(1, -1, 1, 1, 2).to(pred_s.device)

                pred_s = pred_s.sigmoid()
                pred_s[..., 0:2] = (pred_s[..., 0:2] * 2. - 0.5 + grid) * strides[i]  # x,y
                pred_s[..., 2:4] = (pred_s[..., 2:4] * 2) ** 2 * anchors  # w,h

                out.append(pred_s.view(1, -1, out_channel))

            out = torch.cat(out, dim=1)

            # # output = [[x1,y1,x2,y2,conf,cls], [....]]   batch_size张图片的检测结果,放在list里面
            output = non_max_suppression(out, conf_thres=args.conf_thres)

            det = output[0]  # detect阶段batch size为1
            if det is not None and len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], img0.shape).round()

                # draw results
                det = det.cpu()
                for i in range(det.shape[0]):
                    x1, y1, x2, y2 = int(det[i][0]), int(det[i][1]), int(det[i][2]), int(det[i][3])
                    conf = float(det[i][4])
                    cls = int(det[i][5])

                    cv2.rectangle(raw_img, (x1, y1), (x2, y2), color=colors[int(cls)], thickness=1)
                    txt = '%s %.2f' % (names[cls], conf)
                    cv2.putText(raw_img, txt, (x1, y1 - 2), fontFace=0, fontScale=0.6, color=(225, 255, 255),
                                lineType=cv2.LINE_AA)

            cv2.imshow("test", raw_img)
            key = cv2.waitKey(0)
            if key == 27:
                sys.exit()


def check(input, output):
    assert input.shape == (1, 3, 224, 224), "[input error] input shape is wrong"

    assert output['instance_seg_logits'].shape == (1, 3, 224, 224), "[output error] instance_seg_logits shape is wrong"
    assert output['binary_seg_pred'].shape == (1, 1, 224, 224), "[output error] binary_seg_pred shape is wrong"
    assert output['binary_seg_logits'].shape == (1, 2, 224, 224), "[output error] binary_seg_logits shape is wrong"
    assert output['steering_regression'].shape == (1, 1), "[output error] steering_regression shape is wrong"
    assert output['segmentation'].shape == (1, 2, 224, 224), "[output error] segmentation shape is wrong"
    assert output['objdet_detection'][0].shape == (1, 18, 14, 14), "[output error] objdet_detection shape is wrong"
    assert output['objdet_detection'][1].shape == (1, 18, 7, 7), "[output error] objdet_detection shape is wrong"

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

    import pdb; pdb.set_trace()
    check(input, output)
    # print(output)
