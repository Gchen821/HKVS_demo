import os
from mmcv import __file__ as mmcv_path

# 手动添加_ext模块
mmcv_dir = os.path.dirname(mmcv_path)
ext_files = []
for f in os.listdir(mmcv_dir):
    if '_ext' in f and (f.endswith('.so') or f.endswith('.pyd')):
        ext_files.append((os.path.join(mmcv_dir, f), 'mmcv'))

print(ext_files)