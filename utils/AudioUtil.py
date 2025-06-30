import threading
import time

from pycaw.utils import AudioSession

from utils.ConfigUtil import ConfigUtil
from utils.LoggerUtil import LoggerUtil
from utils.ProcessUtil import ProcessUtil

# 两个缓动公式
# Source: https://blog.csdn.net/songche123/article/details/102520760
def _ease_in_cubic(t, b, c, d):
    t /= d
    return c * t * t * t + b


def _ease_out_cubic(t, b, c, d):
    t = t / d - 1
    return c * (t * t * t + 1) + b


class AudioUtil:
    def __init__(self, session: AudioSession, config_util: ConfigUtil,
                 event: threading.Event, logger: LoggerUtil.logger):
        self.session = session
        self.config = config_util.get_by_process(session.Process.name())
        self.event = event
        self.logger = logger

        self.process_util = ProcessUtil(session.Process)
        self.last_target_volume = None
        self.last_volume = None
        self.easing_thread = None
        self.stop_easing_thread = threading.Event()  # 使用Event来控制线程停止

        # 运行函数
        self._check_fg_volume()

    def _check_fg_volume(self):
        if self.config["fg_volume"] == "auto":
            self.config["fg_volume"] = self.session.SimpleAudioVolume.GetMasterVolume()
            # 意外退出的情况
            if self.config["fg_volume"] == self.config["bg_volume"]:
                self.config["fg_volume"] = 1
            self.logger.info(f"Change fg_volume to {self.config['fg_volume']}.")

    def set_volume(self, volume: float):
        def no_easing(cur_volume=volume):
            try:
                self.session.SimpleAudioVolume.SetMasterVolume(cur_volume, None)
                self.last_volume = cur_volume
            except Exception as e:
                self.logger.error(f"Error setting volume: {str(e)}")

        def easing(stop_event):
            f = _ease_in_cubic if self.last_volume < volume else _ease_out_cubic
            c = volume - self.last_volume
            this_last_volume = self.last_volume
            for i in range(self.config["easing"]["steps"]):
                if stop_event.is_set():
                    break
                cur_volume = f(i + 1, this_last_volume, c, self.config["easing"]["steps"])
                no_easing(cur_volume)
                time.sleep(self.config["easing"]["duration"] / self.config["easing"]["steps"])

        def stop_easing():
            if self.easing_thread is not None and self.easing_thread.is_alive():
                self.stop_easing_thread.set()
                self.easing_thread.join(timeout=1.0)  # 添加超时确保不会无限等待
                self.stop_easing_thread.clear()  # 重置事件状态

        if self.last_target_volume != volume:
            self.last_target_volume = volume
            if self.config["easing"] is None or self.last_volume is None:
                no_easing()
            else:
                stop_easing()  # 停止之前的easing线程
                self.stop_easing_thread.clear()  # 确保事件为清除状态
                self.easing_thread = threading.Thread(
                    target=easing,
                    args=(self.stop_easing_thread,),
                    name="EasingThread",
                    daemon=True
                )
                self.easing_thread.start()

    def loop(self):
        self.logger.info("Starting loop.")
        try:
            while not self.event.is_set():
                if self.session.ProcessId <= 0:
                    self.logger.error(f"Invalid PID detected: {self.session.ProcessId}")
                    break  # 退出循环
                # 检查进程是否仍在运行
                if not self.process_util.is_running():
                    self.logger.error(f"Process no longer exists (PID: {self.process_util.pid})")
                    break  # 退出循环
                if self.process_util.is_window_in_foreground():
                    self.set_volume(self.config["fg_volume"])
                else:
                    self.set_volume(self.config["bg_volume"])
                time.sleep(self.config["loop_interval"])
        except Exception as e:
            self.logger.error(f"Error in audio control loop: {str(e)}")
        finally:
            # 停止easing线程
            if self.easing_thread is not None and self.easing_thread.is_alive():
                self.stop_easing_thread.set()
                self.easing_thread.join(timeout=1.0)
                
            # 当线程被停止时，恢复原始音量
            try:
                original_volume = self.session.SimpleAudioVolume.GetMasterVolume()
                if original_volume == self.config["bg_volume"]:
                    self.session.SimpleAudioVolume.SetMasterVolume(self.config["fg_volume"], None)
            except Exception as e:
                self.logger.error(f"Error setting final volume: {str(e)}")
        self.logger.info("Exiting loop.")
