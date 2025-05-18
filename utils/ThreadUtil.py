import threading
import time

from comtypes import CoInitialize
from injector import Injector, singleton, inject

from utils.GetProcessUtil import get_all_audio_sessions, get_real_time_process_list
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
        """启动音频控制线程"""
        try:
            # 获取当前所有音频会话
            sessions = get_real_time_process_list()[1]
            self.logger.info(f"Getting fresh audio sessions list")
            self.logger.info(f"Found {len(sessions)} audio sessions")

            # 获取配置的进程列表
            configured_processes = set(self.config_util.config['processes'].keys())

            # 获取当前正在运行的音频控制线程的进程名
            running_processes = set(self.audio_threads.keys())

            # 启动新的音频控制线程
            for session in sessions:
                process_name = session.Process.name()
                if process_name in configured_processes and process_name not in running_processes:
                    self.logger.info(f"Found target process: {process_name} (PID: {session.ProcessId})")
                    # 为每个线程创建独立的事件
                    thread_event = threading.Event()
                    self.thread_events[process_name] = thread_event
                    audio_util = AudioUtil(session, self.config_util, thread_event, self.logger)
                    thread = threading.Thread(target=audio_util.loop, name=str(session.ProcessId))
                    thread.start()
                    self.audio_threads[process_name] = thread

            # 清理已结束的线程
            for process_name in list(self.audio_threads.keys()):
                if not self.audio_threads[process_name].is_alive():
                    self.logger.info(f"Cleaning up dead thread for process: {process_name}")
                    del self.audio_threads[process_name]
                    if process_name in self.thread_events:
                        del self.thread_events[process_name]

        except Exception as e:
            self.logger.error(f"Error in start_audio_control_threads: {str(e)}")
            raise

    def background_scanner(self):
        CoInitialize()

        config = self.config_util.config
        bg_scan_interval = config["setting"]["bg_scan_interval"]
        self.logger.info(f"Starting with scan interval: {bg_scan_interval}s")
        while True:
            self.start_audio_control_threads()
            time.sleep(bg_scan_interval)
