import time
from dataclasses import dataclass, InitVar
from typing import Optional, List, Union
from pathlib import Path

from wmi import WMI

from .log import logger
from .runtime import run_as_admin


openhardwaremonitor_exe_path: Optional[str] = None


class HardwareMonitorError(Exception):
    """Base class for hardware monitor exceptions"""


class HMExecError(HardwareMonitorError):
    """Exception class for process execution errors"""


class HMWMIError(HardwareMonitorError):
    """Exception class for WMI related errors"""


class HMWMINamespaceError(HMWMIError):
    """Exception class for WMI namespace not found errors"""


class HMNoDeviceError(HardwareMonitorError):
    """Exception class for no device returned from WMI query"""


class HMNoSensorsError(HardwareMonitorError):
    """Exception class for no sensors returned from WMI query"""


class HMSensorNotFound(HardwareMonitorError):
    """Exception class for sensor not found from WMI query"""


# TODO: Catch WMI errors (like disconnection), check wmi lib


def _wmi_get_ohm():
    """Returns OpenHardwareMonitor's WMI object"""
    return WMI(namespace=r"root\OpenHardwareMonitor")


def is_openhardwaremonitor_running():
    return bool(_wmi_get_ohm().Hardware())


def openhardwaremonitor_start():
    if openhardwaremonitor_exe_path is None:
        raise HMExecError('Cannot run OpenHardwareMonitor: executable path not specified')
    run_dir = Path(openhardwaremonitor_exe_path).parent
    logger.debug('Starting OpenHardwareMonitor...')
    run_as_admin(openhardwaremonitor_exe_path, run_dir=str(run_dir))
    retry = 60
    while retry > 0:
        time.sleep(1)
        if is_openhardwaremonitor_running():
            logger.debug('OpenHardwareMonitor started')
            break
        retry -= 1
    else:
        raise HMWMIError('Failed starting OpenHardwareMonitor: WMI timed out')


@dataclass
class Sensor:
    """
    Wrapper class for WMI sensor
    """

    name: str
    """Name of the sensor. e.g. GPU CORE"""

    identifier: str
    """Identifier of the sensor. e.g. /nvidiagpu/0/load"""

    sensor_type: str
    """Type of the sensor.\n
    **Types:**\n
    * Voltage(V)\n
    * Clock(MHz)\n
    * Temperature(C)\n
    * Load(%)\n
    * Fan(RPM)\n
    * Flow(L/h)\n
    * Control(%)\n
    * Level(%)"""

    parent: str
    """Parent device of the sensor. e.g. /nvidiagpu/0/"""

    index: int
    """Index in the sensors array obtained by the WMI query"""

    @classmethod
    def from_wmi(cls, sensor):
        """Constructor from WMI Sensor"""
        return cls(
            name=sensor.Name,
            identifier=sensor.Identifier,
            sensor_type=sensor.SensorType,
            parent=sensor.Parent,
            index=sensor.Index
        )

    @property
    def wmi_sensor(self):
        """Get wrapped WMI Sensor"""
        try:
            return _wmi_get_ohm().Sensor(Identifier=self.identifier)[0]
        except IndexError as exc:
            raise HMSensorNotFound('Sensor not found') from exc

    @property
    def value(self):
        """Get sensor's current value"""
        return self.wmi_sensor.Value

    @property
    def min(self):
        """Get sensor's minimum value"""
        return self.wmi_sensor.Min

    @property
    def max(self):
        """Get sensor's maximum value"""
        return self.wmi_sensor.Max


@dataclass
class Device:
    """
    Wrapper class for WMI hardware device
    """

    name: str
    """Name of the device. e.g. Nvidia GTX970"""

    identifier: str
    """Identifier of the device. e.g. /nvidiagpu/0"""

    hardware_type: str
    """HardwareType of the device.\n
    **Types:**\n
    * Mainboard\n
    * SuperIO\n
    * CPU\n
    * GpuNvidia\n
    * GpuAti\n
    * TBalancer\n
    * Heatmaster\n
    * HDD\n
    * RAM\n\n
    *These are the types that you can find in the
    [official documentation](http://goo.gl/3qSJfo)"""

    parent: str
    """Parent of the device (if have). e.g. /mainboard/"""

    sensors: Optional[List[Sensor]] = None
    """List of Sensors attached to the device"""

    def __post_init__(self):
        """Constructor"""
        self.sensors = list()
        for sensor in _wmi_get_ohm().Sensor():
            if sensor.Parent == self.identifier:
                self.sensors.append(Sensor.from_wmi(sensor))
        self.sensors.sort(key=lambda s: s.identifier)

    @classmethod
    def from_wmi(cls, device):
        """Constructor from WMI Device"""
        return cls(
            name=device.Name,
            identifier=device.Identifier,
            hardware_type=device.HardwareType,
            parent=device.Parent,
        )

    def get_info(self):
        """Function for get device info with a correct format"""
        info_str = f'\n{self.hardware_type}\n' \
                   f'-------------------\n' \
                   f'\t* Name: {self.name}\n' \
                   f'\t* Identifier: {self.identifier}\n'
        if self.parent:
            info_str += f'\t* Parent: {self.parent}\n'
        if self.sensors:
            info_str += '\t* Sensors:\n' \
                        '\t-------------\n' \
                        f'\t\t  {"name":22}\t{"identifier":27}\t{"sensor_type":11}\t{"value"}\n' \
                      + '\n'.join(f'\t\t- {sens.name:22}\t{sens.identifier:27}\t{sens.sensor_type:11}\t{sens.value:.2f}'
                                  for sens in self.sensors)
        info_str += '\n'

        return info_str


@dataclass
class SystemInfo:
    """Class that represent all the PC's hardware. Also have information about
    the OS (like name and architecture)"""

    name: str = ""
    """Computer name. e.g. aspire-one-5755g"""

    os_name: str = ""
    """OS name. e.g. Windows 10"""

    os_architecture: str = ""
    """OS architecture. e.g. x86_64"""

    mainboard: Optional[Union[Device, List[Device]]] = None
    """Mainboard of the computer"""

    superio: Optional[Union[Device, List[Device]]] = None
    """SuperIO controller(s) of the computer"""

    cpu: Optional[Union[Device, List[Device]]] = None
    """Processor(s) of the computer"""

    ram: Optional[Union[Device, List[Device]]] = None
    """RAM module(s) of the computer"""

    hdd: Optional[Union[Device, List[Device]]] = None
    """HardDisk Drives of the computer"""

    gpu: Optional[Union[Device, List[Device]]] = None
    """Graphic Processor of the computer (Nvidia or AMD)"""

    start_ohm: InitVar[bool] = False
    """Init var to start OpenHardwareMonitor"""

    def __post_init__(self, start_ohm):
        """Constructor"""
        wmi_ohm = _wmi_get_ohm()
        if not is_openhardwaremonitor_running():
            if not start_ohm:
                raise HMWMINamespaceError('Failed while querying OpenHardwareMonitor WMI namespace. OHM not running?')
            openhardwaremonitor_start()
            wmi_ohm = _wmi_get_ohm()
        self.name = WMI().Win32_ComputerSystem()[0].Name
        self.os_name = WMI().Win32_OperatingSystem()[0].Caption
        self.os_architecture = WMI().Win32_OperatingSystem()[0].OSArchitecture
        self.mainboard = self.add_device(wmi_ohm.Hardware(HardwareType="Mainboard"))
        self.superio = self.add_device(wmi_ohm.Hardware(HardwareType="SuperIO"))
        self.cpu = self.add_device(wmi_ohm.Hardware(HardwareType="CPU"))
        self.ram = self.add_device(wmi_ohm.Hardware(HardwareType="RAM"))
        self.hdd = self.add_device(wmi_ohm.Hardware(HardwareType="HDD"))
        self.gpu = self.add_device(wmi_ohm.Hardware(HardwareType="GpuNvidia"))
        if self.gpu is None:
            self.gpu = self.add_device(wmi_ohm.Hardware(HardwareType="GpuAti"))

    @staticmethod
    def add_device(device_query):
        """Function for get the Device Object if its only a device, or a list with
        the devices in case of have more of one of the same type.\n
        Returns None if don't have any device of that type"""
        if len(device_query) > 1:
            device_list = list()
            for element in device_query:
                device = Device.from_wmi(element)
                device_list.append(device)

        elif len(device_query) == 1:
            device_list = Device.from_wmi(device_query[0])

        else:
            device_list = None

        return device_list

    def formatted_devices(self):
        info_strs = []
        for device_list in (self.mainboard, self.superio, self.cpu, self.ram, self.gpu, self.hdd):
            if isinstance(device_list, list):
                for device in device_list:
                    info_strs.append(device.get_info())
            else:
                info_strs.append(device_list.get_info())
        return ''.join(info_strs)

    def formatted_info(self):
        return f'{self.name}\n' \
               f'---------------\n' \
               f'OS: {self.os_name} {self.os_architecture}\n\n' \
               + self.formatted_devices()

    def print_devices(self):
        logger.info(self.formatted_devices())

    def print_info(self):
        logger.info(self.formatted_info())


if __name__ == '__main__':
    logger.setLevel('INFO')
    SystemInfo().print_info()
