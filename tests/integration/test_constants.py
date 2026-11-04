"""Every hard-coded concept ID must match the loaded vocabulary. Needs `tracemap vocab load`."""

import pytest

from tracemap import constants
from tracemap.db import connect

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def concepts():
    ids = [c.concept_id for c in constants.ALL]
    with connect() as conn:
        rows = conn.execute(
            "SELECT concept_id, concept_name, domain_id, vocabulary_id, standard_concept "
            "FROM vocab.concept WHERE concept_id = ANY(%s)",
            (ids,),
        ).fetchall()
    if not rows:
        pytest.skip("vocab.concept is empty; run `tracemap vocab load` first")
    return {row[0]: row for row in rows}


@pytest.mark.parametrize("expected", constants.ALL, ids=lambda c: f"{c.concept_id}")
def test_constant_matches_vocabulary(concepts, expected):
    assert expected.concept_id in concepts, f"{expected.concept_id} not in vocab.concept"
    _, name, domain, vocabulary, standard = concepts[expected.concept_id]
    assert (name, domain, vocabulary) == (
        expected.concept_name,
        expected.domain_id,
        expected.vocabulary_id,
    )
    if expected.concept_id != 0:
        assert standard == "S", f"{expected.concept_id} is not a standard concept"
