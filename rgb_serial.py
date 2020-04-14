from time import sleep
from dataclasses import dataclass
from typing import Mapping, ClassVar, List, Optional

import serial
from serial.tools import list_ports

from hardware_monitor import SystemInfo, Sensor


arduino_id = None

RAW_MIN = 0
RAW_MAX = 255


@dataclass
class SensorSpec:
    device: str
    filters: Mapping[str, str]
    min: float = 0.0
    max: float = 100.0

    sensor: Sensor = None

    system_info: ClassVar[SystemInfo] = None

    def __post_init__(self):
        if self.__class__.system_info is None:
            self.__class__.system_info = SystemInfo()
        for sensor in getattr(self.__class__.system_info, self.device).sensors:
            for f_attr, f_val in self.filters.items():
                if getattr(sensor, f_attr) != f_val:  # if any filter fails, break loop
                    break
            else:  # didn't break loop, so all filters matched for sensor
                self.sensor = sensor
                break
        else:
            raise OSError(f'Sensor not found (device: {self.device}, filters: {str(self.filters)})')

    @property
    def value(self):
        return self.sensor.value

    @property
    def raw_value(self):
        normalized_value = (self.value - self.min) / (self.max - self.min)
        return int(max(RAW_MIN, min(RAW_MAX, (RAW_MIN + normalized_value * (RAW_MAX - RAW_MIN)))))


@dataclass
class RingLightSpec:
    id: int
    name: str
    temp_sensor: SensorSpec
    load_sensor: SensorSpec
    fan_sensor: SensorSpec

    def prepare_command(self):
        print(f"Preparing command for ring #{self.id} \"{self.name}\" -> "
              f"Temp: {self.temp_sensor.value:.2f}°C, "
              f"Load: {self.load_sensor.value:.2f}%, "
              f"Fan: {self.fan_sensor.value:.2f}%")
        command = f'U {self.id} {self.temp_sensor.raw_value} {self.load_sensor.raw_value} {self.fan_sensor.raw_value}\n'
        return command


rings: List[RingLightSpec] = []
ser: Optional[serial.Serial] = None


def setup_serial():
    global ser

    arduino_list = serial.tools.list_ports.grep(arduino_id)
    for device in arduino_list:
        arduino_port = device.device
        break
    else:
        raise ConnectionError(f'Arduino serial port not found for specified VID:CID = {arduino_id}')

    serial_timeout = 3

    ser = serial.Serial(arduino_port, 115200, timeout=serial_timeout)
    print('Connected to serial port, waiting for arduino to reset')
    sleep(4)  # Wait for arduino reset on serial connection


def read_serial(until=serial.LF):
    if until is None:
        buffer = ser.read_all()
    else:
        buffer = ser.read_until(terminator=until)
    return buffer.decode().strip()


def print_serial(*args, **kwargs):  # TODO: Implement logging
    buffer = read_serial(*args, **kwargs)
    if buffer:
        print(f'Received: {buffer}')


def flush_serial():
    if ser.in_waiting:
        print_serial(until=None)
    ser.flush()


def update_loop():
    setup_serial()
    try:
        while True:
            for ring in rings:
                command = ring.prepare_command()
                ser.write(command.encode('UTF-8'))
                sleep(0.5)  # Wait for reply
                flush_serial()
                sleep(0.5)
            print()
    except KeyboardInterrupt:  # TODO: Catch serial errors, attempt reconnect?
        print("Exit!")
        ser.close()
