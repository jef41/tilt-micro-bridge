# Minimum & Maximum values
We can automatically discard messages form a Tilt where the data seems to be invalid

A config.json example looks like:
```
{
    "gravity_range_min" : 0.980,
    "gravity_range_max" : 1.210,
    "temp_range_min" : 32,
    "temp_range_max" : 120
}
```

Gravity ranges are in SG points.

Temperatures are in °Farenheit

It is suggested that you allow a few extra points outside of your anticipated ranges to allow for any calibration offset.