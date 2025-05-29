from PySide6.QtGui import QPixmap,QImage
import sys
from pathlib import Path
#获取选取设备信息的索引，通过[]之间的字符去解析
def TxtWrapBy(start_str, end, all_text):
    start = all_text.find(start_str)
    if start >= 0:
        start += len(start_str)
        end_index = all_text.find(end, start)
        if end_index >= 0:
            return all_text[start:end_index].strip()
    return ""
#将返回的错误码转换为十六进制显示
def ToHexStr(num):
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


def pil_to_pixmap(pil_image):
        if pil_image.mode == "RGB":
            qimage = QImage(
                pil_image.tobytes(),
                pil_image.width,
                pil_image.height,
                QImage.Format_RGB888
            )
        elif pil_image.mode == "L":
            qimage = QImage(
                pil_image.tobytes(),
                pil_image.width,
                pil_image.height,
                QImage.Format_Grayscale8
            )
        return QPixmap.fromImage(qimage)


def load_basepath():
    """智能加载SDK目录下的DLL"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS  # 打包环境
    else:
        # 开发环境：当前文件 → 上级目录 → 同级目录的net
        current_file_path = Path(__file__).resolve()
        base_path = current_file_path.parent.parent.parent
    
    return base_path