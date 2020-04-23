import ctypes
import logging
import os
import sys
from threading import Event

import win32con, win32event, win32process
from win32comext.shell.shell import ShellExecuteEx
from win32comext.shell import shellcon


# ----- LOGGING ----- #

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


# ----- RUNTIME ----- #

quit_event = Event()


def in_bundled_app():
    return getattr(sys, 'frozen', False)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin(exe_path, args=None, run_dir=None, show_cmd=None, wait=False):
    show_cmd = win32con.SW_NORMAL if show_cmd is None else show_cmd
    if args is None:
        args = tuple()
    args = " ".join(args)
    if run_dir is None:
        run_dir = ''

    procInfo = ShellExecuteEx(
        lpVerb='runas',
        lpFile=exe_path,
        lpParameters=args,
        lpDirectory=run_dir,
        nShow=show_cmd,
        fMask=shellcon.SEE_MASK_NOCLOSEPROCESS | shellcon.SEE_MASK_FLAG_NO_UI,
    )

    if wait:
        procHandle = procInfo['hProcess']
        obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
        rc = win32process.GetExitCodeProcess(procHandle)
        # print "Process handle %s returned code %s" % (procHandle, rc)
    else:
        rc = None

    return rc


# TODO: Conda/venv detection or maybe raise error?
def run_self_as_admin(new_args=None, **kwargs):
    run_dir = os.getcwd()
    if new_args is None:
        new_args = sys.argv[1:]
    if not in_bundled_app():  # When not running in bundled app, prepend script path
        new_args.insert(0, sys.argv[0])
    run_as_admin(sys.executable, new_args, run_dir=run_dir, **kwargs)


def ensure_admin():
    if not is_admin():
        run_as_admin(sys.executable, sys.argv)
        exit()


# ----- PATHS ----- #

def app_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
