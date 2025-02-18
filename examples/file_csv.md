# Settings Specific to the CSV Log File provider

A config.json example looks like:
```
{
    "csv_log_tilt_colours": ["simulated", "red"],
    "csv_log_averaging_period": 30,
    "csv_log_max_kb": 60,
    "csv_log_temp_unit": "C",
    "csv_log_rate": 1,
    "csv_log_period": 60
}
```

`csv_log_tilt_colours` as a minimum this is required. It must be a list, even if only one Tilt is included, i.e. `["simulated"]`

`csv_log_averaging_period` an integer of seconds that decribes over how many data points to average. If set to 0 then the most recently received data for that Tilt will be logged. If set to 30 then the most recent 30 seconds worth of data will be averaged and that single value logged. This must be a number that is <= the log period.

`csv_log_max_kb` an integer of kb for each log file. Note that at present the logs are rolled over such that up to 6 files will be stored per Tilt. WIth multiple Tilt devices on a Pico this may need adjusting. In the future I am looking to automate and remove this option.

`csv_log_temp_unit` a single character string, `C` or `F`, log data in Centigrade or Farenheit

`csv_log_rate` an integer value, used to describe logging irregularly. This confuses and is not really relevant to this provider, I aim to remove this option. If the log_rate were 2 and the log_period were 60 then logging would happen every 30 seconds.

`csv_log_period` an integer of seconds at which to log data