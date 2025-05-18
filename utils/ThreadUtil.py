import threading
import time

from comtypes import CoInitialize
from injector import Injector, singleton, inject

from utils.GetProcessUtil import get_all_audio_sessions
from utils.AudioUtil import AudioUtil
from utils.ConfigUtil import ConfigUtil
from utils.LoggerUtil import LoggerUtil


@singleton
class ThreadUtil:
    @inject
    def __init__(self, injector: Injector, config_util: ConfigUtil,
                 event: threading.Event, logger_util: LoggerUtil):
        self.injector = injector
        self.config_util = config_util
        self.event = event
        self.logger = logger_util.logger
        self.audio_threads = {}  # 存储正在运行的音频控制线程
        self.thread_events = {}  # 存储每个线程的独立事件

    def start_audio_control_threads(self):
        alive_process = [process.name for process in threading.enumerate() if process.is_alive()]
        sessions = get_all_audio_sessions()
        
        # 获取当前配置中的进程列表
        configured_processes = set(self.config_util.config["processes"].keys())
        
        # 停止不再需要的线程
        for process_name in list(self.audio_threads.keys()):
            if process_name not in configured_processes:
                self.logger.info(f"Stopping audio control for removed process: {process_name}")
                if process_name in self.audio_threads:
                    thread = self.audio_threads[process_name]
                    if thread.is_alive():
                        # 使用线程特定的事件来停止线程
                        if process_name in self.thread_events:
                            self.thread_events[process_name].set()
                            thread.join(timeout=2)  # 等待线程结束
                            del self.thread_events[process_name]
                    del self.audio_threads[process_name]

        # 启动新的音频控制线程
        for session in sessions:
            process_name = session.Process.name()
            if process_name in configured_processes and str(session.ProcessId) not in alive_process:
                if process_name not in self.audio_threads:
                    self.logger.info(f"Found target process: {process_name} (PID: {session.ProcessId})")
                    # 为每个线程创建独立的事件
                    thread_event = threading.Event()
                    self.thread_events[process_name] = thread_event
                    audio_util = AudioUtil(session, self.config_util, thread_event, self.logger)
                    thread = threading.Thread(target=audio_util.loop, name=session.ProcessId)
                    thread.start()
                    self.audio_threads[process_name] = thread

    def background_scanner(self):
        CoInitialize()

        config = self.config_util.config
        bg_scan_interval = config["setting"]["bg_scan_interval"]
        self.logger.info(f"Starting with scan interval: {bg_scan_interval}s")
        while True:
            self.start_audio_control_threads()
            time.sleep(bg_scan_interval)
