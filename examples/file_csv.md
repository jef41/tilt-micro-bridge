# Settings Specific to the CSV Log File provider

A minimal log to CSV config.json looks like:
```
{
    "csv_log_tilt_colours": ["red"]
}
```

A more complete config.json example looks like:
```
{
    "csv_log_tilt_colours": ["simulated", "red"],
    "csv_log_temp_unit": "C",
    "csv_log_period": 60,
    "csv_log_averaging_period": 30,
    "csv_bkp_count": 4
}
```
## Settings

`csv_log_tilt_colours` as a minimum this is required. It must be a list, even if only one Tilt is included, i.e. `["simulated"]`


<!--`csv_log_max_kb` an integer of kb for each log file. Note that at present the logs are rolled over such that up to 6 files will be stored per Tilt. WIth multiple Tilt devices on a Pico this may need adjusting. In the future I am looking to automate and remove this option.-->

`csv_log_temp_unit` a single character string, `C` or `F`, log data in Centigrade or Farenheit

<!--`csv_log_rate` an integer value, used to describe logging irregularly. This confuses and is not really relevant to this provider, I aim to remove this option. If the log_rate were 2 and the log_period were 60 then logging would happen every 30 seconds.-->

`csv_log_period` an integer of seconds at which to log data, 60 = 1 minute

`csv_log_averaging_period` an integer of seconds that decribes over how many data points to average. If set to 0 then the most recently received data for that Tilt will be logged. If set to 30 then the most recent 30 seconds worth of data will be averaged and that single value logged. This must be a number that is <= the log period.

`csv_backup_count` an integer decribeing how many CSV log files to keep for each Tilt. If set to 0 then only 1 CSV file will be present. This will be a larger file, but if storage space is exceeded then the whole file will be replace - losing all hsitorical logging. The default is 4. With this setting there would be 5 files named e.g. `red.csv, red.csv.1, red.csv.2, red.csv.3, red.csv.4`. If logging continued such that all 5 files were full, then `red.csv.4` (the oldest file) wil be deleted, the others renamed and a new `red.csv` started.

## Output
Two sample excerpts of log files with dummy data are shown below. The first illustrates a file where no beer name nor Original Gravity was specified, in the second both criteria were specified in the congfig.json. 

### orange.log
```
2025-02-19 16:40:23, Orange Tilt logger added
2025-02-19 16:40:33, Header: Orange Tilt
timestamp, Temperature (°C), Specific Gravity
2025-02-19 16:40:33, 22.6, 1.0230
2025-02-19 16:41:03, 22.4, 1.0224
2025-02-19 16:41:33, 22.1, 1.0240
2025-02-19 16:42:03, 22.7, 1.0226
```

### Festbier.log
```
2025-02-19 16:40:24, Simulated Tilt: Festbier logger added
2025-02-19 16:40:34, Header: Simulated Tilt for Festbier
timestamp, ABV (%), Apparent Attenuation (%), Temperature (°C), Specific Gravity
2025-02-19 16:40:34, 5.71, 77.04, 21.9, 1.0259
2025-02-19 16:41:04, 6.28, 85.10, 22.5, 1.0216
2025-02-19 16:41:34, 6.37, 86.41, 22.5, 1.0209
2025-02-19 16:42:04, 6.76, 92.03, 22.2, 1.0179
```

The first entry in the file identifies the start time of the device. The second entry will occur after the first averaging period has elapsed.

There follows a header line detailing the type of parameter and unit being recorded. 

Subsequent data will be recorded at the logging interval. In the data above a 10 second averaging and 30 second logging interval were used.

## Calculating data storage

Bear in mind that a Pico and similar microcontrollers typically have limited flash storage. In development there is approximately 480kb free on the Pico, once I have compiled a UF2 this should be increased somewhat, but storage is still limited. 

File sizes will be calculated automatically based on available flash storage at run time. By default there are 2 debug.log files at 50kb each. Tilt-bridge will look for free space, will discount the debug.log files and any other files that will be ovewritten and calculate remaining blocks and filesize.

Allow 200 bytes for the header of a log file. Each data point entry will consume 34 bytes in the case of the smaller (Temp & SG only) or 47 bytes for the more complete (ABV, AA, Temp & SG). 

With 480kb free - 100kb of debug files = 380kb free space.

Thus approximately 11,300 (compact) or 8,000 (more complete) records could fill the flash. At this point, to prevent the device crashing, the oldest log file will be deleted and a new one written. 

If logging a single Tilt at 1 minute intervals this represents 188 or 133 hours, ~7 days or ~5 days. Obviously changing the logging interval can significantly improve the data sotorage time.

However, if there were 2 Tilts being logged every 1 minute, the time until data was overwritten would be halved. Increasing the log interval, to say 5 minutes, is one approach. ANother would be to use a RP2040 based board with more flash storage. 

Summary; some thought and file management needs to go into memory management if you are storing CSV log files on the Pico. 