# RGBHardwareMonitor

The SystemInfo module will allow you to get in Python information about your hardware, and work with it. The *TempLED.py* script allows you to build custom illumination systems based on Adafruit NeoPixels strips and Arduino. This script will get the GPU's temperature and load, and will send to the Arduino a lighting command based on the obtained values.

**SystemInfo class:**

**Attributes:**

* **Name** *string*
* **OSName** *string*
* **OSArchitecture** *string*
* **Mainboard** *Device*
* **CPU** *Device*
* **RAM** *Device* 
* **HDD** *Device*
* **GPU** *Device*

*Any device of the SystemInfo class can be a list of Device objects. e.g. If you have 2 HDDs*


**Device class:**

**Attributes:**

* **Name** *string*
* **Identifier** *string*
* **HardwareType** *string*
* **Parent** *string*
* **Sensors** *list(Sensor)*


**Sensor class:**

**Attributes:**

* **Name** *string*
* **Identifier** *string*
* **SensorType** *string*
* **Parent** *string*
* **Index** *int*

**Methods:**

* **getValue(*void*)** *float*
* **getMin(*void*)** *float*
* **getMax(*void*)** *float*

*The Sensor class have attributes for get the values because you must do the WMI query to get the updated value*


## Requeriments
* [OpenHardwareMonitor](http://openhardwaremonitor.org/) running
* Python 3
* Pyserial (*>=3.0*)
* WMI python module (*>=1.4*)
* Pywin32 (*>=220*)

## Custom Illumination System

The script will search for the Arduino port automatic, for that, you must change the *VID:PID* value for the value of your Arduino. 

The Arduino's code:
* Use serial communication with the Python script
* Use a little protocol based on integers.
* Have 5 lighting effects: Permanent, Theatre Chase, Rainbow, Rainbow Circle and Breathing.
* It's ready for any-long NeoPixels strip (You must change the *numLEDS* constant).

## Issues

* Open Hardware Monitor don't get the temperature information of the most recents CPU families.

## Licence

Released under GNUv3 License.
