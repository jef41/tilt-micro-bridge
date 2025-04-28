1) Hold down the bootsel button on the Pico whilst conencting it to your computer
2) drag and drop thje UF2 file to the Pico - this is like an operating system
3) Using Thonny stop and restart the cxonnection (Ctrl-F2)
4) In Thonny create a file name config.json and populate it as required. Below are two examples as a starting point
5) json is very particular about syntax. After creating your configuration, perhaps use a site like 
https://jsonlint.com to validate the file.
6) Ensure the file is saved to the Pico, then in Thonny issue a reset (Ctrl-D), you should see some information messages pop up then data being received from your configured Tilt devices
7) Once happy witht he configuration the Pico may be plugged in to any USB power - a computer is not necessary
8) FOr calibration it may be easier to plug the device back into your computerand connect to it using Thonny. Use Ctl+D to reset the Pico. THe device will reboot and for the next hour will print out data as it is received from Tilt devices. These values are uncalibrated values as received from the Tilt. 

If you get stuck please raise an issue and I will respond, try to help and improve the documentation.

These are working samples, but you will need to omit or correct parts - the Tilt colours and blanked out (xxx-yyy) bits at least will need to be replaced with values unique to your configuration.

A minimal config.json looks like;

```
{
    "csv_log_tilt_colours": ["blue"],
    "csv_log_period": 120,
    "csv_log_averaging_period": 30
}
```

With this configuration SG and temperature data from a blue Tilt will be saved to the Pico device every 120 seconds, with the saved value being an average value calulated over the most recent 30 seconds. Temperature will be recorded in °C.

A more practical example is show below;

```
{
    "debug_log": [12, 1],

    "ssid": "yyyyy-xxxxx",
    "password": "ssssssssssssss",
    "country_code": "GB",
    
    "gravity_range_min" : 0.980,
    "gravity_range_max" : 1.210,
    "temp_range_min" : 35,
    "temp_range_max" : 120,

    "grainfather_tilt_stream_urls": {
        "red": "https://community.grainfather.com/iot/uuu-vvv/tilt",
        "blue": "https://community.grainfather.com/iot/www-xxx/tilt"
    },
    "grainfather_custom_stream_urls": {
        "orange": "https://community.grainfather.com/iot/yyy-zzz/custom"
    },
    "grainfather_averaging_period": 300,

    "csv_log_tilt_colours": ["blue"],
    "csv_log_temp_unit": "F",
    "csv_log_averaging_period": 0,
    "csv_log_period": 300,

    "red_gravity_offsets": [[1.0016,1.0000], [1.1070,1.1015], [1.0574,1.056]],
    "red_temp_offsets": [ "C", [4.8,5.0], [49.3,50.0] ],
    
    "blue_original_gravity": 1.067,
    "blue_name": "Festbier"
}
```

In this example 

* the debug.log file has been set to a slightly smaller 12kb.
* wifi credentials have been supplied
* 2 Tilt devices will appear in Grainfather equipment (red and blue)
* 1 Tilt device will appear as custom equipoment in Grainfather (orange)
* data sent to Grainfather will be averaged from the most recent 5 minutes of received data
* data from the blue Tilt will also be logged to CSV files on the Pico, at 5 minute log interval. Averaging is disabled, so for each log period the most recent value will be stored. The temperature will be logged in °F.
* the red Tilt has some calibration values that will be applied to SG and a 5°F offset applied to temperature readings
* the blue Tilt is in a brew named Festbier and the original gravity has been noted. Consequently the CSV file will also contain data for ABV and Apparent Attenuation

Note that the difference between Grainfather Tilt or Custom equipment is purely visual - whether or not the Tilt logo appears next to the device. 
