import win32gui
import win32process
import psutil
from pycaw.utils import AudioUtilities
import time

# 添加缓存存储上次的窗口进程列表和缓存刷新控制
_cached_window_processes = []
_cached_audio_sessions = []
_last_window_processes_refresh = 0
_last_audio_sessions_refresh = 0
_cache_ttl = 0.5  # 缓存有效期（秒）

def get_all_audio_sessions(force_refresh=False):
    """获取所有音频会话，支持缓存"""
    global _cached_audio_sessions, _last_audio_sessions_refresh
    current_time = time.time()
    
    # 如果强制刷新或缓存过期，则获取新的音频会话列表
    if force_refresh or (current_time - _last_audio_sessions_refresh) > _cache_ttl or not _cached_audio_sessions:
        sessions = AudioUtilities.GetAllSessions()
        _cached_audio_sessions = [session for session in sessions if session.Process is not None]
        _last_audio_sessions_refresh = current_time
    
    return _cached_audio_sessions

def get_all_window_processes(force_refresh=False):
    """获取所有窗口进程，支持缓存"""
    global _cached_window_processes, _last_window_processes_refresh
    current_time = time.time()
    
    # 如果强制刷新或缓存过期，则获取新的窗口列表
    if force_refresh or (current_time - _last_window_processes_refresh) > _cache_ttl or not _cached_window_processes:
        new_window_processes = []
        ignore_list = ['TextInputHost.exe']  # 添加过滤列表

        def enum_window_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    p = psutil.Process(pid)
                    process_name = p.name()
                    if process_name not in ignore_list:
                        window_title = win32gui.GetWindowText(hwnd)
                        new_window_processes.append((process_name, window_title))
                except psutil.NoSuchProcess:
                    pass

        win32gui.EnumWindows(enum_window_callback, None)
        
        # 保存当前状态用于下次比较
        _cached_window_processes = new_window_processes
        _last_window_processes_refresh = current_time
    
    return _cached_window_processes

def get_real_time_process_list(force_refresh=False):
    """
    获取实时的进程列表，包括窗口进程和音频会话
    返回: (window_processes, audio_sessions)
    参数:
        force_refresh: 是否强制刷新缓存
    """
    window_processes = get_all_window_processes(force_refresh)
    audio_sessions = get_all_audio_sessions(force_refresh)
    return window_processes, audio_sessions
