import os
import tkinter as tk
from tkinter import ttk
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image, ImageTk
import yaml
import sys
from injector import singleton, inject

from utils.GetProcessUtil import get_real_time_process_list
from utils.ConfigUtil import ConfigUtil
from utils.LoggerUtil import LoggerUtil


@singleton
class GUIUtil:
    @inject
    def __init__(self, config_util: ConfigUtil, logger_util: LoggerUtil):
        self.config_util = config_util
        self.logger = logger_util.logger
        self.root = None
        self.process_vars = {}  # 存储进程的复选框变量
        self.process_icons = {}  # 存储进程的图标
        self.is_visible = False
        self.scrollable_frame = None
        self.auto_refresh_timer = None
        self.logger.info("GUIUtil initialized")

    def get_process_icon(self, process_name):
        """获取进程的图标"""
        try:
            # 获取进程路径
            for session in get_real_time_process_list()[1]:  # 使用新的实时获取函数
                if session.Process.name() == process_name:
                    exe_path = session.Process.exe()
                    break
            else:
                return None

            # 获取图标
            large, small = win32gui.ExtractIconEx(exe_path, 0, 1)
            win32gui.DestroyIcon(small[0])

            # 转换图标为位图
            ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
            ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)

            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
            hdc = hdc.CreateCompatibleDC()

            hdc.SelectObject(hbmp)
            hdc.DrawIcon((0, 0), large[0])

            win32gui.DestroyIcon(large[0])

            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGBA',
                (ico_x, ico_y),
                bmpstr, 'raw', 'BGRA', 0, 1
            )

            hdc.DeleteDC()
            win32gui.DeleteObject(hbmp.GetHandle())

            return ImageTk.PhotoImage(img)
        except Exception as e:
            self.logger.error(f"Error getting icon for {process_name}: {str(e)}")
            return None

    def update_config(self):
        """更新配置文件"""
        try:
            # 读取当前配置
            with open(self.config_util.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 更新进程列表
            config['processes'] = {}
            for process_name, var in self.process_vars.items():
                if var.get():
                    config['processes'][process_name] = None

            # 保存配置
            with open(self.config_util.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)

            # 重新加载配置
            self.config_util._read()
            self.logger.info("Configuration updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating config: {str(e)}")

    def refresh_process_list(self):
        """刷新进程列表"""
        self.logger.info("Refreshing process lists...")
        try:
            # 清除现有的复选框
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            self.process_vars.clear()
            self.process_icons.clear()

            # 获取最新的进程列表
            window_processes, audio_sessions = get_real_time_process_list()
            self.logger.info(f"Process lists refreshed. Found {len(window_processes)} window processes and {len(audio_sessions)} audio sessions")

            # 获取当前配置的进程
            current_processes = set(self.config_util.config['processes'].keys())

            # 为每个进程创建复选框
            for session in audio_sessions:
                process_name = session.Process.name()
                if process_name not in self.process_vars:
                    var = tk.BooleanVar(value=process_name in current_processes)
                    self.process_vars[process_name] = var

                    # 获取进程图标
                    icon = self.get_process_icon(process_name)
                    self.process_icons[process_name] = icon

                    # 创建复选框
                    cb = ttk.Checkbutton(
                        self.scrollable_frame,
                        text=process_name,
                        variable=var,
                        image=icon if icon else None,
                        compound=tk.LEFT,
                        command=self.update_config
                    )
                    cb.pack(anchor=tk.W, padx=5, pady=2)

            self.logger.info("Process list refreshed successfully")
        except Exception as e:
            self.logger.error(f"Error refreshing process list: {str(e)}")

    def start_auto_refresh(self):
        """启动自动刷新定时器"""
        if self.auto_refresh_timer:
            self.root.after_cancel(self.auto_refresh_timer)
        self.auto_refresh_timer = self.root.after(1000, self.auto_refresh)  # 每1秒刷新一次

    def auto_refresh(self):
        """自动刷新进程列表"""
        if self.is_visible:
            self.refresh_process_list()
        self.start_auto_refresh()

    def create_gui(self):
        """创建图形界面"""
        self.logger.info("Creating GUI...")
        if self.root is not None:
            self.logger.info("GUI already exists")
            return

        try:
            self.root = tk.Tk()
            self.root.title("AutoMuteBG 进程管理")
            self.root.geometry("400x600")
            self.logger.info("Basic window created")

            # 创建主框架
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # 创建顶部按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))

            # 创建刷新按钮
            refresh_button = ttk.Button(
                button_frame,
                text="刷新进程列表",
                command=self.refresh_process_list
            )
            refresh_button.pack(side=tk.RIGHT)

            # 创建说明标签
            label = ttk.Label(
                main_frame,
                text="勾选要控制的进程，取消勾选则停止控制\n配置会自动保存",
                justify=tk.LEFT
            )
            label.pack(anchor=tk.W, pady=(0, 10))

            # 创建画布和滚动条
            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            self.scrollable_frame = ttk.Frame(canvas)

            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # 放置画布和滚动条
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # 绑定鼠标滚轮事件
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # 设置关闭窗口的处理
            def on_closing():
                self.logger.info("Window closing")
                self.hide()  # 隐藏窗口而不是退出程序
            self.root.protocol("WM_DELETE_WINDOW", on_closing)

            # 初始刷新进程列表
            self.refresh_process_list()
            
            # 启动自动刷新
            self.start_auto_refresh()

            self.logger.info("GUI creation completed")
        except Exception as e:
            self.logger.error(f"Error creating GUI: {str(e)}")
            raise

    def show(self):
        """显示图形界面"""
        self.logger.info("Show GUI requested")
        try:
            if self.root is None:
                self.logger.info("Root window is None, creating new GUI")
                self.create_gui()
            else:
                self.logger.info("Root window exists, attempting to show it")
                self.root.deiconify()  # 重新显示窗口
                self.logger.info("Window deiconified")
                self.root.lift()  # 将窗口提升到最前
                self.logger.info("Window lifted")
                self.root.focus_force()  # 强制获取焦点
                self.logger.info("Window focus forced")
                # 刷新进程列表
                self.refresh_process_list()
                # 重新启动自动刷新
                self.start_auto_refresh()
            self.is_visible = True
            self.logger.info("Window shown successfully")
        except Exception as e:
            self.logger.error(f"Error in show method: {str(e)}")
            raise

    def hide(self):
        """隐藏图形界面"""
        self.logger.info("Hide GUI requested")
        try:
            if self.root is not None:
                self.logger.info("Root window exists, attempting to hide it")
                self.root.withdraw()  # 使用withdraw而不是destroy
                self.logger.info("Window withdrawn")
                self.is_visible = False
                # 停止自动刷新
                if self.auto_refresh_timer:
                    self.root.after_cancel(self.auto_refresh_timer)
                    self.auto_refresh_timer = None
                self.logger.info("Window hidden successfully")
            else:
                self.logger.info("Root window is None, nothing to hide")
        except Exception as e:
            self.logger.error(f"Error in hide method: {str(e)}")
            raise

    def quit(self):
        """退出图形界面"""
        self.logger.info("Quit GUI requested")
        if self.root is not None:
            # 停止自动刷新
            if self.auto_refresh_timer:
                self.root.after_cancel(self.auto_refresh_timer)
                self.auto_refresh_timer = None
            self.root.quit()  # 停止主循环
            self.root.destroy()  # 销毁窗口
            self.root = None
            self.is_visible = False
            self.logger.info("GUI destroyed") 