from time import sleep
from dataclasses import dataclass
from typing import Mapping

import serial
from serial.tools import list_ports

from hardware_monitor import SystemInfo, Sensor

# You must change this for your Arduino VID:PID!!
ARDUINO_ID = "2341:8036"


RAW_MIN = 0
RAW_MAX = 255
system = SystemInfo()


@dataclass
class SensorSpec:
    device: str
    filters: Mapping[str, str]
    min: float = 0.0
    max: float = 100.0

    sensor: Sensor = None

    def __post_init__(self):
        for sensor in getattr(system, self.device).sensors:
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
        command = f'1 {self.id} {self.temp_sensor.raw_value} {self.load_sensor.raw_value} {self.fan_sensor.raw_value}\n'
        return command


ring1 = RingLightSpec(
    id=1, name='CPU',
    temp_sensor=SensorSpec('cpu', dict(sensor_type='Temperature'), min=35.0, max=95.0),
    load_sensor=SensorSpec('cpu', dict(sensor_type='Load', name='CPU Total')),
    fan_sensor=SensorSpec('superio', dict(sensor_type='Control', name='Fan Control #2'))
)
ring2 = RingLightSpec(
    id=2, name='GPU',
    temp_sensor=SensorSpec('gpu', dict(sensor_type='Temperature'), min=35.0, max=85.0),
    load_sensor=SensorSpec('gpu', dict(sensor_type='Load', name='GPU Core')),
    fan_sensor=SensorSpec('gpu', dict(sensor_type='Control', name='GPU Fan'))
)

# Get the Arduino port
arduino_list = serial.tools.list_ports.grep(ARDUINO_ID)

for device in arduino_list:
    arduino_port = device.device
    break
else:
    raise ConnectionError(f'Arduino serial port not found for specified VID:CID = {ARDUINO_ID}')

ser = serial.Serial(arduino_port, 115200)


def main():
    try:
        while True:
            command = ring1.prepare_command()
            ser.write(command.encode('UTF-8'))
            print(f'Received: {ser.read_until().decode().strip()}\n')
            sleep(2)
    except KeyboardInterrupt:
        print("Exit!")
        ser.close()


if __name__ == '__main__':
    main()
