import os
import sys
import subprocess

import win32con

from . import run_self_as_admin, is_admin, in_bundled_app, error_popup

schedtask_name = 'RGBHardwareMonitor'

ps_schedtask_defs = {
    'name': schedtask_name,
    'workingDir': os.getcwd(),
    'command': sys.executable,
}
if not in_bundled_app():  # When not running in bundled app, append script path as argument
    ps_schedtask_defs['params'] = sys.argv[0]
ps_schedtask_defs = [f"${name} = '{value}'" for name, value in ps_schedtask_defs.items()]
ps_schedtask_create = [
    "$action = New-ScheduledTaskAction –Execute \"$command\" -WorkingDirectory \"$workingDir\""
    + (' -Argument "$params"' if not in_bundled_app() else ''),
    "$trigger = New-ScheduledTaskTrigger -AtLogon",
    "Register-ScheduledTask –TaskName $name -Action $action –Trigger $trigger -RunLevel highest | Out-Null",
]
ps_schedtask_delete = [
    "Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction:SilentlyContinue",
]
ps_schedtask_check = [
    "Get-ScheduledTask -TaskName $name",
]


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


def ps_bake_commands(*lines):
    return ['powershell', '-Command', f'{{ {"; ".join(lines)} }}']


def ps_run(*commands, raise_on_error=True):
    baked_commands = ps_bake_commands(*commands)
    process = subprocess.run(['powershell', *baked_commands], text=True, **subprocess_pyinstaller())
    if raise_on_error and process.returncode != 0:
        raise RuntimeError(f'Failed executing powershell script (return code = {process.returncode})\n\n'
                           f'{process.stdout}\n\n{process.stderr}')
    return process


is_enabled = None


# TODO: DRY Merge functions (autorun elevate or something)
def create_autorun():  # TODO: Check return codes
    if is_admin():
        ps_run(*ps_schedtask_defs, *ps_schedtask_delete, *ps_schedtask_create)
    else:
        run_self_as_admin(new_args=['--autorun', 'enable'], show_cmd=win32con.SW_HIDE, wait=True)


# TODO: DRY Merge functions (autorun elevate or something)
def delete_autorun():  # TODO: Check return codes
    if is_admin():
        ps_run(*ps_schedtask_defs, *ps_schedtask_delete)
    else:
        run_self_as_admin(new_args=['--autorun', 'disable'], show_cmd=win32con.SW_HIDE, wait=True)


def check_autorun():
    global is_enabled
    is_enabled = ps_run(*ps_schedtask_defs, *ps_schedtask_check, raise_on_error=False).returncode == 0
    return is_enabled


def set_autorun(state):
    prev_state = check_autorun()
    if prev_state != state:
        if state:
            create_autorun()
        else:
            delete_autorun()
        check_autorun()


def toggle_autorun():
    set_autorun(not is_enabled)
