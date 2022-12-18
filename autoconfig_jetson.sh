sudo nvpmodel -m 0
conda activate pytorch
cd ATC23/
git clone git@github.com:ZexinLi0w0/lanenet-lane-detection-pytorch.git
git clone git@github.com:ZexinLi0w0/Pytorch-UNet.git
git clone git@github.com:ZexinLi0w0/yolov5.git
sudo apt-get install libjpeg-dev zlib1g-dev libpython3-dev
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev
/experiment/miniforge3/envs/pytorch/bin/pip install pillow
/experiment/miniforge3/envs/pytorch/bin/pip install gdown
gdown https://drive.google.com/uc?id=1BdvXkwUGGTTamM17Io4kkjIT6zgvf4BJ
/experiment/miniforge3/envs/pytorch/bin/pip install torchvision-0.9.0a0+01dfa8e-cp36-cp36m-linux_aarch64.whl
/experiment/miniforge3/envs/pytorch/bin/pip install opencv-python pandas scikit-image
conda install matplotlib
cd Pytorch-UNet
wget https://github.com/milesial/Pytorch-UNet/releases/download/v3.0/unet_carvana_scale0.5_epoch2.pth
wget https://github.com/milesial/Pytorch-UNet/releases/download/v3.0/unet_carvana_scale1.0_epoch2.pth
cd ..
/experiment/miniforge3/envs/pytorch/bin/pip install ipython
/experiment/miniforge3/envs/pytorch/bin/pip install psutil
/experiment/miniforge3/envs/pytorch/bin/pip install pyyaml
/experiment/miniforge3/envs/pytorch/bin/pip install seaborn
