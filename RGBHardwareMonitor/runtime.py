import ctypes
import os
import subprocess
import sys
from threading import Event

import win32con
import win32event
import win32process
from win32comext.shell import shellcon
from win32comext.shell.shell import ShellExecuteEx


quit_event = Event()
pause_event = Event()

config = None
config_path = None


def in_bundled_app():
    return getattr(sys, 'frozen', False)


def inside_conda_or_venv():
    is_venv = hasattr(sys, 'real_prefix')
    is_conda = 'CONDA_PREFIX' in os.environ
    return is_venv or is_conda


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
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


def run_self_as_admin(new_args=None, **kwargs):
    if inside_conda_or_venv():
        raise NotImplementedError('Cannot rerun elevated within conda or venv')
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


def subprocess_pyinstaller():
    if hasattr(subprocess, 'STARTUPINFO'):  # Windows
        # Prevent command window from opening
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        env = os.environ  # Fix search paths
    else:
        si = None
        env = None

    ret = dict(stdin=subprocess.PIPE,
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               startupinfo=si,
               env=env)
    return ret


def subprocess_run(args, **kwargs):
    return subprocess.run(args, **kwargs, **subprocess_pyinstaller())


def app_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
