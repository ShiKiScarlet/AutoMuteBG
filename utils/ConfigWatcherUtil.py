import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from injector import singleton, inject

from utils.ConfigUtil import ConfigUtil
from utils.LoggerUtil import LoggerUtil


@singleton
class ConfigWatcherUtil:
    @inject
    def __init__(self, config_util: ConfigUtil, logger_util: LoggerUtil):
        self.config_util = config_util
        self.logger = logger_util.logger
        self.observer = None

    def start_watching(self):
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, config_util, logger):
                self.config_util = config_util
                self.logger = logger
                self.last_modified = time.time()

            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('config.yaml'):
                    # 防止重复触发
                    current_time = time.time()
                    if current_time - self.last_modified > 1:
                        self.last_modified = current_time
                        self.logger.info("Config file changed, reloading...")
                        try:
                            self.config_util._read()
                            self.logger.info("Config reloaded successfully")
                        except Exception as e:
                            self.logger.error(f"Failed to reload config: {str(e)}")

        event_handler = ConfigFileHandler(self.config_util, self.logger)
        self.observer = Observer()
        self.observer.schedule(event_handler, path='.', recursive=False)
        self.observer.start()
        self.logger.info("Started watching config.yaml for changes")

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Stopped watching config.yaml") 