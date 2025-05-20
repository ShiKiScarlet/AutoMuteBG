from typing import List
import logging
import win32gui
import win32process
import psutil
from psutil import Process


class ProcessUtil:
    def __init__(self, process: Process):
        self.process = process
        self.pid = process.pid
        self.process_name = process.name()
        self.logger = logging.getLogger()
        self.logger.info(f"初始化进程追踪: {self.process_name} (PID: {self.pid})")
        # 用于存储已知不匹配的PID
        self.known_non_matching_pids = set()

    def is_running(self):
        return self.process.is_running()

    def is_window_in_foreground(self):
        """检查进程的窗口是否处于前台，支持PID变化的情况"""
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            _, foreground_pid = win32process.GetWindowThreadProcessId(foreground_hwnd)
            
            # 首先尝试PID直接比较
            if foreground_pid == self.pid:
                return True
                
            # 如果PID在已知不匹配列表中，直接返回False
            if foreground_pid in self.known_non_matching_pids:
                return False
                
            # 如果PID不匹配，尝试进程名比较
            try:
                foreground_process = psutil.Process(foreground_pid)
                foreground_process_name = foreground_process.name()
                
                # 如果进程名匹配但PID不同，说明PID变化了
                if foreground_process_name == self.process_name:
                    # 更新PID
                    self.pid = foreground_pid
                    self.logger.info(f"检测到PID变化: {self.process_name} 新PID: {self.pid}")
                    return True
                else:
                    # 进程名不匹配，将PID加入已知不匹配列表
                    self.known_non_matching_pids.add(foreground_pid)
                    
            except psutil.NoSuchProcess:
                # 如果进程已经结束，也将其加入已知不匹配列表
                self.known_non_matching_pids.add(foreground_pid)
                pass  # 前台进程可能已经结束，忽略此错误
                
            return False
            
        except Exception as e:
            self.logger.error(f"前台窗口检查错误: {str(e)}")
            return False

    def get_process_hwnd_list(self):
        """获取指定PID进程的所有窗口句柄"""
        def callback(hwnd, res: List):
            if not win32gui.IsWindowVisible(hwnd):
                return
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == self.pid:
                    res.append(hwnd)
            except Exception:
                pass

        hwnd_list = []
        win32gui.EnumWindows(callback, hwnd_list)
        return hwnd_list
        
    def get_process_hwnd_list_by_name(self):
        """获取指定名称的所有进程的窗口句柄"""
        def callback(hwnd, res: List):
            if not win32gui.IsWindowVisible(hwnd):
                return
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(window_pid)
                    if proc.name() == self.process_name:
                        res.append(hwnd)
                except psutil.NoSuchProcess:
                    pass
            except Exception:
                pass

        hwnd_list = []
        win32gui.EnumWindows(callback, hwnd_list)
        return hwnd_list
