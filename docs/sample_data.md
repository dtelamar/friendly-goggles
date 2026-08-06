# Synthetic sample telemetry

`sample_data/drive_log.csv` is a deterministic, synthetic 10-minute trip. It
does not represent data captured from a real person or vehicle.

The sample exists to make the DriveSense MVP reproducible before OBD-II
hardware is introduced. Its signals are correlated instead of independently
random: speed changes affect throttle and engine load, virtual gear bands
affect RPM, and operating conditions affect coolant and intake temperatures.

## Included scenarios

| Approximate time | Scenario |
| --- | --- |
| 0-20 s | Warm idle |
| 20-78 s | Urban acceleration, cruise, and stop |
| 78-92 s | Traffic-light idle |
| 92-130 s | Acceleration followed by hard braking |
| 142-355 s | Arterial road and highway cruise |
| 355-372 s | Traffic idle |
| 372-426 s | Normal acceleration and cruise |
| 430-438 s | Deliberate high-throttle, high-RPM acceleration |
| 438-500 s | Higher-load driving and brief heat soak |
| 512-516 s | Second hard-braking event |
| 516-532 s | Idle after stopping |
| 532-600 s | Final urban segment and stop |

## Reproducing the file

From the repository root:

```bash
python scripts/generate_sample_data.py
```

The generator uses only Python's standard library and a fixed default seed.
Running it again produces the same CSV bytes, which makes tests and code review
repeatable.

## Units and cadence

- Sample rate: 1 Hz
- Duration: 600 seconds
- Rows: 601 including both `0` and `600` seconds
- Speed: km/h
- Temperatures: degrees Celsius
- Throttle and engine load: percent
- Engine speed: rpm
