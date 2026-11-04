"""Safety gate: every AI suggestion must pass before it is accepted.

Rules:
1. The concept_id must exist in vocab.concept.
2. It must be marked standard_concept = 'S' (unmapped concepts can still be a source
   concept, but the suggestion is for the destination standard concept).
3. If the method claims a vocabulary, the concept must belong to that vocabulary.
4. If the method claims a domain, the concept must belong to that domain.

A suggestion that fails is NOT silently dropped: it is recorded in
etl_meta.mapping_suggestions with status 'rejected' and a short reason, so the reviewer
sees it.
"""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    reason: str = ""


def verify_concept(
    conn: psycopg.Connection,
    concept_id: int | None,
    expected_vocabulary: str | None = None,
    expected_domain: str | None = None,
) -> VerificationResult:
    if concept_id is None or int(concept_id) <= 0:
        return VerificationResult(False, "concept_id missing or zero")
    row = conn.execute(
        "SELECT standard_concept, vocabulary_id, domain_id "
        "FROM vocab.concept WHERE concept_id = %s",
        (int(concept_id),),
    ).fetchone()
    if row is None:
        return VerificationResult(False, f"concept_id {concept_id} not in vocab.concept")
    standard, vocab, domain = row
    if standard != "S":
        return VerificationResult(False, f"concept_id {concept_id} is not a standard concept")
    if expected_vocabulary and vocab != expected_vocabulary:
        return VerificationResult(
            False, f"vocabulary mismatch: wanted {expected_vocabulary}, got {vocab}"
        )
    if expected_domain and domain != expected_domain:
        return VerificationResult(False, f"domain mismatch: wanted {expected_domain}, got {domain}")
    return VerificationResult(True)
