# METEOROLOGICAL-DATA- Station Networks

## ETL & QC Pipeline Overview

### ETL stage (run_pipeline_ETL.py)

- Read two CSV sources, normalize numeric/date formats, merge on `IDSTATION`.
- Optionally filter rows to Europe by latitude/longitude bounding box.
- Save a station dataset with date-range-based filename.

### QC stage (run_pipeline_QC.py)

- Take the ETL-produced aggregated TS CSV.
- Create `TS_<start>_<end>/` folder and a `log.txt`.
- For each variable of interest:
  - detect long runs of empty cells (`NaN`s across columns),
  - detect excessive consecutive-day temperature changes,
  - detect missing days / `NaN` on days,
  - detect flatlined consecutive identical values for multiple `n` thresholds.
- Save each rule’s findings into separate CSV outputs.
