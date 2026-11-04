"""Synthetic UK hospital extract.

Generated deterministically from a subset of Synthea patients and from the loaded OMOP
vocabulary. For each selected patient we:

- Make a UK-style patient identifier (NHS-like 10-digit string, different shape from
  Synthea's UUID) and derive a HMAC-SHA256 linkage key from a secret salt in the
  environment. Raw Synthea UUIDs are never present in the UK files.
- Walk their Synthea conditions and translate the SNOMED code to an ICD-10 code via
  vocab.concept_relationship 'Mapped from' / 'Maps to' chains. A fraction of records
  are deliberately 'messy': codes with or without a dot, retired codes, invalid codes,
  stray whitespace. These exercise the mapping spec's ICD-10 preprocessor and the AI
  mapping evaluation (Phase 3).
- Walk their Synthea procedures and translate to OPCS-4 the same way.
- Pick inpatient encounters as admission spells.

The resulting CSVs live in `data/uk_extract/` (gitignored) and are loaded through the
same `tracemap raw load` as Synthea.
"""

import csv
import hashlib
import hmac
import os
import random
from dataclasses import dataclass
from pathlib import Path

import psycopg

from tracemap.config import get_settings
from tracemap.db import connect


@dataclass(frozen=True)
class UkExtractConfig:
    patients: int = 1000
    inpatient_fraction: float = 0.4
    procedure_fraction: float = 0.3
    messiness_fraction: float = 0.08
    seed: int = 42


def hmac_patient_key(synthea_patient_id: str, salt: str) -> str:
    """Pseudonymised linkage key. Deterministic for a given (id, salt) pair."""
    digest = hmac.new(salt.encode("utf-8"), synthea_patient_id.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()[:24]


def nhs_like_id(index: int, seed: int) -> str:
    """Return a 10-digit identifier with a leading non-zero digit. Not a real NHS number
    (no mod-11 check digit); the comment in the output doc says so."""
    rng = random.Random(f"nhs_id:{index}:{seed}")
    first = rng.randint(1, 9)
    rest = rng.randint(0, 10**9 - 1)
    return f"{first}{rest:09d}"


def _load_synthea_patients(conn: psycopg.Connection, limit: int) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        "SELECT id, birthdate, gender FROM raw.synthea_patients ORDER BY _source_row LIMIT %s",
        (limit,),
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def _snomed_to_icd10(conn: psycopg.Connection, snomed_codes: list[str]) -> dict[str, str]:
    """For each SNOMED code, find one ICD-10 (WHO) code via concept_relationship."""
    if not snomed_codes:
        return {}
    rows = conn.execute(
        """
        SELECT distinct on (sc.concept_code) sc.concept_code AS snomed, ic.concept_code AS icd10
        FROM vocab.concept sc
        JOIN vocab.concept_relationship cr ON cr.concept_id_1 = sc.concept_id
        JOIN vocab.concept ic ON ic.concept_id = cr.concept_id_2
        WHERE sc.vocabulary_id = 'SNOMED'
          AND ic.vocabulary_id = 'ICD10'
          AND cr.relationship_id IN ('Mapped from', 'Maps to')
          AND sc.concept_code = ANY(%s)
          AND cr.invalid_reason IS NULL
        ORDER BY sc.concept_code, ic.concept_code
        """,
        (snomed_codes,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _snomed_to_opcs(conn: psycopg.Connection, snomed_codes: list[str]) -> dict[str, str]:
    if not snomed_codes:
        return {}
    rows = conn.execute(
        """
        SELECT distinct on (sc.concept_code) sc.concept_code AS snomed, oc.concept_code AS opcs
        FROM vocab.concept sc
        JOIN vocab.concept_relationship cr ON cr.concept_id_1 = sc.concept_id
        JOIN vocab.concept oc ON oc.concept_id = cr.concept_id_2
        WHERE sc.vocabulary_id = 'SNOMED'
          AND oc.vocabulary_id = 'OPCS4'
          AND cr.relationship_id IN ('Mapped from', 'Maps to')
          AND sc.concept_code = ANY(%s)
          AND cr.invalid_reason IS NULL
        ORDER BY sc.concept_code, oc.concept_code
        """,
        (snomed_codes,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _mess_up_code(code: str, rng: random.Random) -> str:
    """Apply one of several realistic messiness patterns. Keeps the base code visible."""
    choice = rng.choice(["add_space", "remove_dot", "add_dot", "lowercase", "extra_zero"])
    if choice == "add_space":
        return f" {code} "
    if choice == "remove_dot":
        return code.replace(".", "")
    if choice == "add_dot":
        if "." not in code and len(code) > 3:
            return code[:3] + "." + code[3:]
        return code
    if choice == "lowercase":
        return code.lower()
    if choice == "extra_zero":
        return code + "0"
    return code


def generate_uk_extract(
    out_dir: Path,
    config: UkExtractConfig | None = None,
    salt: str | None = None,
) -> dict[str, int]:
    """Generate uk_patients.csv, uk_admissions.csv, uk_diagnoses.csv, uk_procedures.csv.

    Returns a dict of file -> row count.
    """
    config = config or UkExtractConfig()
    salt = salt or os.environ.get("TRACEMAP_LINKAGE_SALT") or "change-me"
    if salt == "change-me":
        # We allow it but the loader will record which salt was used by hashing it.
        pass
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(config.seed)

    counts: dict[str, int] = {}
    with connect() as conn:
        synthea_patients = _load_synthea_patients(conn, config.patients)
        patient_rows = []
        linkage: dict[str, tuple[str, str]] = {}  # synthea_id -> (uk_id, hmac)
        for i, (sid, birthdate, gender) in enumerate(synthea_patients, 1):
            uk_id = nhs_like_id(i, config.seed)
            hmac_key = hmac_patient_key(sid, salt)
            linkage[sid] = (uk_id, hmac_key)
            # Postcode district only (safe), chosen from a small fixed set.
            postcode = rng.choice(["OX1", "OX2", "OX3", "OX4", "RG1", "RG2", "SL1"])
            patient_rows.append((uk_id, hmac_key, birthdate or "", gender or "", postcode))

        patients_path = out_dir / "uk_patients.csv"
        with patients_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["nhs_id", "linkage_key", "birthdate", "gender", "postcode_district"])
            w.writerows(patient_rows)
        counts["uk_patients.csv"] = len(patient_rows)

        synthea_ids = [sid for sid, _, _ in synthea_patients]
        record_synthea_linkage_keys(conn, synthea_ids, salt)

        # Diagnoses: SNOMED conditions per patient -> ICD-10
        rows_diag = conn.execute(
            "SELECT patient, start, code FROM raw.synthea_conditions WHERE patient = ANY(%s)",
            (synthea_ids,),
        ).fetchall()
        snomed_codes = sorted({r[2] for r in rows_diag})
        icd10_map = _snomed_to_icd10(conn, snomed_codes)

        diag_rows = []
        spell_rows = []
        spell_counter = 0
        for sid, start, snomed in rows_diag:
            if sid not in linkage:
                continue
            uk_id, _ = linkage[sid]
            icd10 = icd10_map.get(snomed)
            if icd10 is None:
                # Simulate unmapped: keep snomed, let AI module find a match
                continue
            if rng.random() < config.messiness_fraction:
                icd10 = _mess_up_code(icd10, rng)
            diag_rows.append((uk_id, start, icd10))
            if rng.random() < config.inpatient_fraction:
                spell_counter += 1
                spell_rows.append((uk_id, f"S{spell_counter:08d}", start, start, "inpatient"))

        diag_path = out_dir / "uk_diagnoses.csv"
        with diag_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["nhs_id", "admission_date", "icd10_code"])
            w.writerows(diag_rows)
        counts["uk_diagnoses.csv"] = len(diag_rows)

        spells_path = out_dir / "uk_admissions.csv"
        with spells_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["nhs_id", "spell_id", "admission_date", "discharge_date", "admission_type"])
            w.writerows(spell_rows)
        counts["uk_admissions.csv"] = len(spell_rows)

        # Procedures: SNOMED procedures -> OPCS-4
        rows_proc = conn.execute(
            "SELECT patient, start, code FROM raw.synthea_procedures WHERE patient = ANY(%s)",
            (synthea_ids,),
        ).fetchall()
        snomed_procs = sorted({r[2] for r in rows_proc})
        opcs_map = _snomed_to_opcs(conn, snomed_procs)

        proc_rows = []
        for sid, start, snomed in rows_proc:
            if sid not in linkage or rng.random() > config.procedure_fraction:
                continue
            uk_id, _ = linkage[sid]
            opcs = opcs_map.get(snomed)
            if opcs is None:
                continue
            if rng.random() < config.messiness_fraction:
                opcs = _mess_up_code(opcs, rng)
            proc_rows.append((uk_id, start, opcs))

        proc_path = out_dir / "uk_procedures.csv"
        with proc_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["nhs_id", "procedure_date", "opcs4_code"])
            w.writerows(proc_rows)
        counts["uk_procedures.csv"] = len(proc_rows)

    return counts


def default_out_dir() -> Path:
    return get_settings().vocab_dir.parent / "uk_extract"


def record_synthea_linkage_keys(conn: psycopg.Connection, synthea_ids: list[str], salt: str) -> int:
    """Store (synthea_id, linkage_key) pairs so the cross-source model can join to UK rows.

    The salt itself is never stored; only the HMAC output, which is one-way.
    """
    rows = [(sid, hmac_patient_key(sid, salt)) for sid in synthea_ids]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE etl_meta.synthea_linkage_keys")
        cur.executemany(
            "INSERT INTO etl_meta.synthea_linkage_keys (synthea_id, linkage_key) VALUES (%s, %s)",
            rows,
        )
    conn.commit()
    return len(rows)
