from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QThreadPool,QThread
from PySide6.QtGui import QPixmap, QImage
import os
import sys
from pathlib import Path
import mmcv
from src.net.mmdet.apis import inference_detector, init_detector, show_result_pyplot
from mmcv import Config
from src.net.mmdet.utils import (build_ddp, build_dp, compat_cfg, get_device,
                         setup_multi_processes, update_data_root)
import cv2
import torch
from src.utils.globalclass import DetectionQueue

from src.utils.utils import load_basepath





class DetectorWorker(QThread):
    result_ready = Signal(object)
    message_signal = Signal(str,str)

    def __init__(self, model, palette):
        super().__init__()
        self.model = model
        self.palette = palette
        self.queue = DetectionQueue()
        self.running = True

    def stop(self):
        self.running = False
        self.queue.clear_all()
        

    def run(self):
        print("线程启动")
        while self.running:
            try:
                # 获取待处理图像（带500ms超时）
                image = self.queue.get_pending(timeout=10000)
                if image is not None:
                    # 转换为三通道
                    if image.ndim == 2:  # 灰度图
                        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                    elif image.shape[2] == 4:  # RGBA
                        image = image[..., :3]
                
                    result = inference_detector(self.model, image)

                    # 生成可视化结果
                    vis_image = self.model.show_result(
                        image, 
                        result,
                        bbox_color=self.palette,
                        text_color=self.palette,
                        mask_color=self.palette,
                        show=False,
                        score_thr=0.3
                    )
                    # 转换并存储结果
                    pixmap = self.numpy_to_pixmap(vis_image)
                    self.result_ready.emit(pixmap)
            except Exception as e:
                self.message_signal.emit('Error',f"检测失败: {str(e)}")
                self.running = False
                break

    @staticmethod
    def numpy_to_pixmap(image):
        height, width, _ = image.shape
        return QPixmap.fromImage(
            QImage(
                image.data, 
                width, 
                height, 
                3 * width, 
                QImage.Format_RGB888
            )
        )
# class DetectionTask(QRunnable):
#     result_ready = Signal(object)  # 发送numpy数组格式的图像
#     message_signal = Signal(str,str)
#     def __init__(self, detector, image_path, score_thr):
#         super().__init__()
#         self.detector = detector
#         self.image_path = image_path
#         self.score_thr = score_thr
        

#     @Slot()
#     def run(self):
#         try:
#             # 执行推理
#             result, image = self.detector._inference_impl(
#                 self.image_path, 
#                 self.score_thr
#             )
            
#             # 生成可视化结果
#             vis_image = self.detector._visualize_impl(
#                 image, 
#                 result,
#                 score_thr=self.score_thr
#             )
#             result_image=self.update_result(vis_image)
#             # 发送结果
#             self.result_ready.emit(result_image)
#         except Exception as e:
#             self.message_signal.emit('Error',f"检测失败: {str(e)}")


#     def update_result(self, image):
#         """将numpy数组转换为QPixmap显示"""
#         height, width, channel = image.shape
#         bytes_per_line = 3 * width
#         q_img = QImage(
#             image.data, 
#             width, 
#             height, 
#             bytes_per_line, 
#             QImage.Format_RGB888
#         )
#         return QPixmap.fromImage(q_img)

class Detector(QObject):
    result_ready = Signal(object)  # 发送numpy数组格式的图像
    message_signal = Signal(str,str)


    # config_file='./src/net/configs/autoassign/autoassign_r50_fpn_8x2_3x_gcc_duo.py', checkpoint_file='./src/net/epoch_36.pth'
    def __init__(self, config_file='autoassign_r50_fpn_8x2_3x_gcc_duo.py', checkpoint_file='epoch_36.pth'):
        super().__init__()
        config_file = os.path.join(load_basepath(),"src","net","configs","autoassign",config_file)
        checkpoint_file = os.path.join(load_basepath(),"src","net",checkpoint_file)
        print("初始化模型")
        self._init_detector(config_file, checkpoint_file)
        print("初始化模型完成")
        print("初始化线程")
        self.worker = DetectorWorker(self.model, self.palette)
        self._connect_signals()
        print("线程初始化完成")
        self.worker.start()
        print("线程启动完成")

    def _init_detector(self, config_file, checkpoint_file):

        
        """内部初始化方法"""
        self.cfg = mmcv.Config.fromfile(config_file)
        # self.device = get_device()
        # self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device ="cpu"
        self.model = init_detector(self.cfg, checkpoint_file, device=self.device)
        self.palette = [(255, 165, 79), (255, 69, 0), 
                       (138, 43, 226), (0, 0, 255)]
    def _connect_signals(self):
        self.worker.result_ready.connect(self.result_ready.emit)
        self.worker.message_signal.connect(self.message_signal.emit)
        self.worker.finished.connect(lambda: self.message_signal.emit("提示","检测线程已停止"))
    def _inference_impl(self, image, score_thr):
        """实际推理实现"""
        try:
            result = inference_detector(self.model, image)
            return result, image
        except Exception as e:
            raise RuntimeError(f"推理错误: {str(e)}")

    def _visualize_impl(self, image, result, score_thr):
        """实际可视化实现"""
        try:
            return self.model.show_result(
                image, 
                result,
                bbox_color=self.palette,
                text_color=self.palette,
                mask_color=self.palette,
                show=False,
                score_thr=score_thr
            )
        except Exception as e:
            raise RuntimeError(f"可视化错误: {str(e)}")

    def shoutdown(self):
        self.worker.stop()