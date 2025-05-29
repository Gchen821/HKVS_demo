# -- coding: utf-8 --
import sys
import threading
import msvcrt
# import _tkinter
# import tkinter.messagebox
# from tkinter import * 
# from tkinter.messagebox import *
# import tkinter as tk
import numpy as np
import cv2
import time
import sys, os
import datetime
import inspect
import ctypes
import random
from PIL import Image,ImageTk
from ctypes import *
# from tkinter import ttk
from PySide6.QtCore import QObject, Signal

from .MvImport.MvCameraControl_class import *
from src.utils.utils import *
from src.utils.globalclass  import DetectionQueue

def Async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def Stop_thread(thread):
    Async_raise(thread.ident, SystemExit)

class CameraOperation(QObject):
    message_signal=Signal(str,str)
    pixmap_ready_signal = Signal(object,object,object,object,object)
    def __init__(self,obj_cam,st_device_list,n_connect_num=0,b_open_device=False,b_start_grabbing = False,h_thread_handle=None,\
                b_thread_closed=False,st_frame_info=None,b_exit=False,b_save_bmp=False,b_save_jpg=False,buf_save_image=None,\
                n_save_image_size=0,frame_rate=0,result_frame_rate=0,exposure_time=0,gain=0,file_path="",b_recording=False,video_path="",detect=False):
        super().__init__()
        self.obj_cam = obj_cam
        self.st_device_list = st_device_list
        self.n_connect_num = n_connect_num
        self.b_open_device = b_open_device
        self.b_start_grabbing = b_start_grabbing 
        self.b_thread_closed = b_thread_closed
        self.st_frame_info = st_frame_info
        self.b_exit = b_exit
        self.b_save_bmp = b_save_bmp
        self.b_save_jpg = b_save_jpg
        self.b_recording = b_recording
        self.buf_save_image = buf_save_image
        self.h_thread_handle = h_thread_handle
        # self.n_win_gui_id = n_win_gui_id
        self.n_save_image_size = n_save_image_size
        self.b_thread_closed
        self.frame_rate = frame_rate
        self.result_frame_rate = result_frame_rate
        self.exposure_time = exposure_time
        self.gain = gain
        self.file_path = file_path
        self.video_path = video_path
        self.stRecordPar = None
        self.detect = detect
        self.queue = DetectionQueue()

    def To_hex_str(self,num):
        chaDic = {10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f'}
        hexStr = ""
        if num < 0:
            num = num + 2**32
        while num >= 16:
            digit = num % 16
            hexStr = chaDic.get(digit, str(digit)) + hexStr
            num //= 16
        hexStr = chaDic.get(num, str(num)) + hexStr   
        return hexStr

    def Open_device(self):
        print("当前线程 ID:", threading.get_native_id())
        if False == self.b_open_device:
            # ch:选择设备并创建句柄 | en:Select device and create handle
            nConnectionNum = int(self.n_connect_num)
            stDeviceList = cast(self.st_device_list.pDeviceInfo[int(nConnectionNum)], POINTER(MV_CC_DEVICE_INFO)).contents
            self.obj_cam = MvCamera()
            ret = self.obj_cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                self.obj_cam.MV_CC_DestroyHandle()
                self.message_signal.emit("error","create handle fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','create handle fail! ret = '+ self.To_hex_str(ret))
                return ret

            ret = self.obj_cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                # self.message_signal.emit("error","open device fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','open device fail! ret = '+ self.To_hex_str(ret))
                return ret
            print ("open device successfully!")
            self.b_open_device = True
            self.b_thread_closed = False

            # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
            if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
                nPacketSize = self.obj_cam.MV_CC_GetOptimalPacketSize()
                if int(nPacketSize) > 0:
                    ret = self.obj_cam.MV_CC_SetIntValue("GevSCPSPacketSize",nPacketSize)
                    if ret != 0:
                        print ("warning: set packet size fail! ret[0x%x]" % ret)
                else:
                    print ("warning: set packet size fail! ret[0x%x]" % nPacketSize)

            stBool = c_bool(False)
            ret =self.obj_cam.MV_CC_GetBoolValue("AcquisitionFrameRateEnable", stBool)
            if ret != 0:
                print ("get acquisition frame rate enable fail! ret[0x%x]" % ret)

            # ch:设置触发模式为off | en:Set trigger mode as off
            ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
            if ret != 0:
                print ("set trigger mode fail! ret[0x%x]" % ret)
            # self.get_record_param()
            
            return 0

    def get_record_param(self):
        stParam =  MVCC_INTVALUE()
        memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))
        if self.stRecordPar == None:
            self.stRecordPar = MV_CC_RECORD_PARAM()
        memset(byref(self.stRecordPar), 0, sizeof(MV_CC_RECORD_PARAM))
        # ch:获取图像高度 | en:Get the width of the image
        ret = self.obj_cam.MV_CC_GetIntValue("Width", stParam)
        if ret != 0: 
            print ("get width fail! nRet [0x%x]" % ret)
        self.stRecordPar.nWidth = stParam.nCurValue

        # ch:获取图像高度 | en:Get the height of the image
        ret = self.obj_cam.MV_CC_GetIntValue("Height", stParam)
        if ret != 0: 
            print ("get height fail! nRet [0x%x]"% ret)
        self.stRecordPar.nHeight = stParam.nCurValue

        # ch:获取图像像素 | en:Get the pixelFormat of the image
        stEnumValue = MVCC_ENUMVALUE()
        memset(byref(stEnumValue), 0 ,sizeof(MVCC_ENUMVALUE))
        ret = self.obj_cam.MV_CC_GetEnumValue("PixelFormat", stEnumValue)
        if ret != 0: 
            print ("get PixelFormat fail! nRet [0x%x]" % ret)
            sys.exit()
        self.stRecordPar.enPixelType = MvGvspPixelType(stEnumValue.nCurValue)

        # ch:获取图像帧率 | en:Get the resultingFrameRate of the image
        stFloatValue = MVCC_FLOATVALUE()
        memset(byref(stFloatValue), 0 ,sizeof(MVCC_FLOATVALUE))
        ret = self.obj_cam.MV_CC_GetFloatValue("ResultingFrameRate", stFloatValue)
        if ret != 0: 
            print ("get ResultingFrameRate value fail! nRet [0x%x]" % ret)
            sys.exit()
        self.stRecordPar.fFrameRate = stFloatValue.fCurValue

        # ch:录像结构体赋值 | en:Video structure assignment
        self.stRecordPar.nBitRate = 1000
        self.stRecordPar.enRecordFmtType = MV_FormatType_AVI
        
    def Start_grabbing(self):
        if False == self.b_start_grabbing and True == self.b_open_device:
            self.b_exit = False
            ret = self.obj_cam.MV_CC_StartGrabbing()
            if ret != 0:
                self.message_signal.emit("error","start grabbing fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','start grabbing fail! ret = '+ self.To_hex_str(ret))
                return
            self.b_start_grabbing = True
            print ("start grabbing successfully!")
            try:
                # self.n_win_gui_id = random.randint(1,10000)
                self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread, args=(self,))
                self.h_thread_handle.start()
                self.b_thread_closed = True
            except:
                self.message_signal.emit("error","error: unable to start thread")
                # tkinter.messagebox.showerror('show error','error: unable to start thread')
                False == self.b_start_grabbing

    def Stop_grabbing(self):
        if True == self.b_start_grabbing and self.b_open_device == True:
            #退出线程
            if True == self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_StopGrabbing()
            if ret != 0:
                self.message_signal.emit("error","stop grabbing fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','stop grabbing fail! ret = '+self.To_hex_str(ret))
                return
            print ("stop grabbing successfully!")
            self.b_start_grabbing = False
            self.b_exit  = True      

    def Close_device(self):
        if True == self.b_open_device:
            #退出线程
            if True == self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_CloseDevice()
            if ret != 0:
                self.message_signal.emit("error","close deivce fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','close deivce fail! ret = '+self.To_hex_str(ret))
                return
                
        # ch:销毁句柄 | Destroy handle
        self.obj_cam.MV_CC_DestroyHandle()
        self.b_open_device = False
        self.b_start_grabbing = False
        self.b_exit  = True
        print ("close device successfully!")

    def Set_trigger_mode(self,strMode):
        if True == self.b_open_device:
            if "continuous" == strMode: 
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode",0)
                if ret != 0:
                    self.message_signal.emit("error","set triggermode fail! ret = "+self.To_hex_str(ret))
                    # tkinter.messagebox.showerror('show error','set triggermode fail! ret = '+self.To_hex_str(ret))
            if "triggermode" == strMode:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode",1)
                if ret != 0:
                    self.message_signal.emit("error","set triggermode fail! ret = "+self.To_hex_str(ret))
                    # tkinter.messagebox.showerror('show error','set triggermode fail! ret = '+self.To_hex_str(ret))
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerSource",7)
                if ret != 0:
                    self.message_signal.emit("error","set triggersource fail! ret = "+self.To_hex_str(ret))
                    # tkinter.messagebox.showerror('show error','set triggersource fail! ret = '+self.To_hex_str(ret))

    def Trigger_once(self,nCommand):
        if True == self.b_open_device:
            if 1 == nCommand: 
                ret = self.obj_cam.MV_CC_SetCommandValue("TriggerSoftware")
                if ret != 0:
                    self.message_signal.emit("error","set triggersoftware fail! ret = "+self.To_hex_str(ret))
                    # tkinter.messagebox.showerror('show error','set triggersoftware fail! ret = '+self.To_hex_str(ret))

    def Get_parameter(self):
        if True == self.b_open_device:
            stFloatParam_FrameRate =  MVCC_FLOATVALUE()
            memset(byref(stFloatParam_FrameRate), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_ResultFrameRate =  MVCC_FLOATVALUE()
            memset(byref(stFloatParam_ResultFrameRate), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_exposureTime = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_exposureTime), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_gain = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_gain), 0, sizeof(MVCC_FLOATVALUE))
            ret = self.obj_cam.MV_CC_GetFloatValue("AcquisitionFrameRate", stFloatParam_FrameRate)
            if ret != 0:
                self.message_signal.emit("error","get acquistion frame rate fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','get acquistion frame rate fail! ret = '+self.To_hex_str(ret))
            self.frame_rate = stFloatParam_FrameRate.fCurValue
            ret = self.obj_cam.MV_CC_GetFloatValue("ResultingFrameRate", stFloatParam_ResultFrameRate)
            if ret != 0:
                self.message_signal.emit("error","get ResultingFrameRate  rate fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','get acquistion frame rate fail! ret = '+self.To_hex_str(ret))
            self.result_frame_rate = stFloatParam_ResultFrameRate.fCurValue
            
            ret = self.obj_cam.MV_CC_GetFloatValue("ExposureTime", stFloatParam_exposureTime)
            if ret != 0:
                self.message_signal.emit("error","get exposure time fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','get exposure time fail! ret = '+self.To_hex_str(ret))
            self.exposure_time = stFloatParam_exposureTime.fCurValue
            ret = self.obj_cam.MV_CC_GetFloatValue("Gain", stFloatParam_gain)
            if ret != 0:
                self.message_signal.emit("error","get gain fail! ret = "+self.To_hex_str(ret))
                # tkinter.messagebox.showerror('show error','get gain fail! ret = '+self.To_hex_str(ret))
            self.gain = stFloatParam_gain.fCurValue
            # self.message_signal.emit("info","Get parameter successfully!")
            # tkinter.messagebox.showinfo('show info','get parameter success!')
        else:
            self.message_signal.emit("error","device not open!")

    def Set_parameter(self,frameRate,exposureTime,gain):
        issuccess = True   
        if '' == frameRate or '' == exposureTime or '' == gain:
            self.message_signal.emit("error","please type in the text box !")
            # tkinter.messagebox.showinfo('show info','please type in the text box !')
            return
        if True == self.b_open_device:
            ret = self.obj_cam.MV_CC_SetFloatValue("ExposureTime",float(exposureTime))
            if ret != 0:
                self.message_signal.emit("error","set exposure time fail! ret = "+self.To_hex_str(ret))
                issuccess=False
                # tkinter.messagebox.showerror('show error','set exposure time fail! ret = '+self.To_hex_str(ret))

            ret = self.obj_cam.MV_CC_SetFloatValue("Gain",float(gain))
            if ret != 0:
                self.message_signal.emit("error","set gain fail! ret = "+self.To_hex_str(ret))
                issuccess=False
                # tkinter.messagebox.showerror('show error','set gain fail! ret = '+self.To_hex_str(ret))

            ret = self.obj_cam.MV_CC_SetFloatValue("AcquisitionFrameRate",float(frameRate))
            if ret != 0:
                self.message_signal.emit("error","set acquistion frame rate fail! ret = "+self.To_hex_str(ret))
                issuccess=False
                # tkinter.messagebox.showerror('show error','set acquistion frame rate fail! ret = '+self.To_hex_str(ret))
            if issuccess :
                self.message_signal.emit("info","Set parameter successfully!")
            # tkinter.messagebox.showinfo('show info','set parameter success!')

    def Work_thread(self):
        print("当前线程 ID:", threading.get_native_id())
        stOutFrame = MV_FRAME_OUT()  
        img_buff = None
        buf_cache = None
        buf_cache_0 = None
        buf_cache_1 = None
        buf_cache_2 = None
        buf_cache_3 = None

        buf_cache_dir_0 = None
        buf_cache_dir_1 = None
        buf_cache_dir_2 = None
        buf_cache_dir_3 = None
        numArray = None


        stInputFrameInfo = MV_CC_INPUT_FRAME_INFO()
        memset(byref(stInputFrameInfo), 0 ,sizeof(MV_CC_INPUT_FRAME_INFO))
        while True:
            ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 1000)

            if 0 == ret:
                if None == buf_cache and None == buf_cache_0 and None == buf_cache_1 and None == buf_cache_2 and None == buf_cache_3:
                    buf_cache = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                    buf_cache_0 = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                    buf_cache_1 = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                    buf_cache_2 = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                    buf_cache_3 = (c_ubyte * (stOutFrame.stFrameInfo.nFrameLen*3))()
                #获取到图像的时间开始节点获取到图像的时间开始节点
                self.st_frame_info = stOutFrame.stFrameInfo
                cdll.msvcrt.memcpy(byref(buf_cache), stOutFrame.pBufAddr, self.st_frame_info.nFrameLen)
                print ("get one frame: Width[%d], Height[%d], nFrameNum[%d]"  % (self.st_frame_info.nWidth, self.st_frame_info.nHeight, self.st_frame_info.nFrameNum))
                if self.b_recording :
                    stInputFrameInfo.pData = cast(stOutFrame.pBufAddr, POINTER(c_ubyte))
                    stInputFrameInfo.nDataLen = stOutFrame.stFrameInfo.nFrameLen
                    # ch:输入一帧数据到录像接口 | en:Input a frame of data to the video interface
                    ret_record = self.obj_cam.MV_CC_InputOneFrame(stInputFrameInfo)
                    if ret_record != 0:
                        self.message_signal.emit("error","input one frame fail! nRet [0x%x]" % ret)
                        self.b_recording = False


                nRet = self.obj_cam.MV_CC_Image2Polarizer(buf_cache,self.st_frame_info.nWidth, self.st_frame_info.nHeight,buf_cache_0,buf_cache_1,buf_cache_2,buf_cache_3,5)
                
                
                self.n_save_image_size = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3 + 2048
                if img_buff is None:
                    img_buff = (c_ubyte * self.n_save_image_size)()
                if True == self.b_save_jpg:
                    self.Save_jpg(buf_cache) #ch:保存Jpg图片 | en:Save Jpg
                if True == self.b_save_bmp:
                    try:
                        self.Save_Bmp(buf_cache,nWidth=self.st_frame_info.nWidth,nHeight=self.st_frame_info.nHeight,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen,frame_name="") #ch:保存Bmp图片 | en:Save Bmp
                        self.Save_Bmp(buf_cache_0,nWidth=self.st_frame_info.nWidth,nHeight=self.st_frame_info.nHeight,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen,frame_name="_FourDirection")
                        self.Save_Bmp(buf_cache_1,nWidth=self.st_frame_info.nWidth,nHeight=self.st_frame_info.nHeight,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen,frame_name="_Non")
                        self.Save_Bmp(buf_cache_2,nWidth=self.st_frame_info.nWidth,nHeight=self.st_frame_info.nHeight,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen,frame_name="_Degree")
                        self.Save_Bmp(buf_cache_3,nWidth=self.st_frame_info.nWidth,nHeight=self.st_frame_info.nHeight,enPixelType=PixelType_Gvsp_RGB8_Packed,nFrameLen=int(self.st_frame_info.nFrameLen)*3,frame_name="_ColorAngle")
                        if None == buf_cache_dir_0 and None == buf_cache_dir_1 and None == buf_cache_dir_2 and None == buf_cache_dir_3:
                            buf_cache_dir_0 = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                            buf_cache_dir_1 = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                            buf_cache_dir_2 = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                            buf_cache_dir_3 = (c_ubyte * (stOutFrame.stFrameInfo.nFrameLen*3))()
                        
                        nRet_save =self.Image2Polarizer(buf_cache,self.st_frame_info.nWidth, self.st_frame_info.nHeight,buf_cache_dir_0,buf_cache_dir_1,buf_cache_dir_2,buf_cache_dir_3)
                        if nRet_save == 0:
                            self.Save_Bmp(buf_cache_dir_0,nWidth=self.st_frame_info.nWidth/2,nHeight=self.st_frame_info.nHeight/2,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen/4,frame_name="_FourDirection_dir90")
                            self.Save_Bmp(buf_cache_dir_1,nWidth=self.st_frame_info.nWidth/2,nHeight=self.st_frame_info.nHeight/2,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen/4,frame_name="_FourDirection_dir45")
                            self.Save_Bmp(buf_cache_dir_2,nWidth=self.st_frame_info.nWidth/2,nHeight=self.st_frame_info.nHeight/2,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen/4,frame_name="_FourDirection_dir135")
                            self.Save_Bmp(buf_cache_dir_3,nWidth=self.st_frame_info.nWidth/2,nHeight=self.st_frame_info.nHeight/2,enPixelType=self.st_frame_info.enPixelType,nFrameLen=self.st_frame_info.nFrameLen/4,frame_name="_FourDirection_dir0")
                    except Exception as e:
                        raise Exception("get one frame failed:%s" % e)
                    self.message_signal.emit("info","save bmp success!")

                    
            else:
                print("no data, ret = "+self.To_hex_str(ret))
                continue
            
            numArray,mode = self.convert_pixel(buf_cache=buf_cache,enPixelType=self.st_frame_info.enPixelType,img_buff=img_buff)
            numArray_0,mode0 = self.convert_pixel(buf_cache=buf_cache_0,enPixelType=self.st_frame_info.enPixelType,img_buff=img_buff)
            numArray_1,mode1 = self.convert_pixel(buf_cache=buf_cache_1,enPixelType=self.st_frame_info.enPixelType,img_buff=img_buff)
            numArray_2,mode2 = self.convert_pixel(buf_cache=buf_cache_2,enPixelType=self.st_frame_info.enPixelType,img_buff=img_buff)
            numArray_3,mode3 = self.convert_pixel(buf_cache=buf_cache_3,enPixelType=PixelType_Gvsp_RGB8_Packed,img_buff=img_buff)




            #合并OpenCV到Tkinter界面中
            current_image = Image.frombuffer(mode, (self.st_frame_info.nWidth,self.st_frame_info.nHeight), numArray.astype('uint8')).resize((800, 600), Image.Resampling.LANCZOS)
            current_image_0 = Image.frombuffer(mode0, (self.st_frame_info.nWidth,self.st_frame_info.nHeight), numArray_0.astype('uint8')).resize((800, 600), Image.Resampling.LANCZOS)
            current_image_1 = Image.frombuffer(mode1, (self.st_frame_info.nWidth,self.st_frame_info.nHeight), numArray_1.astype('uint8')).resize((800, 600), Image.Resampling.LANCZOS)
            current_image_2 = Image.frombuffer(mode2, (self.st_frame_info.nWidth,self.st_frame_info.nHeight), numArray_2.astype('uint8')).resize((800, 600), Image.Resampling.LANCZOS)
            current_image_3 = Image.frombuffer(mode3, (self.st_frame_info.nWidth,self.st_frame_info.nHeight), numArray_3.astype('uint8')).resize((800, 600), Image.Resampling.LANCZOS)  
            pixmap_0 = pil_to_pixmap(current_image_0)
            pixmap_1 = pil_to_pixmap(current_image_1)
            pixmap_2 = pil_to_pixmap(current_image_2)
            pixmap_3 = pil_to_pixmap(current_image_3)
            pixmap = pil_to_pixmap(current_image)
            if self.detect:
                np_array = np.array(current_image)
                self.queue.add_pending(np_array)
            self.pixmap_ready_signal.emit(pixmap,pixmap_0,pixmap_1,pixmap_2,pixmap_3)
            nRet = self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
            if self.b_exit == True:
                if img_buff is not None:
                    del img_buff
                if buf_cache is not None:
                    del buf_cache
                if buf_cache_0 is not None:
                    del buf_cache_0
                if buf_cache_1 is not None:
                    del buf_cache_1
                if buf_cache_2 is not None:
                    del buf_cache_2
                if buf_cache_3 is not None:
                    del buf_cache_3
                if buf_cache_dir_0 is not None:
                    del buf_cache_dir_0
                if buf_cache_dir_1 is not None:
                    del buf_cache_dir_1
                if buf_cache_dir_2 is not None:
                    del buf_cache_dir_2
                if buf_cache_dir_3 is not None:
                    del buf_cache_dir_3
                break

    def Image2Polarizer(self,ImageBuffer, width, height, pOutImage1, pOutImage2, pOutImage3, pOutImage4):
        """
        使用 ctypes 重写 Image2Polarizer 函数，将输入图像数据分解为四个偏振角度的图像数据。
        
        参数:
            ImageBuffer: ctypes 数组，输入的图像数据（1维，长度应>= width*height）
            width: 图像宽度
            height: 图像高度
            pOutImage1: ctypes 数组，用于存储偏振角 90° 对应的数据
            pOutImage2: ctypes 数组，用于存储偏振角 45° 对应的数据
            pOutImage3: ctypes 数组，用于存储偏振角 135° 对应的数据
            pOutImage4: ctypes 数组，用于存储偏振角 0° 对应的数据

        返回:
            0 成功，其他值表示错误（例如 MV_E_PARAMETER 表示输入指针为空）
        """
        if not ImageBuffer:
            return MV_E_PARAMETER

        k = 0
        # 遍历图像的每 2 行 2 列块
        for i in range(0, height, 2):
            for j in range(0, width, 2):
                pOutImage1[k] = ImageBuffer[i + j]             # 90° 偏振
                pOutImage2[k] = ImageBuffer[i + j + 1]           # 45° 偏振
                pOutImage3[k] = ImageBuffer[(i + 1) * width + j]   # 135° 偏振
                pOutImage4[k] = ImageBuffer[(i + 1) * width + j + 1] # 0° 偏振
                k += 1

        return 0
    def convert_pixel(self,buf_cache,enPixelType,img_buff):
            #转换像素结构体赋值
            stConvertParam = MV_CC_PIXEL_CONVERT_PARAM()
            memset(byref(stConvertParam), 0, sizeof(stConvertParam))
            stConvertParam.nWidth = self.st_frame_info.nWidth
            stConvertParam.nHeight = self.st_frame_info.nHeight
            stConvertParam.pSrcData = cast(buf_cache, POINTER(c_ubyte))
            stConvertParam.nSrcDataLen = self.st_frame_info.nFrameLen
            stConvertParam.enSrcPixelType = enPixelType 


            mode = None     # array转为Image图像的转换模式
            # RGB8直接显示
            if PixelType_Gvsp_RGB8_Packed == enPixelType :
                numArray = CameraOperation.Color_numpy(self,buf_cache,self.st_frame_info.nWidth,self.st_frame_info.nHeight)
                mode = "RGB"

            # Mono8直接显示
            elif PixelType_Gvsp_Mono8 == enPixelType :
                numArray = CameraOperation.Mono_numpy(self,buf_cache,self.st_frame_info.nWidth,self.st_frame_info.nHeight)
                
                mode = "L"

            # 如果是彩色且非RGB则转为RGB后显示
            elif self.Is_color_data(enPixelType):
                nConvertSize = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3
                stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
                stConvertParam.pDstBuffer = (c_ubyte * nConvertSize)()
                stConvertParam.nDstBufferSize = nConvertSize
                time_start=time.time()
                ret = self.obj_cam.MV_CC_ConvertPixelType(stConvertParam)
                time_end=time.time()
                print('MV_CC_ConvertPixelType to RGB:',time_end - time_start) 
                if ret != 0:
                    self.message_signal.emit("error","convert pixel fail! ret = "+self.To_hex_str(ret))
                    # tkinter.messagebox.showerror('show error','convert pixel fail! ret = '+self.To_hex_str(ret))
                    # continue
                cdll.msvcrt.memcpy(byref(img_buff), stConvertParam.pDstBuffer, nConvertSize)
                numArray = CameraOperation.Color_numpy(self,img_buff,self.st_frame_info.nWidth,self.st_frame_info.nHeight)
                mode = "RGB"
                
            # 如果是黑白且非Mono8则转为Mono8后显示
            elif self.Is_mono_data(enPixelType):
                nConvertSize = self.st_frame_info.nWidth * self.st_frame_info.nHeight
                stConvertParam.enDstPixelType = PixelType_Gvsp_Mono8
                stConvertParam.pDstBuffer = (c_ubyte * nConvertSize)()
                stConvertParam.nDstBufferSize = nConvertSize
                time_start=time.time()
                ret = self.obj_cam.MV_CC_ConvertPixelType(stConvertParam)
                time_end=time.time()
                print('MV_CC_ConvertPixelType to Mono8:',time_end - time_start) 
                if ret != 0:
                    self.message_signal.emit("error","convert pixel fail! ret = "+self.To_hex_str(ret))
                    # tkinter.messagebox.showerror('show error','convert pixel fail! ret = '+self.To_hex_str(ret))
                    # continue
                cdll.msvcrt.memcpy(byref(img_buff), stConvertParam.pDstBuffer, nConvertSize)
                numArray = CameraOperation.Mono_numpy(self,img_buff,self.st_frame_info.nWidth,self.st_frame_info.nHeight)
                mode = "L"

            
            return numArray,mode

            

    def Save_jpg(self,buf_cache):
        if(None == buf_cache):
            return
        self.buf_save_image = None
        file_path = self.file_path+str(self.st_frame_info.nFrameNum) + ".jpg"
        self.n_save_image_size = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3 + 2048
        if self.buf_save_image is None:
            self.buf_save_image = (c_ubyte * self.n_save_image_size)()

        stParam = MV_SAVE_IMAGE_PARAM_EX()
        stParam.enImageType = MV_Image_Jpeg;                                        # ch:需要保存的图像类型 | en:Image format to save
        stParam.enPixelType = self.st_frame_info.enPixelType                               # ch:相机对应的像素格式 | en:Camera pixel type
        stParam.nWidth      = self.st_frame_info.nWidth                                    # ch:相机对应的宽 | en:Width
        stParam.nHeight     = self.st_frame_info.nHeight                                   # ch:相机对应的高 | en:Height
        stParam.nDataLen    = self.st_frame_info.nFrameLen
        stParam.pData       = cast(buf_cache, POINTER(c_ubyte))
        stParam.pImageBuffer=  cast(byref(self.buf_save_image), POINTER(c_ubyte)) 
        stParam.nBufferSize = self.n_save_image_size                                 # ch:存储节点的大小 | en:Buffer node size
        stParam.nJpgQuality = 80;                                                    # ch:jpg编码，仅在保存Jpg图像时有效。保存BMP时SDK内忽略该参数
        return_code = self.obj_cam.MV_CC_SaveImageEx2(stParam)            

        if return_code != 0:
            self.message_signal.emit("Error","save jpg fail! ret = " + self.To_hex_str(return_code))
            # tkinter.messagebox.showerror('show error','save jpg fail! ret = '+self.To_hex_str(return_code))
            self.b_save_jpg = False
            return
        file_open = open(file_path.encode('utf-8'), 'wb+')
        img_buff = (c_ubyte * stParam.nImageLen)()
        try:
            cdll.msvcrt.memcpy(byref(img_buff), stParam.pImageBuffer, stParam.nImageLen)
            file_open.write(img_buff)
            self.b_save_jpg = False
            self.message_signal.emit("info","save jpg success!")
            # tkinter.messagebox.showinfo('show info','save jpg success!')
        except:
            self.b_save_jpg = False
            raise Exception("get one frame failed:%s" % e.message)
        if None != img_buff:
            del img_buff
        if None != self.buf_save_image:
            del self.buf_save_image

    def Save_Bmp(self,buf_cache,nWidth,nHeight,enPixelType,nFrameLen,frame_name):
        if(0 == buf_cache):
            return
        self.buf_save_image = None
        if not os.path.exists(self.file_path):
            os.makedirs(self.file_path)  
        file_path = self.file_path+str(self.st_frame_info.nFrameNum)+ frame_name + ".bmp" 
        print(file_path)   
        self.n_save_image_size = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3 + 2048
        if self.buf_save_image is None:
            self.buf_save_image = (c_ubyte * self.n_save_image_size)()
        
        print("save bmp",nWidth)
        print("save bmp",nHeight)
        print("save bmp",enPixelType)
        print("save bmp",nFrameLen)

        stParam = MV_SAVE_IMAGE_PARAM_EX()
        stParam.enImageType = MV_Image_Bmp;                                        # ch:需要保存的图像类型 | en:Image format to save
        stParam.enPixelType = enPixelType                               # ch:相机对应的像素格式 | en:Camera pixel type
        stParam.nWidth      = int(nWidth)                                    # ch:相机对应的宽 | en:Width
        stParam.nHeight     = int(nHeight)                                   # ch:相机对应的高 | en:Height
        stParam.nDataLen    = int(nFrameLen)
        stParam.pData       = cast(buf_cache, POINTER(c_ubyte))
        stParam.pImageBuffer=  cast(byref(self.buf_save_image), POINTER(c_ubyte)) 
        stParam.nBufferSize = int(nFrameLen)*3+2048;                               # ch:存储节点的大小 | en:Buffer node size
        return_code = self.obj_cam.MV_CC_SaveImageEx2(stParam)            
        if return_code != 0:
            self.message_signal.emit("Error","save bmp fail! ret = " + self.To_hex_str(return_code))
            # tkinter.messagebox.showerror('show error','save bmp fail! ret = '+self.To_hex_str(return_code))
            self.b_save_bmp = False
            return
        file_open = open(file_path.encode('utf-8'), 'wb+')
        img_buff = (c_ubyte * stParam.nImageLen)()
        try:
            cdll.msvcrt.memcpy(byref(img_buff), stParam.pImageBuffer, stParam.nImageLen)
            file_open.write(img_buff)
            self.b_save_bmp = False
            # self.message_signal.emit("info","save bmp success!")
            # tkinter.messagebox.showinfo('show info','save bmp success!')
        except Exception as e:
            self.b_save_bmp = False
            raise Exception("get one frame failed:%s" % e)
        if None != img_buff:
            del img_buff
        if None != self.buf_save_image:
            del self.buf_save_image

    def Is_mono_data(self,enGvspPixelType):
        if PixelType_Gvsp_Mono8 == enGvspPixelType or PixelType_Gvsp_Mono10 == enGvspPixelType \
            or PixelType_Gvsp_Mono10_Packed == enGvspPixelType or PixelType_Gvsp_Mono12 == enGvspPixelType \
            or PixelType_Gvsp_Mono12_Packed == enGvspPixelType:
            return True
        else:
            return False

    def Is_color_data(self,enGvspPixelType):
        if PixelType_Gvsp_BayerGR8 == enGvspPixelType or PixelType_Gvsp_BayerRG8 == enGvspPixelType \
            or PixelType_Gvsp_BayerGB8 == enGvspPixelType or PixelType_Gvsp_BayerBG8 == enGvspPixelType \
            or PixelType_Gvsp_BayerGR10 == enGvspPixelType or PixelType_Gvsp_BayerRG10 == enGvspPixelType \
            or PixelType_Gvsp_BayerGB10 == enGvspPixelType or PixelType_Gvsp_BayerBG10 == enGvspPixelType \
            or PixelType_Gvsp_BayerGR12 == enGvspPixelType or PixelType_Gvsp_BayerRG12 == enGvspPixelType \
            or PixelType_Gvsp_BayerGB12 == enGvspPixelType or PixelType_Gvsp_BayerBG12 == enGvspPixelType \
            or PixelType_Gvsp_BayerGR10_Packed == enGvspPixelType or PixelType_Gvsp_BayerRG10_Packed == enGvspPixelType \
            or PixelType_Gvsp_BayerGB10_Packed == enGvspPixelType or PixelType_Gvsp_BayerBG10_Packed == enGvspPixelType \
            or PixelType_Gvsp_BayerGR12_Packed == enGvspPixelType or PixelType_Gvsp_BayerRG12_Packed== enGvspPixelType \
            or PixelType_Gvsp_BayerGB12_Packed == enGvspPixelType or PixelType_Gvsp_BayerBG12_Packed == enGvspPixelType \
            or PixelType_Gvsp_YUV422_Packed == enGvspPixelType or PixelType_Gvsp_YUV422_YUYV_Packed == enGvspPixelType:
            return True
        else:
            return False

    def Mono_numpy(self,data,nWidth,nHeight):
        data_ = np.frombuffer(data, count=int(nWidth * nHeight), dtype=np.uint8, offset=0)
        data_mono_arr = data_.reshape(nHeight, nWidth)
        numArray = np.zeros([nHeight, nWidth, 1],"uint8")
        numArray[:, :, 0] = data_mono_arr
        return numArray

    def Color_numpy(self,data,nWidth,nHeight):
        data_ = np.frombuffer(data, count=int(nWidth*nHeight*3), dtype=np.uint8, offset=0)
        data_r = data_[0:nWidth*nHeight*3:3]
        data_g = data_[1:nWidth*nHeight*3:3]
        data_b = data_[2:nWidth*nHeight*3:3]

        data_r_arr = data_r.reshape(nHeight, nWidth)
        data_g_arr = data_g.reshape(nHeight, nWidth)
        data_b_arr = data_b.reshape(nHeight, nWidth)
        numArray = np.zeros([nHeight, nWidth, 3],"uint8")

        numArray[:, :, 0] = data_r_arr
        numArray[:, :, 1] = data_g_arr
        numArray[:, :, 2] = data_b_arr
        return numArray
    def Start_recording(self):
        print("Start recording")
        self.get_record_param()
        if None == self.stRecordPar :
            self.message_signal.emit("Error","Please open camera first!")
            return False
        if not self.b_start_grabbing:
            self.message_signal.emit("Error","Please start grabbing first!")
            return False 
        if not os.path.exists(self.video_path):
            os.makedirs(self.video_path)  
        self.stRecordPar.strFilePath= (self.video_path+'Recording.avi').encode('utf-8')
        nRet = self.obj_cam.MV_CC_StartRecord(self.stRecordPar)
        if nRet != 0: 
            print ("Start Record fail! nRet [0x%x]\n", nRet)
            self.message_signal.emit("Error","Start Record fail! nRet [0x%x]\n", nRet)
            return False

        return True
    
    def Stop_recording(self):
        ret = self.obj_cam.MV_CC_StopRecord()
        if ret != 0:
            print ("stop Record fail! ret[0x%x]" % ret)
            self.message_signal.emit("Error","stop Record fail! ret[0x%x]" % ret)
            return False
        return True
