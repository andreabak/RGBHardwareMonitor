<!-- TODO: Rewrite README -->

# DISCLAIMER
This project is currently a Work-in-Progress. Structure, specifications and code can radically change at any time.


# RGBHardwareMonitor

The _hardware_monitor_ module will allow you to get in Python information about your hardware, and work with it. The *rgb_serial.py* script allows you to build custom illumination systems based on Adafruit NeoPixels strips and Arduino. This script will get the GPU's temperature and load, and will send to the Arduino a lighting command based on the obtained values.

**SystemInfo class:**

**Attributes:**

* **name** *string*
* **os_name** *string*
* **os_architecture** *string*
* **mainboard** *Device*
* **superio** *Device*
* **cpu** *Device*
* **ram** *Device* 
* **hdd** *Device*
* **gpu** *Device*

*Any device of the SystemInfo class can be a list of Device objects. e.g. If you have 2 HDDs*


**Device class:**

**Attributes:**

* **name** *string*
* **identifier** *string*
* **hardware_type** *string*
* **parent** *string*
* **sensors** *list(Sensor)*


**Sensor class:**

**Attributes:**

* **name** *string*
* **identifier** *string*
* **sensor_type** *string*
* **parent** *string*
* **index** *int*

**Properties:**

* **value** *float*
* **min** *float*
* **max** *float*


## Requeriments
* [OpenHardwareMonitor](http://openhardwaremonitor.org/) running
* Python (*>=3.7*)
* Pyserial (*>=3.0*)
* WMI python module (*>=1.4*)
* Pywin32 (*>=220*)


## Custom Illumination System

The script will search for the Arduino port automatic, for that, you must change the *VID:PID* value for the value of your Arduino. 

The Arduino's code:
* Use serial communication with the Python script
* Use a little protocol based on integers.
* Implemented effects:
  - *RingLights*: shows a rotating/flashing ring displaying temperature, load and fan speed;
  - ... more to come (feel free to send pull requests). 


## Issues

* Open Hardware Monitor information is sometimes not descriptive of the sensor they represent.


## Licence

Released under GNUv3 License.
