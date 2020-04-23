import time
import traceback
from threading import Thread, Event

# TODO: Replace import with installable library once done?
from modules.systray.src.systray import SysTrayIcon, CheckBoxMenuOption, MenuOption

from . import autorun
from . import runtime
from .log import logger, error_popup
from .runtime import quit_event, pause_event, app_path, subprocess_run


class IconAnimation:
    icons = []
    frames_interval = 0.2

    def __init__(self, frame_callback, start_animation=True):
        self.frame_callback = frame_callback

        self.icon_index = 0
        self.thread = None
        self.thread_quit_event = None

        if start_animation:
            self.start()

    def start(self):
        if self.thread is None:
            self.thread = Thread(target=self._animation_loop)
            self.thread_quit_event = Event()
            self.thread_quit_event.clear()
            self.thread.start()
        self._icon_callback()

    def stop(self):
        if self.thread is not None:
            self.thread_quit_event.set()
            self.thread.join(self.frames_interval)
            self.thread = None

    @property
    def current_icon(self):
        return self.icons[self.icon_index]

    def _icon_callback(self):
        self.frame_callback(self.current_icon)

    def _animation_loop(self):
        while not self.thread_quit_event.is_set():
            self._icon_callback()
            self.icon_index += 1
            self.icon_index = self.icon_index % len(self.icons)
            time.sleep(self.frames_interval)

    def __del__(self):
        self.stop()


class IconStaticAnimation(IconAnimation):
    frames_interval = 5

    def _animation_loop(self):
        self._icon_callback()
        # No frame stepping


class RunningIconAnimation(IconAnimation):
    icons = [app_path(f'resources/icon/icon.f{n}.ico') for n in range(6)]


class WaitIconAnimation(IconAnimation):
    icons = [app_path(f'resources/icon_wait/icon_wait.f{n}.ico') for n in range(10)]


class PausedIconStatic(IconStaticAnimation):
    icons = [app_path(f'resources/icon_paused/icon_paused.ico')]


def systray_error_handler(exc):
    logger.error(f'Running failed with exception: {exc}', exc_info=exc)
    error_popup(traceback.format_exc())


class RGBHardwareMonitorSysTray(SysTrayIcon):  # TODO: Instead of inheriting, wrap and expose context manager
    default_animation = RunningIconAnimation

    def __init__(self, menu_options=None, on_quit=None, animation_cls=None, start_animation=False):
        if on_quit is None:
            on_quit = self._on_quit_default

        menu_options = menu_options or []
        menu_options += [
            MenuOption('Edit config',
                       callback=lambda t: subprocess_run(['start', '', runtime.config_path], shell=True)),
            CheckBoxMenuOption('Pause (and disconnect)',
                               check_hook=lambda: pause_event.is_set(),
                               callback=lambda t: pause_event.clear() if pause_event.is_set() else pause_event.set()),
            CheckBoxMenuOption('Run at startup',
                               check_hook=lambda: autorun.is_enabled,
                               callback=lambda t: autorun.toggle_autorun()),
        ]

        animation_cls = animation_cls if animation_cls else self.default_animation

        super().__init__(animation_cls.icons[0], "RGBHardwareMonitor",
                         menu_options=menu_options,
                         on_quit=on_quit,
                         window_class_name="RGBHardwareMonitorTray",
                         error_handler=systray_error_handler)

        self.animation = None
        self.set_animation(animation_cls, start_animation=start_animation)

    def shutdown(self):
        self.animation.stop()
        super().shutdown()

    def set_animation(self, animation_cls, start_animation=True):
        if self.animation is not None:
            self.animation.stop()
        self.animation = animation_cls(self.set_icon, start_animation=start_animation)

    def animation_start(self):
        self.animation.start()

    def animation_stop(self):
        self.animation.stop()

    def set_icon(self, icon):
        self.update(icon=icon)

    @staticmethod
    def _on_quit_default(systray):
        quit_event.set()
