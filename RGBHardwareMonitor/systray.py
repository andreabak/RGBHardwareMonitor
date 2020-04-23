import time
from threading import Thread, Event

# TODO: Replace import with installable library once done?
from modules.systray.src.systray import SysTrayIcon, CheckBoxMenuOption

from . import quit_event, app_path, autorun


from . import quit_event, app_path


class RGBHardwareMonitorSysTray(SysTrayIcon):
    icons = [app_path(f'resources/icon/icon.f{n}.ico') for n in range(6)]
    icons_index = 0
    animation_interval = 1.0 / len(icons)
    animation_thread = None
    animation_thread_quit = None

        menu_options = menu_options or []
        menu_options += [
            CheckBoxMenuOption('Run at startup',
                               check_hook=lambda: autorun.is_enabled,
                               callback=lambda t: autorun.toggle_autorun()),
        ]

        if on_quit is None:
            on_quit = self._on_quit_default
        super().__init__(self.icons[0], "RGBHardwareMonitor", on_quit=on_quit)
        self.animation_start()

    def shutdown(self):
        self.animation_stop()
        super().shutdown()

    def animation_start(self):
        self.animation_thread = Thread(target=self._animation_loop)
        self.animation_thread_quit = Event()
        self.animation_thread_quit.clear()
        self.animation_thread.start()

    def animation_stop(self):
        self.animation_thread_quit.set()
        self.animation_thread.join(self.animation_interval)

    def _animation_loop(self):
        while not self.animation_thread_quit.is_set():
            self.update(icon=self.icons[self.icons_index])
            self.icons_index += 1
            self.icons_index = self.icons_index % len(self.icons)
            time.sleep(self.animation_interval)

    @staticmethod
    def _on_quit_default(systray):
        quit_event.set()
