import logging
import os
import sys
from datetime import datetime

from injector import singleton, inject

from utils.ConfigUtil import ConfigUtil

LOG_PATH = "../logs/"


def get_log_dir():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, 'logs')
    else:
        # Running as script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        main_dir = os.path.dirname(script_dir)
        return os.path.join(main_dir, 'logs')


@singleton
class LoggerUtil:
    logger = None

    @inject
    def __init__(self, config_util: ConfigUtil):
        self.max_log_files = config_util.config["setting"]["max_log_files"]

        self.log_dir = get_log_dir()
        self.logger = self._setup_logging()

        self._delete_old_log_files()

    def _setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")

        # 设置控制台日志输出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.WARNING)  # 控制台只显示警告和错误
        logger.addHandler(console_handler)

        if self.max_log_files > 0:
            os.makedirs(self.log_dir, exist_ok=True)
            log_file = os.path.join(self.log_dir, datetime.now().strftime("%Y%m%d%H%M%S") + ".log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)  # 文件保持详细日志
            logger.addHandler(file_handler)

        return logger

    def _delete_old_log_files(self):
        log_files = [f for f in os.listdir(self.log_dir) if f.endswith(".log")]
        log_files.sort()

        if len(log_files) > self.max_log_files:
            files_to_delete = log_files[:len(log_files) - self.max_log_files]
            for file_name in files_to_delete:
                file_path = os.path.join(self.log_dir, file_name)
                os.remove(file_path)
