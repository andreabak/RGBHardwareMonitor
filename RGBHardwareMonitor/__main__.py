import sys
import re
import argparse
import configparser
import traceback
from time import sleep
from typing import Optional

from RGBHardwareMonitor.hardware_monitor import HMNoSensorsError, HMSensorNotFound
from . import runtime
from . import rgb_serial
from . import hardware_monitor
from . import autorun
from .log import logger, log_stream_handler, setup_file_logging, error_popup
from .runtime import quit_event, pause_event, is_admin
from .systray import RGBHardwareMonitorSysTray, WaitIconAnimation, PausedIconStatic


def sensor_spec_from_cfg(config, section_name, subsection_name):
    sensorspec_cfg = config[f'{section_name}.{subsection_name}']
    sensorspec_device = sensorspec_cfg['device']
    sensorspec_min = sensorspec_cfg.getfloat('range_min', rgb_serial.SensorSpec.min)
    sensorspec_max = sensorspec_cfg.getfloat('range_max', rgb_serial.SensorSpec.max)
    sensorspec_filters = []
    for key in sensorspec_cfg:
        match = re.fullmatch(r'filters_(?P<filter_name>.+)', key, re.I)
        if match:
            sensorspec_filters.append((match.group('filter_name'), sensorspec_cfg[key]))
    return rgb_serial.SensorSpec(
        device=sensorspec_device,
        filters=dict(sensorspec_filters),
        min=sensorspec_min, max=sensorspec_max,
    )


def ring_lights_from_cfg(config):
    ringlights = []
    for section_name in config.sections():
        match = re.fullmatch(r'RingLight(?P<ring_id>\d+)', section_name, re.I)
        if match:
            ring_cfg = config[section_name]
            ring_id = int(match.group('ring_id'))
            ring_name = ring_cfg['name']
            ring_temp_sensor = sensor_spec_from_cfg(config, section_name, 'TempSensor')
            ring_load_sensor = sensor_spec_from_cfg(config, section_name, 'LoadSensor')
            ring_fan_sensor = sensor_spec_from_cfg(config, section_name, 'FanSensor')
            ringlights.append(rgb_serial.RingLightSpec(
                id=ring_id, name=ring_name,
                temp_sensor=ring_temp_sensor, load_sensor=ring_load_sensor, fan_sensor=ring_fan_sensor,
            ))
    return ringlights


def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-i', '--system-info', action='store_true',
                           help='Print OpenHardwareMonitor system info and exit')
    argparser.add_argument('--autorun', choices=['enable', 'disable'],
                           help='Set autorun and exit')
    argparser.add_argument('-c', '--config', default='config.ini',
                           help='Specify custom path for configuration')
    log_choices = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']
    argparser.add_argument('--log-file', default=None,
                           help='Specify custom path for log file')
    argparser.add_argument('-l', '--log-level', choices=log_choices, default=None,
                           help='Log file level')
    argparser.add_argument('-v', '--verbosity', choices=log_choices, default=None,
                           help='Console log level')
    return argparser.parse_args()


# TODO: More systray features: edit colors / runtime params (autosave config), open log?
# TODO: Runtime colors set from python to arduino (maybe even persist on flash/eeprom)?
def real_main():
    quit_event.clear()
    pause_event.clear()

    args = parse_args()

    if args.autorun:
        if not is_admin():
            raise PermissionError('Must run with elevated privileges to set autorun')
        autorun.set_autorun(args.autorun == 'enable')
        return 0
    autorun.check_autorun()

    runtime.config_path = args.config
    runtime.config = configparser.ConfigParser()
    runtime.config.read(runtime.config_path)
    # TODO: Implement "close OpenHardwareMonitor on exit" option in config

    hardware_monitor.openhardwaremonitor_exe_path = runtime.config['RGBHardwareMonitor']['openhardwaremonitor_path']

    if args.system_info:
        hardware_monitor.SystemInfo().print_info()
        return 0

    verbosity = args.verbosity or runtime.config['RGBHardwareMonitor'].get('verbosity', 'INFO')
    log_stream_handler.setLevel(verbosity)
    log_file = args.log_file or runtime.config['RGBHardwareMonitor'].get('log_file')
    log_level = args.log_level or runtime.config['RGBHardwareMonitor'].get('log_level', 'INFO')
    if log_file:
        setup_file_logging(log_file, log_level)

    rgb_serial.arduino_id = runtime.config['RGBHardwareMonitor']['arduino_serial_id']

    with RGBHardwareMonitorSysTray(animation_cls=WaitIconAnimation, start_animation=True) as systray:
        init_exc: Optional[Exception] = None
        for _ in range(12):
            try:
                rgb_serial.rings = ring_lights_from_cfg(runtime.config)
            except (HMNoSensorsError, HMSensorNotFound) as exc:
                init_exc = exc
                sleeptime: float = 5.0
                logger.debug(f'Got no sensors found error. OpenHardwareMonitor initializing? Retrying in {sleeptime}')
                sleep(sleeptime)
            except Exception as exc:
                init_exc = exc
                raise
            else:
                init_exc = None
                break
        else:
            raise RuntimeError(f'Initialization failed: {init_exc}') from init_exc
        while not quit_event.is_set():
            if not pause_event.is_set():
                rgb_serial.update_loop(systray=systray)
            else:
                systray.set_animation(PausedIconStatic)
                sleep(1)

    return 0


def main():
    try:
        sys.exit(real_main())
    except Exception as exc:
        logger.critical(f'Running failed with exception: {exc}', exc_info=exc)
        error_popup(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
