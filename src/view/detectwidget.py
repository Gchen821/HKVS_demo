from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt,Signal
from qfluentwidgets import (
    PrimaryPushButton, PushButton, RadioButton, SpinBox,
    FluentWindow, ComboBox, BodyLabel,MessageBox,DoubleSpinBox,StrongBodyLabel,PrimaryToolButton,
    setTheme, Theme, GroupHeaderCardWidget,CardWidget,HeaderCardWidget,FlowLayout
)
from src.net.DetectModel import Detector


class DetectionResultWidget(QWidget):
    detect_stop=Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("水下图像检测")  # 设置窗口标题
        self.setFixedSize(800, 600)  # 设置窗口固定大小
        print("开始加载模型...")
        self.model=Detector()
        print("水下图像检测","模型加载完成...")
        self.model.result_ready.connect(self.update_result)
        self.model.message_signal.connect(self.showDialog)

        # 创建 QLabel 显示检测结果
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)  # 居中对齐

        # 布局管理
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_result(self, image):
        self.label.setPixmap(image)
    def showDialog(self,title,content):
        # w = MessageDialog(title, content, self)   # Win10 style message box
        w = MessageBox(title, content, self)
        # close the message box when mask is clicked
        w.setClosableOnMaskClicked(True)
        w.cancelButton.hide()
        w.buttonLayout.insertStretch(1)
        w.exec()

    def closeEvent(self, event):
        """重写关闭事件处理"""
        # 执行清理操作
        self.model.shoutdown()
        self.detect_stop.emit()
        # 确认关闭
        event.accept()
        
