from __future__ import annotations

import argparse
from dataclasses import dataclass, field as dataclass_field
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
import yaml


CATALOG_PATH = Path("profiles/catalog.yaml")
SCHEMA_PATH = Path("profiles/profile.schema.json")


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: str
    field: str
    code: str
    message: str = dataclass_field(compare=False)


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _catalog_paths(source_root: Path) -> list[Path]:
    catalog = _load_yaml(source_root / CATALOG_PATH)
    if not isinstance(catalog, Mapping):
        raise ValueError("profile catalog must be an object")
    if set(catalog) != {"schema_version", "profiles"}:
        raise ValueError("profile catalog has unknown or missing fields")
    if catalog["schema_version"] != "1.0":
        raise ValueError("profile catalog schema_version must be 1.0")
    entries = catalog.get("profiles")
    if not isinstance(entries, list) or not all(
        isinstance(entry, str) for entry in entries
    ):
        raise ValueError("profile catalog profiles must be a list of paths")
    if len({entry.casefold() for entry in entries}) != len(entries):
        raise ValueError("profile catalog paths must be case-insensitively unique")
    profiles_root = (source_root / "profiles").resolve()
    paths: list[Path] = []
    for entry in entries:
        relative = PurePosixPath(entry)
        if (
            relative.is_absolute()
            or relative.parent != PurePosixPath(".")
            or relative.suffix != ".yaml"
            or "\\" in entry
            or ":" in entry
        ):
            raise ValueError("profile catalog entries must be YAML file names")
        path = (profiles_root / relative.name).resolve()
        if path.parent != profiles_root:
            raise ValueError("profile catalog path escapes the profiles directory")
        paths.append(path)
    return paths


def load_registry(source_root: Path) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for path in _catalog_paths(source_root):
        profile = _load_yaml(path)
        if not isinstance(profile, dict):
            raise ValueError(f"profile must be an object: {path.name}")
        profiles.append(profile)
    return profiles


def _field_path(parts: Sequence[Any]) -> str:
    return ".".join(str(part) for part in parts) or "$"


def _repository_file(source_root: Path, relative_path: str) -> tuple[Path | None, str]:
    normalized = PurePosixPath(relative_path)
    if (
        normalized.is_absolute()
        or not normalized.parts
        or ".." in normalized.parts
        or "\\" in relative_path
        or ":" in relative_path
    ):
        return None, "path must be repository-relative POSIX"
    repository_root = source_root.resolve()
    candidate = repository_root.joinpath(*normalized.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repository_root)
    except (OSError, ValueError):
        return None, "path does not resolve to a repository file"
    if candidate.is_symlink() or not resolved.is_file():
        return None, "path must resolve to a regular repository file"
    return resolved, ""


def _cross_file_diagnostics(
    source_root: Path,
    profile_entries: Sequence[tuple[str, Mapping[str, Any]]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    profiles_by_id = {profile["id"]: profile for _, profile in profile_entries}
    paths_by_id = {profile["id"]: path for path, profile in profile_entries}
    known_ids = set(profiles_by_id)

    for profile_id, profile in profiles_by_id.items():
        profile_path = paths_by_id[profile_id]
        if Path(profile_path).stem != profile_id:
            diagnostics.append(
                Diagnostic(
                    profile_path,
                    "id",
                    "profile-file-id-mismatch",
                    "profile id must match its metadata file name",
                )
            )

        reference = profile.get("reference")
        if isinstance(reference, str):
            _, error = _repository_file(source_root, reference)
            if error:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        "reference",
                        "reference-invalid",
                        error,
                    )
                )

        detection = profile["detection"]
        overlap = {
            value.casefold() for value in detection["dependency_markers"]
        } & {
            value.casefold() for value in detection["supporting_dependencies"]
        }
        if overlap:
            diagnostics.append(
                Diagnostic(
                    profile_path,
                    "detection.supporting_dependencies",
                    "dependency-role-overlap",
                    "candidate and supporting dependency roles must not overlap",
                )
            )

        composition = profile["composition"]
        for relationship in ("requires", "recommends", "conflicts"):
            for target in composition[relationship]:
                field = f"composition.{relationship}"
                if target == profile_id:
                    diagnostics.append(
                        Diagnostic(
                            profile_path,
                            field,
                            "composition-self",
                            "profile composition must not reference itself",
                        )
                    )
                elif target not in known_ids:
                    diagnostics.append(
                        Diagnostic(
                            profile_path,
                            field,
                            "composition-unknown",
                            f"unknown profile id: {target}",
                        )
                    )
        for target in composition["conflicts"]:
            if target in profiles_by_id and profile_id not in profiles_by_id[target][
                "composition"
            ]["conflicts"]:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        "composition.conflicts",
                        "conflict-asymmetric",
                        f"conflict with {target} must be declared by both profiles",
                    )
                )

        deprecation = profile.get("deprecation")
        if isinstance(deprecation, Mapping):
            replacement = deprecation.get("replacement")
            if isinstance(replacement, str) and replacement not in known_ids:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        "deprecation.replacement",
                        "replacement-unknown",
                        f"unknown replacement profile id: {replacement}",
                    )
                )

        evidence = profile["evidence"]
        for index, manifest_path in enumerate(evidence["manifests"]):
            _, error = _repository_file(source_root, manifest_path)
            if error:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        f"evidence.manifests.{index}",
                        "evidence-path-invalid",
                        error,
                    )
                )
        for index, result in enumerate(evidence["results"]):
            result_path, error = _repository_file(source_root, result["path"])
            if error:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        f"evidence.results.{index}.path",
                        "evidence-path-invalid",
                        error,
                    )
                )
            elif hashlib.sha256(result_path.read_bytes()).hexdigest() != result["sha256"]:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        f"evidence.results.{index}.sha256",
                        "evidence-hash-mismatch",
                        "evidence sha256 does not match the repository file",
                    )
                )

        stages = {result["stage"] for result in evidence["results"]}
        benchmark_status = evidence["benchmark_status"]
        expected_benchmark_status = (
            "full_run_recorded"
            if "full_run" in stages
            else "pilot_recorded"
            if "pilot" in stages
            else "not_started"
        )
        if benchmark_status != expected_benchmark_status:
            diagnostics.append(
                Diagnostic(
                    profile_path,
                    "evidence.benchmark_status",
                    "evidence-status-mismatch",
                    "benchmark status must match recorded evidence stages",
                )
            )
        required_stage = {"beta": "pilot", "stable": "full_run"}.get(
            profile["status"]
        )
        if required_stage and not any(
            result["stage"] == required_stage
            and result["outcome"] == "passed"
            and result["public"] is True
            for result in evidence["results"]
        ):
            diagnostics.append(
                Diagnostic(
                    profile_path,
                    "evidence.results",
                    "maturity-evidence-missing",
                    f"{profile['status']} requires public passed {required_stage} evidence",
                )
            )

    requires_graph = {
        profile_id: [
            target
            for target in profile["composition"]["requires"]
            if target in known_ids and target != profile_id
        ]
        for profile_id, profile in profiles_by_id.items()
    }
    visited: set[str] = set()
    active: set[str] = set()

    def visit(profile_id: str) -> None:
        if profile_id in active:
            diagnostics.append(
                Diagnostic(
                    paths_by_id[profile_id],
                    "composition.requires",
                    "composition-cycle",
                    "requires relationship contains a cycle",
                )
            )
            return
        if profile_id in visited:
            return
        active.add(profile_id)
        for target in requires_graph[profile_id]:
            visit(target)
        active.remove(profile_id)
        visited.add(profile_id)

    for profile_id in profiles_by_id:
        visit(profile_id)
    return diagnostics


def validate_repository(source_root: Path) -> tuple[Diagnostic, ...]:
    schema_path = source_root / SCHEMA_PATH
    diagnostics: list[Diagnostic] = []
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except OSError as error:
        return (
            Diagnostic(SCHEMA_PATH.as_posix(), "$", "schema-unreadable", str(error)),
        )
    except json.JSONDecodeError as error:
        return (
            Diagnostic(SCHEMA_PATH.as_posix(), "$", "schema-invalid", str(error)),
        )
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        return (
            Diagnostic(SCHEMA_PATH.as_posix(), "$", "schema-invalid", error.message),
        )
    validator = Draft202012Validator(schema)
    try:
        paths = _catalog_paths(source_root)
    except (OSError, ValueError, yaml.YAMLError) as error:
        return (
            Diagnostic(
                CATALOG_PATH.as_posix(),
                "$",
                "catalog-invalid",
                str(error),
            ),
        )

    raw_entries: list[tuple[str, Mapping[str, Any]]] = []
    valid_entries: list[tuple[str, Mapping[str, Any]]] = []
    for path in paths:
        relative_path = PurePosixPath("profiles", path.name).as_posix()
        try:
            profile = _load_yaml(path)
        except (OSError, yaml.YAMLError) as error:
            diagnostics.append(
                Diagnostic(relative_path, "$", "profile-unreadable", str(error))
            )
            continue
        if isinstance(profile, Mapping):
            raw_entries.append((relative_path, profile))
        errors = sorted(
            validator.iter_errors(profile),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        for error in errors:
            diagnostics.append(
                Diagnostic(
                    relative_path,
                    _field_path(error.absolute_path),
                    "schema-invalid",
                    error.message,
                )
            )
        if isinstance(profile, Mapping) and not errors:
            valid_entries.append((relative_path, profile))

    ids: dict[str, list[str]] = {}
    references: dict[str, list[str]] = {}
    for path, profile in raw_entries:
        profile_id = profile.get("id")
        if isinstance(profile_id, str):
            ids.setdefault(profile_id.casefold(), []).append(path)
        reference = profile.get("reference")
        if isinstance(reference, str):
            references.setdefault(reference.casefold(), []).append(path)
    for duplicate_paths in ids.values():
        if len(duplicate_paths) > 1:
            for path in duplicate_paths:
                diagnostics.append(
                    Diagnostic(
                        path,
                        "id",
                        "profile-id-duplicate",
                        "profile ids must be case-insensitively unique",
                    )
                )
    for duplicate_paths in references.values():
        if len(duplicate_paths) > 1:
            for path in duplicate_paths:
                diagnostics.append(
                    Diagnostic(
                        path,
                        "reference",
                        "reference-duplicate",
                        "profile references must be case-insensitively unique",
                    )
                )
    diagnostics.extend(_cross_file_diagnostics(source_root, valid_entries))
    return tuple(sorted(diagnostics))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate profile metadata.")
    parser.add_argument("--source-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    diagnostics = validate_repository(args.source_root.resolve())
    for diagnostic in diagnostics:
        print(
            f"{diagnostic.path}:{diagnostic.field}:{diagnostic.code}: "
            f"{diagnostic.message}"
        )
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
