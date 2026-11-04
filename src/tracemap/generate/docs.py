"""Generate human-readable mapping documentation and Mermaid lineage diagrams from the
mapping specification. The output lives in docs/mappings/ and docs/lineage/, built into
the MkDocs site at docs/site/ by `mkdocs build`."""

from pathlib import Path

from tracemap.config import REPO_ROOT
from tracemap.spec.models import (
    ConstantRule,
    CopyRule,
    LookupRule,
    MappingSpec,
    StandardConceptMapRule,
    load_all_specs,
)

MAPPINGS_DIR = REPO_ROOT / "docs" / "mappings"
LINEAGE_DIR = REPO_ROOT / "docs" / "lineage"
INDEX_PATH = REPO_ROOT / "docs" / "mappings" / "index.md"


def _rule_summary(rule) -> str:
    """One short string per rule, suitable for the Rule column of the mapping table."""
    name = type(rule).__name__.removesuffix("Rule").lower()
    if isinstance(rule, ConstantRule):
        label = f" ({rule.label})" if rule.label else ""
        return f"constant = {rule.value}{label}"
    if isinstance(rule, LookupRule):
        return f"lookup via `{rule.via}`"
    if isinstance(rule, StandardConceptMapRule):
        extra = " (domain routing)" if rule.domain_routing else ""
        return f"standard_concept_map ({rule.source_vocabulary}, '{rule.relationship}'){extra}"
    return name


def _source_column(rule) -> str:
    if isinstance(rule, CopyRule | LookupRule | StandardConceptMapRule):
        return rule.from_
    if hasattr(rule, "from_"):
        return getattr(rule, "from_", "")
    return "-"


def mapping_doc(spec: MappingSpec) -> str:
    """Render one mapping specification as a markdown page."""
    lines = [
        f"# `{spec.target_table}`",
        "",
        f"**Spec version:** {spec.spec_version}  ",
        f"**Source systems:** {', '.join(spec.source_systems)}",
        "",
    ]
    if spec.description:
        lines += [spec.description.strip(), ""]
    for source in spec.sources:
        lines += [
            f"## Source: `{source.source_table}`",
            "",
            f"- **System:** {source.source_system}",
            f"- **Grain:** {source.grain}",
        ]
        if source.where:
            lines.append(f"- **Where:** `{source.where}`")
        lines += [
            "",
            "| Target field | Source column | Rule | Notes |",
            "| --- | --- | --- | --- |",
        ]
        for rule in source.fields:
            note = (rule.notes or "").replace("|", "\\|").strip()
            lines.append(
                f"| `{rule.target}` | `{_source_column(rule)}` | {_rule_summary(rule)} | {note} |"
            )
        lines.append("")
    lines += [
        f"[Lineage diagram](../lineage/{spec.target_table}.md)",
        "",
    ]
    return "\n".join(lines)


def lineage_diagram(spec: MappingSpec) -> str:
    """Render one target-table lineage diagram as a Mermaid flowchart."""
    lines = [
        f"# Lineage: `{spec.target_table}`",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for i, source in enumerate(spec.sources):
        src_id = f"src{i}"
        stg_id = f"stg{i}"
        lines.append(f'  {src_id}["{source.source_table}"] --> {stg_id}["staging"]')
        lookups = sorted({rule.via for rule in source.fields if isinstance(rule, LookupRule)})
        for lu in lookups:
            lu_id = "km_" + lu.replace(".", "_")
            lines.append(f'  {lu_id}["{lu}"] --> tgt["cdm.{spec.target_table}"]')
        std_maps = sorted(
            {
                rule.source_vocabulary
                for rule in source.fields
                if isinstance(rule, StandardConceptMapRule)
            }
        )
        for sm in std_maps:
            sm_id = f"std_{sm.lower().replace(' ', '_').replace('+', 'plus')}"
            lines.append(f'  {sm_id}["vocab.{sm} → standard"] --> tgt["cdm.{spec.target_table}"]')
        lines.append(f'  {stg_id} --> tgt["cdm.{spec.target_table}"]')
    lines += ["```", ""]
    return "\n".join(lines)


def project_lineage_diagram(specs: dict[str, MappingSpec]) -> str:
    """One whole-project diagram."""
    lines = ["# Whole-project lineage", "", "```mermaid", "flowchart LR"]
    seen_sources: set[str] = set()
    for name, spec in sorted(specs.items()):
        for source in spec.sources:
            src = source.source_table
            if src not in seen_sources:
                lines.append(f'  s["{src}"]'.replace("s[", f"s_{src.replace('.', '_')}["))
                seen_sources.add(src)
            lines.append(f'  s_{src.replace(".", "_")} --> t_{name}["cdm.{name}"]')
    lines += ["```", ""]
    return "\n".join(lines)


def write_docs(spec_dir: Path | None = None) -> list[Path]:
    """Regenerate every mapping doc and lineage diagram, plus an index."""
    MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    specs = load_all_specs(spec_dir)
    for name, spec in sorted(specs.items()):
        doc_path = MAPPINGS_DIR / f"{name}.md"
        doc_path.write_text(mapping_doc(spec), encoding="utf-8")
        written.append(doc_path)
        lineage_path = LINEAGE_DIR / f"{name}.md"
        lineage_path.write_text(lineage_diagram(spec), encoding="utf-8")
        written.append(lineage_path)
    index_lines = [
        "# Mapping specifications",
        "",
        "One page per OMOP target table. The page is generated directly from the YAML "
        "spec in `mapping_spec/`, so what you see here is what the pipeline executes.",
        "",
        "| Target | Spec | Lineage |",
        "| --- | --- | --- |",
    ]
    for name in sorted(specs):
        index_lines.append(f"| `{name}` | [spec]({name}.md) | [lineage](../lineage/{name}.md) |")
    index_lines.append("")
    INDEX_PATH.write_text("\n".join(index_lines), encoding="utf-8")
    written.append(INDEX_PATH)
    whole_path = LINEAGE_DIR / "project.md"
    whole_path.write_text(project_lineage_diagram(specs), encoding="utf-8")
    written.append(whole_path)
    return written
