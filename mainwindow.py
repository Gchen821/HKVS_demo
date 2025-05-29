# This Python file uses the following encoding: utf-8
import sys
import os
from PySide6.QtWidgets import QApplication,QMainWindow, QSplitter, QHBoxLayout, QVBoxLayout, QButtonGroup,QWidget,QFormLayout,QLabel,QSizePolicy,QGridLayout,QFileDialog
from PySide6.QtCore import Qt,QProcess,QEasingCurve
from PySide6.QtGui import QIcon
from qfluentwidgets import (
    PrimaryPushButton, PushButton, RadioButton, SpinBox,
    FluentWindow, ComboBox, BodyLabel,MessageBox,DoubleSpinBox,StrongBodyLabel,PrimaryToolButton,
    setTheme, Theme, GroupHeaderCardWidget,CardWidget,HeaderCardWidget,FlowLayout
)
from qfluentwidgets import FluentIcon as FIF
from src.hkvs.CameraController import CameraController
import threading
from src.view.detectwidget import DetectionResultWidget
from src.view.ScaledLabel import ScaledLabel
from src.utils.utils import load_basepath

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HKVS")

        # 设置窗口样式，应用圆角边框
        self.setMinimumSize(1200, 800)

        self.light_process = QProcess()
        self.camera_controller = CameraController()

        if sys.platform == "win32":
            import winreg
            def get_pictures_folder():
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                    return winreg.QueryValueEx(key, "My Pictures")[0]
            def get_videos_folder():
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                    return winreg.QueryValueEx(key, "My Video")[0]

            file_path = get_pictures_folder()+os.sep+"HKVS"+os.sep
            video_path = get_videos_folder() +os.sep+"HKVS"+os.sep

        else:
            file_path = os.path.expanduser("~/Pictures")+os.sep+"HKVS"+os.sep
            video_path = os.path.expanduser("~/Videos") +os.sep+"HKVS"+os.sep

        self.file_path = file_path
        self.video_file_path = video_path
        self.recording = False
        self.init_ui()
        self.init_connect()


    def closeEvent(self, event):
        if hasattr(self, "camera_controller"):
            del self.camera_controller  # 删除引用
        event.accept()

    def init_ui(self):
        # 创建主分割器
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ========== 左侧区域 ==========
        self.left_card = QWidget(self)
        left_layout = QVBoxLayout(self.left_card)
        self.device_combo = ComboBox()
        left_layout.addWidget(self.device_combo)
        self.video_label = QWidget(self)
        video_layout =  QVBoxLayout(self.video_label)
        video_splitter = QSplitter(Qt.Vertical)
        self.video_label_item = QWidget(self)
        video_layout_item = QHBoxLayout(self.video_label_item)
        self.video_label=ScaledLabel(self.left_card)
        # self.video_label.setScaledContents(True)
        self.video_label_0 = ScaledLabel(self.video_label_item)
        # self.video_label_0.setScaledContents(True)
        self.video_label_1 = ScaledLabel(self.video_label_item)
        # self.video_label_1.setScaledContents(True)
        self.video_label_2 = ScaledLabel(self.video_label_item)
        # self.video_label_2.setScaledContents(True)
        self.video_label_3 = ScaledLabel(self.video_label_item)
        # self.video_label_3.setScaledContents(True)
        
        video_layout_item.addWidget(self.video_label_0)
        video_layout_item.addWidget(self.video_label_1)
        video_layout_item.addWidget(self.video_label_2)
        video_layout_item.addWidget(self.video_label_3)


        video_layout.addWidget(self.video_label)
        # video_layout.addLayout(video_layout_item)
        
        video_splitter.addWidget(self.video_label)
        video_splitter.addWidget(self.video_label_item)
        video_splitter.setStretchFactor(850, 250)
        video_splitter.setSizes([850, 250])

        # # 让每一行、每一列的大小都能自动调整
        # for i in range(2):  # 两行
        #     video_layout.setRowStretch(i, 1)
        # for j in range(3):  # 三列
        #     video_layout.setColumnStretch(j, 1)
        # video_layout.setSpacing(5)
        

        
        left_layout.addWidget(video_splitter)
        splitter.addWidget(self.left_card)

        # ========== 右侧区域 ==========
        self.right_panel = QWidget(self)
        right_layout = QVBoxLayout(self.right_panel)
        splitter.addWidget(self.right_panel)

        # 初始化控制卡
        self.control_card = HeaderCardWidget()
        self.control_card.setTitle("设备初始化")
        right_layout.addWidget(self.control_card)
        control_vlayout = QVBoxLayout()

        self.find_btn = PrimaryPushButton("查找设备")
        control_hlayout=QHBoxLayout()
        self.open_btn = PushButton("打开设备")
        self.close_btn = PushButton("关闭设备")
        self.light_btn = PushButton("灯光设置")
        self.detec_btn = PrimaryPushButton("开始检测")
        control_vlayout.addWidget(self.find_btn)
        control_hlayout.addWidget(self.open_btn)
        control_hlayout.addWidget(self.close_btn)
        control_vlayout.addLayout(control_hlayout)
        control_vlayout.addWidget(self.light_btn)
        control_vlayout.addWidget(self.detec_btn)


        self.control_card.viewLayout.addLayout(control_vlayout)

        # 采集控制卡
        self.acquire_card = HeaderCardWidget()
        self.acquire_card.setTitle("采集设置")
        right_layout.addWidget(self.acquire_card)
        # acquire_layout = QVBoxLayout()

        # 模式选择
        # mode_group = QHBoxLayout()
        # self.mode_button_group = QButtonGroup(self.acquire_card)
        # self.continuous_radio = RadioButton("连续模式")
        # self.trigger_radio = RadioButton("触发模式")
        # self.mode_button_group.addButton(self.continuous_radio)
        # self.mode_button_group.addButton(self.trigger_radio)
        # mode_group.addWidget(self.continuous_radio)
        # mode_group.addWidget(self.trigger_radio)
        # acquire_layout.addLayout(mode_group)

        # 采集按钮
        btn_hlayout = QHBoxLayout()
        file_hlayout = QHBoxLayout()
        video_file_hlayout = QHBoxLayout()
        btn_vlayout = QVBoxLayout()
        self.start_btn = PrimaryPushButton("开始采集")
        self.stop_btn = PushButton("停止采集")
        # self.soft_trigger_btn = PushButton("软触发一次")
        self.save_btn = PushButton("保存图像")
        self.recording_btn = PushButton("录制视频")
        self.file_path_label = StrongBodyLabel(str(self.file_path))
        self.file_path_btn = PrimaryToolButton(FIF.FOLDER)

        self.video_file_path_label = StrongBodyLabel(str(self.video_file_path))
        self.video_file_path_btn = PrimaryToolButton(FIF.FOLDER)

        btn_hlayout.addWidget(self.start_btn)
        btn_hlayout.addWidget(self.stop_btn)
        file_hlayout.addWidget(self.file_path_label)
        file_hlayout.addWidget(self.file_path_btn)
        video_file_hlayout.addWidget(self.video_file_path_label)
        video_file_hlayout.addWidget(self.video_file_path_btn)
        btn_vlayout.addLayout(btn_hlayout)
        # btn_vlayout.addWidget(self.soft_trigger_btn)
        btn_vlayout.addLayout(file_hlayout)
        btn_vlayout.addWidget(self.save_btn)
        btn_vlayout.addLayout(video_file_hlayout)
        btn_vlayout.addWidget(self.recording_btn)
        # acquire_layout.addLayout(btn_vlayout)
        self.acquire_card.viewLayout.addLayout(btn_vlayout)

        # 参数设置卡
        self.param_card = HeaderCardWidget()
        self.param_card.setTitle("参数设置")
        right_layout.addWidget(self.param_card)
        param_layout = QFormLayout()

        # 参数输入
        self.exposure_spin = DoubleSpinBox()
        self.exposure_spin.setRange(15, 9999611)
        self.exposure_spin.setDecimals(2)
        param_layout.addRow(BodyLabel("曝光："), self.exposure_spin)

        self.gain_spin = DoubleSpinBox()
        self.gain_spin.setDecimals(4)
        self.gain_spin.setRange(0, 17.0166)
        param_layout.addRow(BodyLabel("增益："), self.gain_spin)

        self.framerate_spin = DoubleSpinBox()
        self.framerate_spin.setRange(0.1, 100000)
        self.framerate_spin.setDecimals(2)
        param_layout.addRow(BodyLabel("帧率："), self.framerate_spin)

        self.result_framerate_spin = DoubleSpinBox()
        self.result_framerate_spin.setRange(0.1, 100000)
        self.result_framerate_spin.setDecimals(2)
        param_layout.addRow(BodyLabel("实际帧率："), self.result_framerate_spin)
        self.result_framerate_spin.setReadOnly(True)

        # 参数按钮
        param_btn_layout = QHBoxLayout()
        self.get_param_btn = PushButton("获取参数")
        self.set_param_btn = PrimaryPushButton("设置参数")
        param_btn_layout.addWidget(self.get_param_btn)
        param_btn_layout.addWidget(self.set_param_btn)
        param_layout.addRow(param_btn_layout)
        self.param_card.viewLayout.addLayout(param_layout)


        # 设置分割器比例
        splitter.setSizes([800, 200])


    def init_connect(self):
        ##灯光控制
        self.light_process.finished.connect(self.on_light_process_finished)
        self.light_btn.clicked.connect(self.on_light_btn_clicked)
        ##其他组件
        self.find_btn.clicked.connect(self.on_find_devices)
        self.open_btn.clicked.connect(self.on_open_device)
        self.close_btn.clicked.connect(self.on_close_device)
        self.start_btn.clicked.connect(self.on_start_acquire)
        self.stop_btn.clicked.connect(self.on_stop_acquire)
        # self.soft_trigger_btn.clicked.connect(self.on_soft_trigger)
        self.save_btn.clicked.connect(self.on_save_image)
        self.recording_btn.clicked.connect(self.on_recording)
        self.get_param_btn.clicked.connect(self.on_get_parameter)
        self.set_param_btn.clicked.connect(self.on_set_parameter)
        self.device_combo.currentIndexChanged.connect(self.on_device_selected)

        self.detec_btn.clicked.connect(self.on_detect_btn_clicked)

        self.file_path_btn.clicked.connect(self.on_file_path_btn_clicked)
        self.video_file_path_btn.clicked.connect(self.on_video_file_path_btn_clicked)

        ##消息提示
        self.camera_controller.message_signal.connect(self.showDialog)
        self.camera_controller.pixmap_ready_signal.connect(self.show_image)
        self.camera_controller.open_device_success_signal.connect(self.open_device_success)

    def on_device_selected(self, index):
        # 更新选择的设备索引
        self.camera_controller.nSelCamIndex = index
    def on_find_devices(self):
        dev_list = self.camera_controller.enum_devices()
        
        self.device_combo.clear()
        for dev in dev_list:
            print(dev)
            self.device_combo.addItem(dev)

    def on_open_device(self):
        self.camera_controller.open_device()

    def open_device_success(self):
        self.on_get_parameter()

    def on_close_device(self):
        self.camera_controller.close_device()

    def on_start_acquire(self):
        print("当前线程 ID:", threading.get_native_id())
        # 开始采集图像，显示到 video_label 上
        self.camera_controller.start_grabbing()

    def show_image(self,image,image0,image1,image2,image3):
        self.video_label.set_pixmap(image)
        self.video_label_0.set_pixmap(image0)
        self.video_label_1.set_pixmap(image1)
        self.video_label_2.set_pixmap(image2)
        self.video_label_3.set_pixmap(image3)

    def on_stop_acquire(self):
        self.camera_controller.stop_grabbing()

    def on_soft_trigger(self):
        self.camera_controller.trigger_once()

    def on_save_image(self):
        # 调用保存图像功能，此处示例采用 BMP 保存
        self.camera_controller.bmp_save(self.file_path)

    def on_recording(self):
        if self.recording == False:
            if self.camera_controller.start_recording(self.video_file_path):
                self.recording = True
                self.recording_btn.setText("停止录制")
        else:
            if self.camera_controller.stop_recording():
                self.recording = False
                self.recording_btn.setText("开始录制")

    def on_get_parameter(self):
        params = self.camera_controller.get_parameter()
        if params:
            frame_rate, result_frame_rate,exposure_time, gain = params
            self.framerate_spin.setValue(frame_rate)
            self.exposure_spin.setValue(exposure_time)
            self.gain_spin.setValue(gain)
            self.result_framerate_spin.setValue(result_frame_rate)
        

    def on_set_parameter(self):
        frame_rate = self.framerate_spin.value()
        exposure_time = self.exposure_spin.value()
        gain = self.gain_spin.value()
        self.camera_controller.set_parameter(frame_rate, exposure_time, gain)


    def on_detect_btn_clicked(self):
        if hasattr(self, "camera_controller") and self.camera_controller.b_is_run:
            self.detection_window = DetectionResultWidget()
            self.detection_window.detect_stop.connect(self.detect_close)
            self.detection_window.show()  # 非模态窗口
            self.camera_controller.start_detect()
            self.detec_btn.setText("检测中.......")
            self.detec_btn.setEnabled(False)
            
        else:
            self.showDialog("提示", "请先打开相机")

    def detect_close(self):
        self.camera_controller.stop_detect()
        self.detec_btn.setText("开始检测")
        self.detec_btn.setEnabled(True)

    def on_light_btn_clicked(self):
        # os.system("F:\\216\\水下高亮度LED光源-7-1\\150WLightControlSystem.exe")
        # exe_path = r"F:\\216\\水下高亮度LED光源-7-1\\150WLightControlSystem.exe"  # 替换为你的 EXE 路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        exe_path = os.path.join(current_dir, "src\\light\\150WLightControlSystem.exe")
        print(exe_path)
        self.light_process.start(exe_path)  # 启动 EXE
        self.light_btn.setText("运行中...")
        self.light_btn.setEnabled(False)

    def on_light_process_finished(self):
        self.light_btn.setText("灯光设置")
        self.light_btn.setEnabled(True)


    def showDialog(self,title,content):
        # w = MessageDialog(title, content, self)   # Win10 style message box
        w = MessageBox(title, content, self)
        # close the message box when mask is clicked
        w.setClosableOnMaskClicked(True)
        w.cancelButton.hide()
        w.buttonLayout.insertStretch(1)
        w.exec()

    def on_file_path_btn_clicked(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Choose folder"), self.file_path)

        if not path :
            return
        
        self.file_path = path+"/"
        self.file_path_label.setText(self.file_path)
            
    def on_video_file_path_btn_clicked(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Choose folder"), self.video_file_path)
        if not path :
            return
        
        self.video_file_path = path+"/"
        self.video_file_path_label.setText(self.video_file_path)



if __name__ == "__main__":
    app = QApplication([])
    logo_path = os.path.join(load_basepath(),"resources","logo.jpg")
    app.setWindowIcon(QIcon(logo_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
