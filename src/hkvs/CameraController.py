# This Python file uses the following encoding: utf-8
import sys
import os
from ctypes import POINTER, cast
from PySide6.QtCore import QObject, Signal

from src.utils.utils import *
# 导入 MVS SDK 的相关模块（确保路径正确）
from .MvImport.MvCameraControl_class import *
from .CamOperation_class import *

class CameraController(QObject):
    message_signal = Signal(str,str)
    pixmap_ready_signal = Signal(object,object,object,object,object)
    open_device_success_signal = Signal()
    def __init__(self):
        super().__init__()
        self.initialized =False
        # 初始化设备相关变量
        self.deviceList = MV_CC_DEVICE_INFO_LIST()
        self.tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
        self.cam = MvCamera()
        self.nSelCamIndex = 0
        self.obj_cam_operation = None
        self.b_is_run = False
        self.h_thread_handle = None
        self.initialized = True


    def __del__(self):
        try:
            if self.obj_cam_operation:
                self.obj_cam_operation.Close_device()
        except Exception as e:
            print(f"销毁时发生错误: {str(e)}")

    def enum_devices(self):
        """
        枚举设备，返回设备描述字符串列表
        """
        self.deviceList = MV_CC_DEVICE_INFO_LIST()
        ret = MvCamera.MV_CC_EnumDevices(self.tlayerType, self.deviceList)
        if ret != 0:
            print("enum devices fail! ret =", ToHexStr(ret))
            self.message_signal.emit("Error",f"枚举设备失败！ret={ToHexStr(ret)}")
            return []
        if self.deviceList.nDeviceNum == 0:
            print("find no device!")
            self.message_signal.emit("Error","未发现设备！")
            return []
        devList = []
        for i in range(self.deviceList.nDeviceNum):
            mvcc_dev_info = cast(self.deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                chUserDefinedName = ""
                for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chUserDefinedName:
                    if 0 == per:
                        break
                    chUserDefinedName = chUserDefinedName + chr(per)
                print ("device model name: %s" % chUserDefinedName)

                nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
                nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
                nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
                nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
                print ("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))
                devList.append("["+str(i)+"]GigE: "+ chUserDefinedName +"("+ str(nip1)+"."+str(nip2)+"."+str(nip3)+"."+str(nip4) +")")
                
            elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                chUserDefinedName = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chUserDefinedName:
                    if per == 0:
                        break
                    chUserDefinedName += chr(per)
                print ("device model name: %s" % chUserDefinedName)
                strSerialNumber = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber:
                    if per == 0:
                        break
                    strSerialNumber = strSerialNumber + chr(per)
                print ("user serial number: %s" % strSerialNumber)
                devList.append("["+str(i)+"]USB: "+ chUserDefinedName +"(" + str(strSerialNumber) + ")")
        return devList


    def init_cam_connect(self):
        self.obj_cam_operation.message_signal.connect(self.message_signal.emit)
        self.obj_cam_operation.pixmap_ready_signal.connect(self.pixmap_ready_signal.emit)

        
    def open_device(self):
        """
        根据当前选择的设备索引打开设备
        """
        if self.b_is_run:
            print("Camera is Running!")
            self.message_signal.emit("Error","设备正在运行！")
            return
        self.obj_cam_operation = CameraOperation(self.cam, self.deviceList, self.nSelCamIndex)
        self.init_cam_connect()
        ret = self.obj_cam_operation.Open_device()
        if ret != 0:
            self.b_is_run = False
            print("Open device failed! ret =", ToHexStr(ret))
            self.message_signal.emit("Error",f"打开设备失败！ret={ToHexStr(ret)}")
        else:
            self.b_is_run = True
            print("Open device successfully!")
            self.open_device_success_signal.emit()
            self.message_signal.emit("Success","打开设备成功！")

    def close_device(self):
        if self.obj_cam_operation:
            self.obj_cam_operation.Close_device()
        self.b_is_run = False
        print("Device closed.")
        self.message_signal.emit("Success","设备已关闭！")

    def start_grabbing(self):
        """
        开始采集图像，并在 display_widget 中显示（display_widget 建议为 QLabel）
        """
        if self.obj_cam_operation:
            # 注意：原代码中 Start_grabbing 接受 Tkinter 的 window 与 panel，
            # 此处需要 CameraOperation 内部适配 Qt 显示方式，或者自行修改实现。
            self.obj_cam_operation.Start_grabbing()
            print("Start grabbing.")
        else:
            print("Device not opened!")
            self.message_signal.emit("Error","设备未打开！")

    def stop_grabbing(self):
        if self.obj_cam_operation:
            self.obj_cam_operation.Stop_grabbing()
            print("Stop grabbing.")

    def trigger_once(self, command=1):
        if self.obj_cam_operation:
            self.obj_cam_operation.Trigger_once(command)
            print("Trigger once.")

    def bmp_save(self,file_path):
        if self.obj_cam_operation:
            self.obj_cam_operation.b_save_bmp = True
            self.obj_cam_operation.file_path = file_path
            print("Save BMP flag set.")

    def jpg_save(self,file_path):
        if self.obj_cam_operation:
            self.obj_cam_operation.b_save_jpg = True
            self.obj_cam_operation.file_path = file_path
            print("Save JPG flag set.")

    def get_parameter(self):
        if self.obj_cam_operation and self.b_is_run:
            self.obj_cam_operation.Get_parameter()
            # 返回帧率、曝光、增益参数（假设为数字或字符串）
            return (self.obj_cam_operation.frame_rate,
                    self.obj_cam_operation.result_frame_rate,
                    self.obj_cam_operation.exposure_time,
                    self.obj_cam_operation.gain)
        else:
            self.message_signal.emit("Error","设备未打开或未运行！")
        return None

    def set_parameter(self, frame_rate, exposure_time, gain):
        if self.obj_cam_operation:
            self.obj_cam_operation.Set_parameter(frame_rate, exposure_time, gain)
            print("Set parameter:", frame_rate, exposure_time, gain)


    def start_recording(self, file_path):
        print(file_path)
        if self.obj_cam_operation:
            self.obj_cam_operation.b_recording = True
            self.obj_cam_operation.video_path = file_path
            return self.obj_cam_operation.Start_recording()
        else:
            self.message_signal.emit("Error","设备未打开！")
            return False

    def stop_recording(self):
        if self.obj_cam_operation:
            self.obj_cam_operation.b_recording = False
            return self.obj_cam_operation.Stop_recording()
        else:
            self.message_signal.emit("Error","设备未打开！")
            return False

    def start_detect(self):
        if self.obj_cam_operation:
            self.obj_cam_operation.detect = True
    
    def stop_detect(self):
        if self.obj_cam_operation:
            self.obj_cam_operation.detect = False
