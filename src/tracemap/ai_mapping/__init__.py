"""AI-assisted mapping evaluation (Phase 3).

The hard rule is in `safety.py`: no suggestion is ever written directly into cdm.*. The AI
produces entries in `etl_meta.mapping_suggestions`, each of which a reviewer must accept
before it becomes part of the mapping spec. Suggestions are verified against the loaded
vocabulary before they are even recorded: the picked concept_id must exist, be standard
and be in an expected domain, otherwise the suggestion is rejected.
"""

from tracemap.ai_mapping.evaluation import Evaluation, EvaluationResult, GoldItem
from tracemap.ai_mapping.gold import GOLD_PATH, build_gold_set, load_gold_set
from tracemap.ai_mapping.methods import (
    BM25Method,
    ExactMatchMethod,
    HybridMethod,
    LlmReRanker,
    Method,
    Prediction,
)

__all__ = [
    "GOLD_PATH",
    "BM25Method",
    "Evaluation",
    "EvaluationResult",
    "ExactMatchMethod",
    "GoldItem",
    "HybridMethod",
    "LlmReRanker",
    "Method",
    "Prediction",
    "build_gold_set",
    "load_gold_set",
]
