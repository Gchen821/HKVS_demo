import os
import mmcv
from src.net.mmdet.apis import inference_detector, init_detector, show_result_pyplot
from mmcv import Config
from src.net.mmdet.utils import (build_ddp, build_dp, compat_cfg, get_device,
                         setup_multi_processes, update_data_root)
import cv2
device = get_device()
config_file='./src/net/configs/autoassign/autoassign_r50_fpn_8x2_3x_gcc_duo.py'
checkpoint_file='./src/net/epoch_36.pth'
cfg = Config.fromfile(config_file)

# 根据配置文件和 checkpoint 文件构建模型
model = init_detector(cfg, checkpoint_file, device=device)

file_path="F:/dataset/DUO/DUO/images/test/1.jpg"
PALETTE=[(255, 165, 79), (255, 69, 0), (138, 43, 226), (0, 0, 255)]
image = mmcv.imread(file_path)
for i in range(10):
    print("===================================")
    print(i)
    result = inference_detector(model, image)
    img_result=model.show_result(
                        image,
                        result,
                        bbox_color=PALETTE,
                        text_color=PALETTE,
                        mask_color=PALETTE,
                        show=False,
                        out_file=None,
                        score_thr=0.3)

cv2.imwrite("result.jpg", img_result)
print("save result")