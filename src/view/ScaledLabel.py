from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget,QSizePolicy
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class ScaledLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中显示
        # self.setScaledContents(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.original_pixmap = QPixmap()  # 保存原始图像

    def set_pixmap(self, pixmap):
        """设置原始图像并触发缩放"""
        self.original_pixmap = pixmap
        self.resize_pixmap()

    def resize_pixmap(self):
        """根据当前控件尺寸缩放图像"""
        if not self.original_pixmap.isNull():
            # 缩放图像，保持宽高比，使用平滑变换
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """重写尺寸变化事件"""
        # print(self.size())
        self.resize_pixmap()
        super().resizeEvent(event)
