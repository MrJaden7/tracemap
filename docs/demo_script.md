# Demo script

A 3-minute walkthrough for the interview. Keep the terminal large and the font big.

## 0. One line of context (15 s)

"TraceMap is a small working version of the TVS SDE's documentation-first OMOP mapper. One YAML mapping spec is the source of truth, and every CDM row traces back to the exact source file, line and run."

## 1. The spec and the generator (30 s)

```bash
head -30 mapping_spec/person.yml
uv run tracemap spec check
```

"Every rule is explicit. The generator reads these specs and writes dbt SQL, dbt tests, markdown mapping docs and Mermaid lineage diagrams."

```bash
uv run tracemap generate
head dbt/models/cdm/visit_occurrence.sql
```

## 2. End-to-end build (30 s)

```bash
uv run tracemap build
```

"Loads raw, regenerates models, runs dbt (70 tests, all green), writes coverage per domain."

## 3. The headline feature: trace (45 s)

```bash
uv run tracemap trace condition_occurrence 100
```

"This CDM row came from this exact line of conditions.csv, loaded by run 5, with this SHA-256. One command walks the lineage."

```bash
uv run tracemap trace person 42
```

"Two shapes: event tables use the source row number as the id; person tables go through an intermediate key map. See ADR 0010."

## 4. Multi-source and linkage (30 s)

```bash
docker exec tracemap-postgres psql -U tracemap -d tracemap -c \
  "SELECT source_system, count(*) FROM (
       SELECT 'synthea' AS source_system FROM int_person_key_map
       UNION ALL SELECT 'uk_extract' FROM int_person_key_map_uk
   ) s GROUP BY 1"
```

"Two synthetic sources. UK side uses ICD-10 and OPCS-4. Linked by HMAC-SHA256 with a salt that lives in an env var. Raw Synthea UUIDs never reach the UK files."

## 5. Safe outputs (20 s)

```bash
uv run tracemap analysis run ed_to_admission --raw         # before
uv run tracemap analysis run ed_to_admission               # after
```

"Same query. Second run suppresses counts below 10 and rounds the rest to the nearest 5. Rules in config/output_rules.yml so a real SDE drops in its own thresholds."

## 6. AI mapping and knowing when not to answer (30 s)

```bash
uv run tracemap ai evaluate --repeats 5
```

"Four methods against a 350-item gold set. Exact match is 99% precision but 34% coverage. BM25 covers 95% but almost never abstains. The LLM re-ranker is constrained to the candidate pool and must pick one or NO_MATCH, so it can never invent a concept_id. This is the dissertation argument in one tool: systems answer questions their sources don't support unless they are designed and tested to abstain."

## 7. Decisions (15 s)

```bash
ls docs/decisions/
```

"13 ADRs. Each one short, with alternatives, and a one-paragraph plain-English version at the end."

## Closing line

"One YAML source of truth, every row traceable, every mapping measured, and an evaluated AI module that knows when to say no. A small version of the TVS SDE's own pipeline, same design philosophy."
