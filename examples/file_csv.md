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
## Settings

`csv_log_tilt_colours` as a minimum this is required. It must be a list, even if only one Tilt is included, i.e. `["simulated"]`

`csv_log_averaging_period` an integer of seconds that decribes over how many data points to average. If set to 0 then the most recently received data for that Tilt will be logged. If set to 30 then the most recent 30 seconds worth of data will be averaged and that single value logged. This must be a number that is <= the log period.

`csv_log_max_kb` an integer of kb for each log file. Note that at present the logs are rolled over such that up to 6 files will be stored per Tilt. WIth multiple Tilt devices on a Pico this may need adjusting. In the future I am looking to automate and remove this option.

`csv_log_temp_unit` a single character string, `C` or `F`, log data in Centigrade or Farenheit

`csv_log_rate` an integer value, used to describe logging irregularly. This confuses and is not really relevant to this provider, I aim to remove this option. If the log_rate were 2 and the log_period were 60 then logging would happen every 30 seconds.

`csv_log_period` an integer of seconds at which to log data

## Output
Two sample excerpts of log files with dummy data are shown below. The first illustrates a file where no beer name nor Original Gravity was specified, in the second both criteria were specified in the congif.json

```
2025-02-18 18:44:56, Red Tilt logger added
2025-02-18 18:45:26, Header: Red Tilt
timestamp, Temperature (°C), Specific Gravity
2025-02-18 18:45:26, 22.00, 1.0242
2025-02-18 18:46:26, 22.30, 1.0235
2025-02-18 18:47:26, 22.40, 1.0236
```

```
2025-02-18 18:44:56, Simulated Tilt: Festbier logger added
2025-02-18 18:45:26, Header: Simulated Tilt for Festbier
timestamp, ABV (%), Apparent Attenuation (%), Temperature (°C), Specific Gravity
2025-02-18 18:45:26, 5.97, 80.79, 22.60, 1.0239
2025-02-18 18:46:26, 6.44, 87.35, 22.20, 1.0204
2025-02-18 18:47:26, 6.46, 87.72, 22.60, 1.0202
```

The first entry in the file identifies the start time of the device. The second entry will occur after the first averaging period has elapsed.

There follows a header line detailing the type of parameter and unit being recorded. 

Subsequent data will be recorded at the logging interval. In the data above a 30 second averaging and 60 second logging interval were used.

## Ammount of data storage

Bear in mind that a Pico and similar microcontrollers typically have limited flash storage. In development there is approximately 480kb free on the Pico, once I have compiled a UF2 this should be increased somewhat, but storage is still limited. 

At present file sizes are specified manually, I plan to implement some automation here, but the following notes are relevant in either case. 

By default the debug log files will consume 120kb (2 files of 60kb each), that leaves 360kb. This should be made configurable in the config.

Allow 200 bytes for the header of a log file. Each data point entry will consume 35 bytes in the case of the smaller (Temp & SG only) or 48 bytes for the more complete (ABV, AA, Temp & SG). Thus approximately 10,500 (compact) or 7,600 (more complete) records will fill the flash. At this point, to prevent the device crashing, the oldest log file will be deleted and a new one written. 

If logging at 1 minute intervals this represents 175 or 126 hours, ~7 days or ~5 days. Obviously changing the logging interval can significantly improve the data sotorage time.

However, if there are 2 Tilts then the log file sizes must be smaller and the number of records that can be rtained on flash will be halved.

Summary; some thought needs to go into memory management if you are storing CSV log files on the Pico. 