from time import sleep
from dataclasses import dataclass
from typing import Mapping, ClassVar, List, Optional, Union

import serial
from serial import SerialException
from serial.tools import list_ports

from .log import logger
from .runtime import quit_event, pause_event
from .hardware_monitor import SystemInfo, Sensor, HMNoSensorsError, HMSensorNotFound
from .systray import WaitIconAnimation, RunningIconAnimation


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
            self.__class__.system_info = SystemInfo(start_ohm=True)
        sensors = getattr(self.__class__.system_info, self.device).sensors
        if not sensors:
            raise HMNoSensorsError('No sensors available from hardware monitor')
        for sensor in sensors:
            for f_attr, f_val in self.filters.items():
                if getattr(sensor, f_attr) != f_val:  # if any filter fails, break loop
                    break
            else:  # didn't break loop, so all filters matched for sensor
                self.sensor = sensor
                break
        else:
            raise HMSensorNotFound(f'Sensor not found (device: {self.device}, filters: {str(self.filters)})')

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
        logger.debug(f"Preparing command for ring #{self.id} \"{self.name}\" -> "
                     f"Temp: {self.temp_sensor.value:.2f}°C, "
                     f"Load: {self.load_sensor.value:.2f}%, "
                     f"Fan: {self.fan_sensor.value:.2f}%")
        command = f'U {self.id} {self.temp_sensor.raw_value} {self.load_sensor.raw_value} {self.fan_sensor.raw_value}\n'
        return command


# TODO: Refactor module into classes, maybe rename it too
rings: List[RingLightSpec] = []
ser: Optional[serial.Serial] = None
serial_timeout = 3


def close_serial():
    global ser

    if ser is not None:
        ser.close()
    ser = None


def read_serial(until=serial.LF):
    if until is None:
        buffer = ser.read_all()
    else:
        buffer = ser.read_until(terminator=until)
    return buffer.decode(errors='replace').strip()


def log_serial(*args, **kwargs):
    buffer = read_serial(*args, **kwargs)
    if buffer:
        logger.debug(f'Received: {buffer}')


def flush_serial():
    if ser.in_waiting:
        log_serial(until=None)
    ser.flush()


def command_and_response(command: Union[str, bytes], ensure_line_end=True, flush=True):
    if isinstance(command, str):
        command = command.encode('utf8')
    if ensure_line_end and command[-1] != b'\n':
        command += b'\n'
    ser.write(command)
    sleep(0.25)  # Wait for data
    response = read_serial()
    if flush:
        sleep(0.25)  # Wait for data
        flush_serial()
    return response


def setup_serial():
    def attempt_serial_handshake(arduino_port):
        global ser, serial_timeout
        close_serial()
        ser = serial.Serial(arduino_port, 115200, timeout=serial_timeout)
        logger.debug(f'Connected to serial port {ser.name}, waiting for arduino to reset')
        sleep(4)  # Wait for arduino reset on serial connection
        logger.debug('Attempting handshake')
        response = command_and_response('H')
        return response == 'EHLO RGBHardwareMonitor'

    arduino_list = serial.tools.list_ports.grep(arduino_id)
    for device in arduino_list:
        if attempt_serial_handshake(device.device):
            logger.debug('Succesfully connected to arduino')
            break
        else:
            logger.debug('Handshake failed')
    else:
        close_serial()
        raise ConnectionError(f'No arduino recognized for serial ports with specified VID:PID = {arduino_id}')


def update_loop(systray=None):
    while True:
        if systray is not None:
            systray.set_animation(WaitIconAnimation, start_animation=True)
        try:
            setup_serial()
            if systray is not None:
                systray.set_animation(RunningIconAnimation, start_animation=True)
            while True:
                for ring in rings:
                    if quit_event.is_set() or pause_event.is_set():
                        return
                    command = ring.prepare_command()
                    command_and_response(command)
                    sleep(1)
        except SerialException as exc:
            logger.warning(f'Serial exception: {str(exc)}', exc_info=True)
        except KeyboardInterrupt:
            logger.debug("Exit!")
        finally:
            close_serial()
