"""Row-level lineage: trace any CDM row back to its exact source file, row, checksum
and run. Powered by the mapping specification and the raw loader's _source_row/_run_id."""

from tracemap.lineage.trace import TraceResult, trace_row

__all__ = ["TraceResult", "trace_row"]
