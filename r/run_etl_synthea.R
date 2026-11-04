# OHDSI reference ETL runner (ETL-Synthea).
#
# Loads the same Synthea output into a separate `reference_etl` schema using OHDSI's
# reference implementation. TraceMap's reconciliation (docs/reconciliation.md) compares
# per-table row counts and the distribution of the top concepts per domain against this
# reference. Every difference must be explained.
#
# Install once with:
#   install.packages("remotes")
#   remotes::install_github("OHDSI/ETLSyntheaBuilder")

suppressPackageStartupMessages({
  library(DatabaseConnector)
  library(ETLSyntheaBuilder)
})

read_env <- function(key, default = NULL) {
  value <- Sys.getenv(key)
  if (nchar(value) == 0) default else value
}

cd <- createConnectionDetails(
  dbms     = "postgresql",
  server   = paste0(read_env("TRACEMAP_DB_HOST", "localhost"), "/",
                   read_env("TRACEMAP_DB_NAME", "tracemap")),
  port     = as.integer(read_env("TRACEMAP_DB_PORT", "5440")),
  user     = read_env("TRACEMAP_DB_USER", "tracemap"),
  password = read_env("TRACEMAP_DB_PASSWORD", "tracemap")
)

cdmSchema      <- "reference_etl"
cdmVersion     <- "5.4"
syntheaSchema  <- "reference_etl_source"
syntheaVersion <- "3.3.0"
vocabFileLoc   <- file.path("data", "vocab")
syntheaFileLoc <- file.path("data", "synthea", "output", "full", "csv")

CreateCDMTables(connectionDetails = cd, cdmSchema = cdmSchema, cdmVersion = cdmVersion)
CreateSyntheaTables(connectionDetails = cd, syntheaSchema = syntheaSchema, syntheaVersion = syntheaVersion)
LoadSyntheaTables(connectionDetails = cd, syntheaSchema = syntheaSchema, syntheaFileLoc = syntheaFileLoc)
LoadVocabFromCsv(connectionDetails = cd, cdmSchema = cdmSchema, vocabFileLoc = vocabFileLoc)
LoadEventTables(connectionDetails = cd, cdmSchema = cdmSchema, syntheaSchema = syntheaSchema,
                cdmVersion = cdmVersion, syntheaVersion = syntheaVersion)

cat("ETL-Synthea reconciliation build complete. Use docs/reconciliation.md template to compare.\n")
