| Query | Before (ms) | After (ms) | Speed-up |
|---|---:|---:|---:|
| q1_device_lookup | 266.3 | 294.5 | 0.9x |
| q2_no_time_filter | 304.5 | 310.9 | 1.0x |
| q3_function_on_time | 1438.9 | 301.0 | 4.8x |
| q4_naive_hourly_agg | 1846.2 | 516.8 | 3.6x |

Table size before: 60 MB / after (compression policy): 44 MB
