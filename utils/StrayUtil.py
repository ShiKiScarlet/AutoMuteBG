import os
import threading
import webbrowser
import pystray
import win32api
import win32con
from PIL import Image
from injector import singleton, inject
import sys

from utils.GetProcessUtil import get_real_time_process_list
from utils.ConfigUtil import ConfigUtil
from utils.LoggerUtil import LoggerUtil
from utils.GUIUtil import GUIUtil


def _open_site():
    webbrowser.open('https://gitee.com/lingkai5wu/AutoMuteBG')


def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


@singleton
class StrayUtil:
    @inject
    def __init__(self, config_util: ConfigUtil, logger_util: LoggerUtil, 
                 event: threading.Event, gui_util: GUIUtil):
        self.setup_msg = config_util.config["setting"]["setup_msg"]
        self.logger = logger_util.logger
        self.event = event
        self.gui_util = gui_util
        self.icon = None
        self.logger.info("StrayUtil initialized")

    def run_detached(self):
        """在后台运行系统托盘图标"""
        self.logger.info("Starting stray.")
        icon_path = get_resource_path(os.path.join("resource", "mute.ico"))
        self.logger.info(f"Loading icon from: {icon_path}")
        image = Image.open(icon_path)

        def on_exit(icon, item):
            """处理退出事件"""
            self.logger.info("Exiting by StrayUtil.")
            self.event.set()
            icon.stop()
            self.gui_util.quit()

        def on_icon_ready(icon):
            """图标准备就绪时的回调"""
            icon.visible = True
            if self.setup_msg:
                icon.notify("程序启动成功，点击托盘图标打开设置")
            threading.current_thread().setName("StrayRunCallbackThread")
            self.logger.info("Stray is running.")

        def show_settings(icon, item):
            """显示设置窗口"""
            self.logger.info("Show settings requested from tray menu")
            try:
                self.gui_util.show()
                self.logger.info("GUI show method called successfully")
            except Exception as e:
                self.logger.error(f"Error showing GUI: {str(e)}")

        # 创建菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示设置", show_settings),
            pystray.MenuItem("进程列表", self._save_process_list_to_txt),
            pystray.MenuItem("关于", self.show_version_info),
            pystray.MenuItem("开源地址", _open_site),
            pystray.MenuItem(
                "退出",
                on_exit
            )
        )

        # 创建系统托盘图标
        self.icon = pystray.Icon(
            "AutoMuteBG",
            image,
            "AutoMuteBG",
            menu
        )

        # 在新线程中运行
        threading.Thread(
            target=self.icon.run,
            args=(on_icon_ready,),
            name="StrayThread",
            daemon=True
        ).start()

    def show_version_info(self):
        version_info = "后台应用自动静音器\n让设定的进程在后台时自动静音，切换到前台恢复。\n版本: 0.2.2 Dev\n开源地址: github.com/lingkai5wu/AutoMuteBG"
        win32api.MessageBox(0, version_info, "关于Auto Mute Background", 0x40) 
    
    def _save_process_list_to_txt(self):
        filename = "process_name.txt"
        window_processes, audio_sessions = get_real_time_process_list()
        with open(filename, 'w', encoding="utf-8") as file:
            if window_processes:
                file.write("当前在窗口管理器中注册的进程：\n窗口标题 - 进程名\n")
            else:
                file.write("当前在窗口管理器中没有进程，请先启动任意进程并打开窗口。")
            for process_name, window_title in window_processes:
                file.write(f"{window_title} - {process_name}\n")
            file.write("\n")
            if audio_sessions:
                file.write("当前在音量合成器中注册的进程：\n进程名\n")
            else:
                file.write("当前在音量合成器中没有进程，请先启动任意进程并播放声音。")
            for session in audio_sessions:
                process_name = session.Process.name()
                file.write(f"{process_name}\n")
        self.logger.info(f"Process list saved to {filename}.")
        os.startfile(filename)

    def _show_settings(self):
        # Implementation of _show_settings method
        pass
