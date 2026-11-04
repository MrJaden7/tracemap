"""Gold-standard evaluation set for AI-assisted mapping.

Builds 300 local-style source terms by perturbing real SNOMED/ICD-10 concept names from
the vocabulary, plus 50 deliberately unmappable or ambiguous terms. The split into
development and frozen-held-out test sets is deterministic given the seed, so the
evaluation is reproducible and the test set is never seen during method development.

Stored as JSON (one record per line) in `data/ai_mapping/gold.jsonl`.
"""

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from tracemap.config import REPO_ROOT
from tracemap.db import connect

GOLD_PATH = REPO_ROOT / "data" / "ai_mapping" / "gold.jsonl"
UNMAPPABLE_TERMS = [
    "Patient refused test",
    "Ref 5B next Thursday",
    "Private matter - no further details",
    "See scan report on microfiche",
    "Old notes re HTN meds",
    "zzz",
    "n/a",
    "not applicable",
    "Needs chase",
    "Ambiguous: multiple possible dx",
]

# Simple perturbations we apply to real concept names.
ABBREVIATIONS = {
    "Type 2 diabetes mellitus": "T2DM",
    "Hypertension": "HTN",
    "Myocardial infarction": "MI",
    "Fractured neck of femur": "#NOF",
    "Congestive heart failure": "CHF",
    "Chronic obstructive pulmonary disease": "COPD",
    "Deep vein thrombosis": "DVT",
    "Urinary tract infection": "UTI",
    "Upper respiratory tract infection": "URTI",
    "Cerebrovascular accident": "CVA",
}
BRITISH_SPELLINGS = {
    "diarrhea": "diarrhoea",
    "esophageal": "oesophageal",
    "pediatric": "paediatric",
    "edema": "oedema",
    "tumor": "tumour",
    "anemia": "anaemia",
    "hemorrhage": "haemorrhage",
}


@dataclass(frozen=True)
class GoldItem:
    term: str
    expected_concept_id: int | None  # None => unmappable
    expected_vocabulary: str | None
    kind: str  # abbreviation, british, typo, partial, unmappable, verbatim
    source_concept_name: str | None  # the real concept name we perturbed, for traceability

    @staticmethod
    def from_json(line: str) -> "GoldItem":
        d = json.loads(line)
        return GoldItem(**d)


def _introduce_typo(text: str, rng: random.Random) -> str:
    if len(text) < 4:
        return text
    i = rng.randint(1, len(text) - 2)
    return text[:i] + text[i + 1] + text[i] + text[i + 2 :]  # swap adjacent


def _british_version(text: str) -> str | None:
    lo = text.lower()
    for us, uk in BRITISH_SPELLINGS.items():
        if us in lo:
            return text.replace(us, uk).replace(us.capitalize(), uk.capitalize())
    return None


def _partial_description(text: str, rng: random.Random) -> str:
    words = text.split()
    if len(words) < 3:
        return text
    cut = rng.randint(2, len(words) - 1)
    return " ".join(rng.sample(words, min(cut, len(words))))


def _pull_source_concepts(limit: int = 500) -> list[tuple[int, str, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT concept_id, concept_name, vocabulary_id FROM vocab.concept
            WHERE vocabulary_id IN ('SNOMED', 'ICD10', 'RxNorm', 'LOINC')
              AND standard_concept = 'S'
              AND invalid_reason IS NULL
              AND length(concept_name) BETWEEN 10 AND 90
            ORDER BY concept_id
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [(int(r[0]), r[1], r[2]) for r in rows]


def build_gold_set(mappable: int = 300, unmappable: int = 50, seed: int = 1337) -> list[GoldItem]:
    """Build the gold set from the loaded vocabulary. Deterministic for a given seed."""
    rng = random.Random(seed)
    source = _pull_source_concepts(limit=max(mappable * 4, 2000))
    if not source:
        raise RuntimeError("vocab.concept is empty; load the vocabulary first.")

    kinds = ("abbreviation", "british", "typo", "partial", "verbatim")

    items: list[GoldItem] = []
    attempts = 0
    while len(items) < mappable and attempts < mappable * 10:
        attempts += 1
        concept_id, name, vocabulary_id = rng.choice(source)
        kind = rng.choice(kinds)
        term = name
        if kind == "abbreviation":
            abbrev = next((a for n, a in ABBREVIATIONS.items() if n.lower() == name.lower()), None)
            if abbrev is None:
                continue
            term = abbrev
        elif kind == "british":
            br = _british_version(name)
            if br is None:
                continue
            term = br
        elif kind == "typo":
            term = _introduce_typo(name, rng)
        elif kind == "partial":
            term = _partial_description(name, rng)
        # verbatim leaves it unchanged
        items.append(
            GoldItem(
                term=term,
                expected_concept_id=concept_id,
                expected_vocabulary=vocabulary_id,
                kind=kind,
                source_concept_name=name,
            )
        )

    # Add deliberately unmappable terms (cycled so we get `unmappable` of them)
    for i in range(unmappable):
        items.append(
            GoldItem(
                term=UNMAPPABLE_TERMS[i % len(UNMAPPABLE_TERMS)]
                + (f" #{i}" if i >= len(UNMAPPABLE_TERMS) else ""),
                expected_concept_id=None,
                expected_vocabulary=None,
                kind="unmappable",
                source_concept_name=None,
            )
        )
    rng.shuffle(items)
    return items


def save_gold(items: list[GoldItem], path: Path | None = None) -> Path:
    path = path or GOLD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(asdict(item)) + "\n")
    return path


def load_gold_set(path: Path | None = None) -> list[GoldItem]:
    path = path or GOLD_PATH
    if not path.is_file():
        raise FileNotFoundError(f"No gold set at {path}; run `tracemap ai gold build` first.")
    with path.open(encoding="utf-8") as f:
        return [GoldItem.from_json(line) for line in f if line.strip()]


def deterministic_split(items: list[GoldItem], dev_fraction: float = 0.5, seed: int = 42):
    """Split into (dev, held_out_test) deterministically.

    The 'held_out_test' set is used only for the final numbers reported in the writeup;
    methods are tuned against 'dev'.
    """
    ordered = sorted(items, key=lambda i: hashlib.sha256(i.term.encode()).hexdigest())
    rng = random.Random(seed)
    idxs = list(range(len(ordered)))
    rng.shuffle(idxs)
    split_at = int(len(ordered) * dev_fraction)
    dev_ids = set(idxs[:split_at])
    dev = [ordered[i] for i in sorted(dev_ids)]
    test = [ordered[i] for i in range(len(ordered)) if i not in dev_ids]
    return dev, test
