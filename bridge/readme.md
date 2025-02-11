Until I produce a UF2 file to put on the Pico please follow these notes...
1) usin Thonny upload a MicroPython UF2 file to the Pico - this is like an operating system
2) copy the contents of this foler to the Pico
3) the Pico should now have a folder called /lib, /bridge_main_averaging.py & /picoTilt.py
4) create a file name config.json, I suggest using all or part of the sample below. 
5) json is very particular about syntax. After creating your configuratioin, perhaps use a site like 
https://jsonlint.com to validare the file.
6) if you rename picoTilt.py to main.py then the application will run whenever you next power on the Pico, whether or not a computer is present. Once you have finished testing then I suggest you rename the file. When you wnat to perform calibration, plug the device back into your computer using Thonny and connect to it. Use Ctl+D to reset the Pico then use Thonny to run main.py. If you get stuck please raise an issue and I will respond, try to help and improve the codumentation.

this is a working sample, feel free to omit or correct parts.

config.json looks like:
```
{
    "grainfather_tilt_stream_urls": {
        "simulated": "https://community.grainfather.com/iot/xxx-xxx/tilt",
        "blue": "https://community.grainfather.com/iot/xxx-xxx/tilt"
    },
    "grainfather_custom_stream_urls": {
        "simulated": "https://community.grainfather.com/iot/xxx-xxx/custom"
    },
    "grainfather_averaging_period": 300,
    "ssid": "yyyyy-xxxxx",
    "password": "ssssssssssssss",
    "country_code": "GB",
    "simulated_gravity_offsets" : [[1.005,1.000], [1.090,1.100], [1.060,1.060]],
    "gravity_range_min" : 0.980,
    "gravity_range_max" : 1.210,
    "temp_range_min" : 0,
    "temp_range_max" : 185
}
```

