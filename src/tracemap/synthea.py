"""Synthea runner.

TraceMap pins Synthea v3.3.0 (see ADR 0006). This module downloads the jar once,
checks its SHA-256, and generates patient records with a fixed seed into a chosen
output folder so each run is reproducible.
"""

import hashlib
import os
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SYNTHEA_VERSION = "v3.3.0"
SYNTHEA_JAR_URL = (
    f"https://github.com/synthetichealth/synthea/releases/download/{SYNTHEA_VERSION}"
    "/synthea-with-dependencies.jar"
)
SYNTHEA_JAR_SHA256 = "8ba04f7d73abadd5a377e41edf24c5c83935a1cb07c6d982cd5db731ef1cf445"


@dataclass(frozen=True)
class SyntheaRun:
    version: str
    seed: int
    patients: int
    jar_sha256: str
    output_dir: Path


def jar_path(synthea_dir: Path) -> Path:
    return synthea_dir / "jar" / f"synthea-with-dependencies-{SYNTHEA_VERSION}.jar"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def fetch_jar(synthea_dir: Path) -> Path:
    jar = jar_path(synthea_dir)
    if jar.is_file() and sha256_of(jar) == SYNTHEA_JAR_SHA256:
        return jar
    jar.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(SYNTHEA_JAR_URL, jar)
    actual = sha256_of(jar)
    if actual != SYNTHEA_JAR_SHA256:
        jar.unlink(missing_ok=True)
        raise RuntimeError(
            f"Synthea jar checksum mismatch: expected {SYNTHEA_JAR_SHA256}, got {actual}"
        )
    return jar


def java_executable() -> str:
    """Prefer JAVA_HOME (Synthea needs Java 17) over whatever `java` is on PATH."""
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if candidate.is_file():
            return str(candidate)
    return "java"


def generate(
    synthea_dir: Path,
    output_dir: Path,
    patients: int,
    seed: int = 42,
) -> SyntheaRun:
    jar = fetch_jar(synthea_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        java_executable(),
        "-jar",
        str(jar),
        "-p",
        str(patients),
        "-s",
        str(seed),
        "--exporter.csv.export",
        "true",
        "--exporter.fhir.export",
        "false",
        "--exporter.hospital.fhir.export",
        "false",
        "--exporter.practitioner.fhir.export",
        "false",
        "--exporter.baseDirectory",
        str(output_dir),
    ]
    subprocess.run(command, check=True)
    return SyntheaRun(
        version=SYNTHEA_VERSION,
        seed=seed,
        patients=patients,
        jar_sha256=SYNTHEA_JAR_SHA256,
        output_dir=output_dir,
    )
