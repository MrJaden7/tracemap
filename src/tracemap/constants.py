"""The few concept IDs TraceMap hard-codes.

Everything else is looked up from the vocabulary at run time. Each constant here records
the name, domain and vocabulary it must have, and tests/integration/test_constants.py
asserts all of that against the loaded vocabulary, so a wrong ID fails the build.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WellKnownConcept:
    concept_id: int
    concept_name: str
    domain_id: str
    vocabulary_id: str


NO_MATCHING_CONCEPT = WellKnownConcept(0, "No matching concept", "Metadata", "None")

MALE = WellKnownConcept(8507, "MALE", "Gender", "Gender")
FEMALE = WellKnownConcept(8532, "FEMALE", "Gender", "Gender")

INPATIENT_VISIT = WellKnownConcept(9201, "Inpatient Visit", "Visit", "Visit")
OUTPATIENT_VISIT = WellKnownConcept(9202, "Outpatient Visit", "Visit", "Visit")
EMERGENCY_ROOM_VISIT = WellKnownConcept(9203, "Emergency Room Visit", "Visit", "Visit")

EHR = WellKnownConcept(32817, "EHR", "Type Concept", "Type Concept")

ALL = (
    NO_MATCHING_CONCEPT,
    MALE,
    FEMALE,
    INPATIENT_VISIT,
    OUTPATIENT_VISIT,
    EMERGENCY_ROOM_VISIT,
    EHR,
)
