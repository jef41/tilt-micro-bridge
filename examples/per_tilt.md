# Settings Specific to a single Tilt device

There are a number of settings that may pertain to a single Tilt device, in the example below the settings are all applied to a Red Tilt:

A config.json example looks like:
```
{
    "red_gravity_offsets" : [[1.005,1.000], [1.090,1.100], [1.060,1.060]],
    "red_original_gravity": 1.067,
    "red_temp_offset": 5,
    "red_name": "Festbier"
}
```

All of these configurations are optional, they should either be present with a value or not present at all.

`{colour}_gravity_offsets` are list pairs of `[raw values, calibration points]`, described in more detail [in the Calibration section](/README.md#Calibration)

`{colour}original_gravity` expressed as Specific Gravity points, if this is present ABV and Apparent Attenuation will be calculated for each reading. These additional calculated readings will be logged by providers where relevant (currently only in CSV log files).

`{colour}_temp_offset` Temperatures are in °Farenheit, described in more detail [in the Calibration section](/README.md#Calibration)

`{colour}_name` A string expressing the name of your brew. If included this will be used by providers as appropriate. Currently this is only used by CSV log files where the beer name will be logged in the file and the log file will be `{colour}_name.log` , `Festbier.log` in this example.