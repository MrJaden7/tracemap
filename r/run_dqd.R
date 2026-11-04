# OHDSI Data Quality Dashboard runner
#
# Runs DQD against TraceMap's cdm + vocab schemas and writes the JSON result to
# docs/dqd/dqd_result_<timestamp>.json. Summary stats go to docs/dqd/summary.md.
#
# This script needs R 4.x with Java and the OHDSI DataQualityDashboard and DatabaseConnector
# packages. Install once with:
#   install.packages(c("remotes"))
#   remotes::install_github("OHDSI/DatabaseConnector")
#   remotes::install_github("OHDSI/DataQualityDashboard")

suppressPackageStartupMessages({
  library(DatabaseConnector)
  library(DataQualityDashboard)
})

read_env <- function(key, default = NULL) {
  value <- Sys.getenv(key)
  if (nchar(value) == 0) default else value
}

details <- createConnectionDetails(
  dbms     = "postgresql",
  server   = paste0(read_env("TRACEMAP_DB_HOST", "localhost"), "/",
                   read_env("TRACEMAP_DB_NAME", "tracemap")),
  port     = as.integer(read_env("TRACEMAP_DB_PORT", "5440")),
  user     = read_env("TRACEMAP_DB_USER", "tracemap"),
  password = read_env("TRACEMAP_DB_PASSWORD", "tracemap")
)

outputFolder <- file.path("docs", "dqd")
dir.create(outputFolder, showWarnings = FALSE, recursive = TRUE)
resultFile <- file.path(outputFolder, format(Sys.time(), "dqd_result_%Y%m%dT%H%M%S.json"))

result <- executeDqChecks(
  connectionDetails         = details,
  cdmDatabaseSchema         = "cdm",
  resultsDatabaseSchema     = "etl_meta",
  vocabDatabaseSchema       = "vocab",
  cdmSourceName             = "TraceMap synthetic Synthea",
  cdmVersion                = "5.4",
  numThreads                = 2,
  sqlOnly                   = FALSE,
  outputFolder              = outputFolder,
  outputFile                = basename(resultFile),
  writeToTable              = FALSE,
  writeTableName            = "dqd_results",
  verboseMode               = FALSE
)

cat(sprintf("DQD completed. Result at %s\n", resultFile))
