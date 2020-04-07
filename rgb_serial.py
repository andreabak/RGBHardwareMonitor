from time import sleep

import serial
from serial.tools import list_ports

from hardware_monitor import SystemInfo


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
    if load > 30:
        return THEATER_CHASE
    else:
        return BREATHING


def select_color(temp):
    if temp > 50:
        return RED
    else:
        return ELECTRIC_BLUE


# Get the GPU's temperature sensor
system = SystemInfo()
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
    break
else:
    raise ConnectionError(f'Arduino serial port not found for specified VID:CID = {ARDUINO_ID}')

ser = serial.Serial(arduino_port, 115200)

n = 0
cum_load = 0
cum_temp = 0
command = "0 0 0 0"
ser.write(command.encode('UTF-8'))
sleep(2)
try:
    while True:
        current_load = graphic_load_sensor.value
        cum_load += current_load
        current_temp = graphic_temp_sensor.value
        cum_temp += current_temp
        n += 1
        print("Load:", current_load, "%", "Temp:", current_temp, "Cº")
        command = select_mode(current_load) + ' ' + select_color(current_temp)
        ser.write(command.encode('UTF-8'))
        ser.read()
except KeyboardInterrupt:
    print("Medium Load:", cum_load / n, "%", "Medium Temp:", cum_temp / n, "Cº")
    ser.write("0".encode('UTF-8'))
    print("Exit!")
    ser.close()
