import serial
import serial.tools.list_ports
from time import sleep

import hardware_monitor


# You must change this for your Arduino VID:PID!!
ARDUINO_ID = "2341:8036"

NORMAL = "0"
THEATER_CHASE = "1"
RAINBOW = "2"
RAINBOW_CYCLE = "3"
BREATHING = "4"

RED = "125 0 0"
ELECTRIC_BLUE = "0 125 125"


def select_mode(load):
    if(load > 30):
        return THEATER_CHASE
    else:
        return BREATHING


def select_color(temp):
    if(temp > 50):
        return RED
    else:
        return ELECTRIC_BLUE

# Get the GPU's temperature sensor
system = hardware_monitor.SystemInfo()
graphic_temp_sensor = None
graphic_load_sensor = None

for sensor in system.gpu.sensors:
    if sensor.sensor_type == "Temperature":
        graphic_temp_sensor = sensor
    if sensor.sensor_type == "Load" and sensor.name == "GPU Core":
        graphic_load_sensor = sensor

# Get the Arduino port
arduino_list = serial.tools.list_ports.grep(ARDUINO_ID)

for device in arduino_list:
    arduino_port = device.device

ser = serial.Serial(arduino_port, 115200)

try:
    n = 0
    m_load = 0
    m_temp = 0
    command = "0 0 0 0"
    ser.write(command.encode('UTF-8'))
    sleep(2)
    while True:
        load = graphic_load_sensor.value
        m_load += load
        temp = graphic_temp_sensor.value
        m_temp += temp
        n += 1
        print("Load:", load, "%", "Temp:", temp, "Cº")
        command = select_mode(load) + ' ' + select_color(temp)
        ser.write(command.encode('UTF-8'))
        ser.read()
except KeyboardInterrupt:
    print("Medium Load:", m_load/n, "%", "Medium Temp:", m_temp/n, "Cº")
    ser.write("0".encode('UTF-8'))
    print("Exit!")
    ser.close()
