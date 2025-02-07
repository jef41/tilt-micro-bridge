# Grainfather Provider
features specific to the Grainfather provider

A config.json example looks like:
```
{
    "grainfather_tilt_stream_urls": {
        "simulated": "https://community.grainfather.com/iot/xxx-xxx/tilt",
        "blue": "https://community.grainfather.com/iot/xxx-xxx/tilt"
    },
    "grainfather_custom_stream_urls": {
        "simulated": "https://community.grainfather.com/iot/xxx-xxx/custom"
    },
    "grainfather_averaging_period" = 300
    "grainfather_temp_unit": "C",
}
```

## grainfather_tilt_stream_urls

requires a ```"colour" : "url"```

the colour of Tilt and the URL from Grainfather interface

once configured tilt-micro-bridge will send data every 15 minutes, the device will appear under Equipment as a Tilt

<img src="../misc/gf_tilt.png" alt="Tilt image form Grainfather website" height="90px">

## grainfather_custom_stream_urls

requires a ```"colour" : "url"```

the colour of Tilt and the URL from Grainfather interface

once configured tilt-micro-bridge will send data every 15 minutes, the device will appear under Equipment as a Custom Fermentation Device

<img src="../misc/gf_custom.png" alt="Custom fermentation device image from Grainfather" height="90px">

## grainfather_averaging_period

An integer of seconds over which to average results. 

If `grainfather_averaging_period` is present it will override `averaging_period`, if that option is set.

If `grainfather_averaging_period` is not present then the value for `averaging_period` will be used here.

If set to 0 no averaging will take place, every 15 mintues the most recent reading from the Tilt will be uploaded. 

If n > 0 and < 15 minutes (900 secs), at each 15 minute data upload interval, the most recent n seconds of data will be averaged, and this single averaged value uploaded.

If n > 15 minutes then at upload interval the most recent 15 minutes worth of data will be uploaded.

Having no averaging may create more noise in the chart.

In testing the Pico was capable of storing 21,000 records. 8 Tilts transmitting every second would result in 7,200 records in 15 minutes, so theoretically an averaging interval of 15 minutes for 8 Tilts would work, let me know, I have only done real world tests with 1 Tilt.

## grainfather_temp_unit

A single character, C or F, for Centigrade or Farenheit. This need not be specified, by default the tilt-micro-bridge will upload in Farenheit, Grainfather will convert the units to display in your chosen units on their platform.
