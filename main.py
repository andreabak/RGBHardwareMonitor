import re
import argparse
import configparser

import rgb_serial


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
    argparser.add_argument('-c', '--config', default='config.ini')
    return argparser.parse_args()


# TODO: Consider implementing a minimal GUI / Tray icon?
def main():
    args = parse_args()
    config = configparser.ConfigParser()
    config.read(args.config)
    rgb_serial.arduino_id = config['RGBHardwareMonitor']['arduino_serial_id']
    rgb_serial.rings = ring_lights_from_cfg(config)
    rgb_serial.update_loop()


if __name__ == '__main__':
    exit(main())
