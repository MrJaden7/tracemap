# R scripts

R tools that TraceMap integrates with. These are not part of the Python test suite because they need an R environment with Java; they run manually or in a separate CI matrix cell.

## `run_dqd.R`

Runs the OHDSI Data Quality Dashboard against TraceMap's `cdm` + `vocab` schemas and writes the JSON result into `docs/dqd/`. Install and run:

```r
install.packages(c("remotes", "DatabaseConnector"))
remotes::install_github("OHDSI/DataQualityDashboard")
# then:
Rscript r/run_dqd.R
```

## `run_etl_synthea.R`

Runs OHDSI's reference ETL (ETL-Synthea v2.1.1) into a separate `reference_etl` schema, so TraceMap's output can be reconciled against the reference. `docs/reconciliation.md` captures the differences.

```r
install.packages(c("remotes", "DatabaseConnector"))
remotes::install_github("OHDSI/ETLSyntheaBuilder")
Rscript r/run_etl_synthea.R
```

## Connection details

Both scripts read `TRACEMAP_DB_*` environment variables from `.env`, so no credentials are hard-coded. Make sure the vocabularies and the Synthea CSVs are already in place under `data/`.
