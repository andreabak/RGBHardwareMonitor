import ctypes
import logging

import win32con


LOG_FORMAT = '%(asctime)s [%(module)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

logger = logging.getLogger('RGBHardwareMonitor')
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFORMAT)

log_stream_handler = logging.StreamHandler()
log_stream_handler.setFormatter(log_formatter)
logger.addHandler(log_stream_handler)

log_file_handler = None


def setup_file_logging(file_path, log_level):
    global log_file_handler, logger, log_formatter
    log_file_handler = logging.FileHandler(file_path)
    log_file_handler.setFormatter(log_formatter)
    log_file_handler.setLevel(log_level)
    logger.addHandler(log_file_handler)


def error_popup(msg, title='Error'):
    return ctypes.windll.user32.MessageBoxW(0, msg, title, win32con.MB_ICONERROR)
