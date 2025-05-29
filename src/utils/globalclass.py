from PySide6.QtCore import QObject, Signal, QThread, QMutex, QWaitCondition, QTimer,QMutexLocker
import numpy as np
import queue
import threading


class DetectionQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.__init__()
            return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.pending_queue = queue.Queue(maxsize=100)
            # self.completed_queue = queue.Queue(maxsize=100)
            self.pending_lock = QMutex()
            # self.completed_lock = QMutex()
            self.pending_cond = QWaitCondition()
            self._initialized = True

    def add_pending(self, image):
        with QMutexLocker(self.pending_lock):
            try:
                self.pending_queue.put_nowait(image)
                print("add pending")
                self.pending_cond.wakeAll()
                return True
            except queue.Full:
                return False

    def get_pending(self, timeout=100):
        with QMutexLocker(self.pending_lock):
            if self.pending_queue.empty():
                self.pending_cond.wait(self.pending_lock, timeout)
            try:
                return self.pending_queue.get_nowait()
            except queue.Empty:
                return None
    def clear_all(self):
        """线程安全的清空待检测队列"""
        with QMutexLocker(self.pending_lock):
            # 循环取出所有元素直到队列为空
            while not self.pending_queue.empty():
                try:
                    self.pending_queue.get_nowait()
                except queue.Empty:
                    break
            
            # 唤醒所有等待线程（防止死锁）
            self.pending_cond.wakeAll()
    # def add_completed(self, result):
    #     with QMutexLocker(self.completed_lock):
    #         self.completed_queue.put_nowait(result)

    # def get_completed(self):
    #     with QMutexLocker(self.completed_lock):
    #         try:
    #             return self.completed_queue.get_nowait()
    #         except queue.Empty:
    #             return None