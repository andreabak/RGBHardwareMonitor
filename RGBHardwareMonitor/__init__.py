import ctypes
import logging
import sys
from threading import Event


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


quit_event = Event()


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin(exe_path, *args, run_dir=None):
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, " ".join(args), run_dir, 1)
    if result <= 32:  # failed
        raise OSError('Failed running process with elevated privileges')


def ensure_admin():
    if not is_admin():
        run_as_admin(sys.executable, sys.argv)
        exit()
