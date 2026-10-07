| Query | Before (ms) | After (ms) | Chunks before/after | Scan types after | Indexes used after |
|---|---:|---:|---|---|---|
| q1_device_lookup | 1.5 | 0.1 | 4 / 4 | Custom Scan, Index Scan | _hyper_1_3_chunk_compressed_device_id__ts_meta_v2_first_tim_idx, _hyper_1_4_chunk_idx_sensor_device_time, _hyper_1_5_chunk_idx_sensor_device_time, _hyper_1_6_chunk_idx_sensor_device_time |
| q2_no_time_filter | 33.8 | 0.8 | 6 / 2 | Custom Scan, Index Scan | _hyper_1_5_chunk_idx_sensor_device_time, _hyper_1_6_chunk_idx_sensor_device_time |
| q3_function_on_time | 1132.6 | 66.8 | 6 / 1 | Custom Scan, Index Scan | _hyper_1_4_chunk_idx_sensor_device_time |
| q4_naive_hourly_agg | 1139.6 | 0.8 | 6 / 2 | Custom Scan, Index Scan | _hyper_2_7_chunk__materialized_hypertable_2_bucket_idx, _hyper_2_8_chunk__materialized_hypertable_2_bucket_idx |
