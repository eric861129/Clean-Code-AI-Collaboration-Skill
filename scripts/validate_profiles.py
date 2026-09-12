from __future__ import annotations

import argparse
from dataclasses import dataclass, field as dataclass_field
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
import yaml


CATALOG_PATH = Path("profiles/catalog.yaml")
SCHEMA_PATH = Path("profiles/profile.schema.json")
EVIDENCE_SCHEMA_PATH = "evals/profile-pilot-result.schema.json"
EVIDENCE_SCHEMA_PATHS = {
    "profile-pilot-result/v1": EVIDENCE_SCHEMA_PATH,
    "profile-pilot-result/v2": "evals/profile-pilot-result-v2.schema.json",
}


def evidence_schema_path(schema_version: object) -> str:
    """只依已知版本挑選 Repository 內的 Schema，不接受外部 URL。"""
    if not isinstance(schema_version, str) or schema_version not in EVIDENCE_SCHEMA_PATHS:
        raise ValueError("public result schema version is unsupported")
    return EVIDENCE_SCHEMA_PATHS[schema_version]


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


_BOUNDARY_PRIORITY = {"project": 0, "package": 1, "workspace": 2}
_KIND_PRIORITY = {"language": 0, "framework": 1}
_DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)


def _normalize_changed_file(repository_root: Path, changed_file: str) -> PurePosixPath:
    relative = PurePosixPath(changed_file)
    if (
        not changed_file
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in changed_file
        or ":" in changed_file
    ):
        raise ValueError(
            f"changed file must be a repository-relative POSIX path: {changed_file}"
        )
    resolved_root = repository_root.resolve()
    resolved_candidate = resolved_root.joinpath(*relative.parts).resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"changed file escapes repository root: {changed_file}") from error
    return relative


def _matches(name: str, pattern: str) -> bool:
    return fnmatchcase(name, pattern)


def profile_is_available(profile: Mapping[str, Any] | None) -> bool:
    """Return whether a profile may participate in routing or packaging."""

    return bool(
        profile
        and profile.get("status") not in {"planned", "deprecated"}
        and profile.get("reference")
    )


def _ancestor_directories(repository_root: Path, relative: PurePosixPath) -> list[Path]:
    root = repository_root.resolve()
    current = root.joinpath(*relative.parent.parts)
    directories: list[Path] = []
    while True:
        directories.append(current)
        if current == root:
            return directories
        current = current.parent


def _directory_file_names(directory: Path) -> tuple[str, ...]:
    try:
        return tuple(
            entry.name
            for entry in directory.iterdir()
            if entry.is_file() and not entry.is_symlink()
        )
    except OSError:
        return ()


def _module_root_for_file(
    repository_root: Path,
    relative: PurePosixPath,
    profiles: Sequence[Mapping[str, Any]],
) -> PurePosixPath:
    candidates: list[tuple[int, int, int, int, Path]] = []
    for distance, directory in enumerate(
        _ancestor_directories(repository_root, relative)
    ):
        names = _directory_file_names(directory)
        if not names:
            continue
        for profile_index, profile in enumerate(profiles):
            manifests = profile["detection"]["owning_manifests"]
            for manifest_index, manifest in enumerate(manifests):
                if any(_matches(name, manifest["pattern"]) for name in names):
                    candidates.append(
                        (
                            distance,
                            _BOUNDARY_PRIORITY[manifest["boundary"]],
                            profile_index,
                            manifest_index,
                            directory,
                        )
                    )
    if not candidates:
        return PurePosixPath(".")
    owner_directory = min(candidates)[4]
    relative_owner = owner_directory.relative_to(repository_root.resolve())
    return PurePosixPath(relative_owner.as_posix() or ".")


def _changed_manifest_matches(
    changed_file: PurePosixPath,
    profile: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    return [
        manifest
        for manifest in profile["detection"]["owning_manifests"]
        if _matches(changed_file.name, manifest["pattern"])
    ]


def _has_nearby_language_file(
    repository_root: Path,
    module_root: PurePosixPath,
    extensions: set[str],
) -> bool:
    root = repository_root.resolve().joinpath(*module_root.parts)
    if not root.is_dir():
        return False
    ignored = {".git", ".venv", "dist", "build", "node_modules", "vendor"}
    try:
        for candidate in root.rglob("*"):
            if any(part.casefold() in ignored for part in candidate.parts):
                continue
            if candidate.is_file() and candidate.suffix.casefold() in extensions:
                return True
    except OSError:
        return False
    return False


def _language_candidate(
    repository_root: Path,
    module_root: PurePosixPath,
    changed_files: Sequence[PurePosixPath],
    profile: Mapping[str, Any],
) -> tuple[bool, str | None]:
    extensions = {
        extension.casefold() for extension in profile["detection"]["file_extensions"]
    }
    if any(changed_file.suffix.casefold() in extensions for changed_file in changed_files):
        return True, "extension-match"

    for changed_file in changed_files:
        manifests = _changed_manifest_matches(changed_file, profile)
        if not manifests:
            continue
        if any(manifest["boundary"] == "project" for manifest in manifests):
            return True, "manifest-match"
        if _has_nearby_language_file(repository_root, module_root, extensions):
            return True, "manifest-match"
    return False, None


def _nearest_package_manifest(
    repository_root: Path,
    changed_files: Sequence[PurePosixPath],
) -> Path | None:
    candidates: list[tuple[int, str, Path]] = []
    root = repository_root.resolve()
    for changed_file in changed_files:
        for distance, directory in enumerate(
            _ancestor_directories(repository_root, changed_file)
        ):
            package_path = directory / "package.json"
            if package_path.is_file() and not package_path.is_symlink():
                relative = package_path.relative_to(root).as_posix()
                candidates.append((distance, relative.casefold(), package_path))
                break
    return min(candidates)[2] if candidates else None


def _package_dependencies(package_path: Path | None) -> set[str]:
    if package_path is None:
        return set()
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(package, Mapping):
        return set()
    dependencies: set[str] = set()
    for field in _DEPENDENCY_FIELDS:
        values = package.get(field, {})
        if isinstance(values, Mapping):
            dependencies.update(
                str(name).casefold() for name in values if isinstance(name, str)
            )
    return dependencies


def _imports_dependency(path: Path, markers: set[str]) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    for marker in markers:
        escaped = re.escape(marker)
        if re.search(
            rf"(?:from\s+|import\s*\(|require\s*\()\s*['\"]{escaped}(?:/[^'\"]*)?['\"]",
            content,
        ):
            return True
    return False


def _framework_candidate(
    repository_root: Path,
    changed_files: Sequence[PurePosixPath],
    profile: Mapping[str, Any],
) -> tuple[bool, str | None]:
    markers = {
        marker.casefold() for marker in profile["detection"]["dependency_markers"]
    }
    if not markers:
        return False, None
    package_path = _nearest_package_manifest(repository_root, changed_files)
    if not markers.intersection(_package_dependencies(package_path)):
        return False, None

    relevant_extensions = {
        extension.casefold() for extension in profile["detection"]["file_extensions"]
    }
    manifest_changed = any(
        changed_file.name.casefold() == "package.json" for changed_file in changed_files
    )
    extension_relevant = any(
        changed_file.suffix.casefold() in relevant_extensions
        for changed_file in changed_files
    )
    import_relevant = any(
        _imports_dependency(
            repository_root.resolve().joinpath(*changed_file.parts), markers
        )
        for changed_file in changed_files
    )
    return (
        (True, "dependency-match")
        if manifest_changed or extension_relevant or import_relevant
        else (False, None)
    )


def profile_sort_key(profile: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        profile["routing"]["load_order"],
        _KIND_PRIORITY[profile["kind"]],
        profile["id"],
    )


def _append_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _route_module(
    repository_root: Path,
    module_root: PurePosixPath,
    changed_files: Sequence[PurePosixPath],
    profiles: Sequence[Mapping[str, Any]],
    explicit_profiles: Sequence[str],
) -> dict[str, Any]:
    root_label = module_root.as_posix()
    if "core-only" in {profile_id.casefold() for profile_id in explicit_profiles}:
        return {
            "root": root_label,
            "profiles": [],
            "unavailable_profiles": [],
            "reason_codes": ["explicit-core-only"],
            "unknowns": [],
        }

    profiles_by_id = {profile["id"]: profile for profile in profiles}
    explicit = sorted({profile_id.casefold() for profile_id in explicit_profiles})
    applicable_profiles: dict[str, Mapping[str, Any]] = {}
    candidates: dict[str, Mapping[str, Any]] = {}
    unavailable: list[str] = []
    reason_codes: list[str] = []
    unknowns: list[str] = []

    for profile in profiles:
        if profile["kind"] == "language":
            applicable, reason = _language_candidate(
                repository_root, module_root, changed_files, profile
            )
        else:
            applicable, reason = _framework_candidate(
                repository_root, changed_files, profile
            )
        profile_id = profile["id"]
        if not applicable:
            continue
        applicable_profiles[profile_id] = profile
        if profile["status"] == "planned":
            unavailable.append(profile_id)
            _append_once(reason_codes, "planned-profile")
            continue
        if profile["status"] == "deprecated":
            unavailable.append(profile_id)
            _append_once(reason_codes, "deprecated-profile")
            continue
        if not profile.get("reference"):
            unavailable.append(profile_id)
            _append_once(reason_codes, "missing-reference")
            continue
        candidates[profile_id] = profile
        if reason is not None:
            _append_once(reason_codes, reason)

    for explicit_id in explicit:
        if explicit_id == "core-only":
            continue
        if explicit_id not in profiles_by_id:
            unknowns.append(f"unknown explicit profile: {explicit_id}")
        elif not profile_is_available(profiles_by_id[explicit_id]):
            _append_once(unavailable, explicit_id)
            _append_once(reason_codes, "explicit-profile-unavailable")
        elif explicit_id not in candidates:
            unknowns.append(f"explicit profile is not applicable: {explicit_id}")

    resolved_requirements: dict[str, frozenset[str]] = {}

    def resolve_requirements(
        profile_id: str,
        active: frozenset[str] = frozenset(),
        required_by: str | None = None,
    ) -> frozenset[str] | None:
        if profile_id in resolved_requirements:
            return resolved_requirements[profile_id]
        if profile_id in active:
            _append_once(reason_codes, "profile-requires-unavailable")
            unknowns.append(f"requires cycle reached {profile_id}")
            return None
        profile = profiles_by_id.get(profile_id)
        if not profile_is_available(profile):
            _append_once(reason_codes, "profile-requires-unavailable")
            if required_by is not None:
                unknowns.append(f"{required_by} requires unavailable {profile_id}")
            return None
        if profile_id not in applicable_profiles:
            _append_once(reason_codes, "profile-requires-inapplicable")
            if required_by is not None:
                unknowns.append(f"{required_by} requires inapplicable {profile_id}")
            return None

        closure = {profile_id}
        for required_id in profile["composition"]["requires"]:
            required_closure = resolve_requirements(
                required_id,
                active | {profile_id},
                profile_id,
            )
            if required_closure is None:
                return None
            closure.update(required_closure)
        result = frozenset(closure)
        resolved_requirements[profile_id] = result
        return result

    selected_ids: set[str] = set()
    seed_ids = (
        [profile_id for profile_id in explicit if profile_id in candidates]
        if explicit
        else list(candidates)
    )
    for candidate_id in seed_ids:
        closure = resolve_requirements(candidate_id)
        if closure is not None:
            selected_ids.update(closure)
    selected = {
        profile_id: profiles_by_id[profile_id] for profile_id in selected_ids
    }

    ordered_candidates = sorted(selected.values(), key=profile_sort_key)

    conflict_pairs: set[tuple[str, str]] = set()
    for profile_id, profile in selected.items():
        for conflict_id in profile["composition"]["conflicts"]:
            if conflict_id in selected_ids:
                conflict_pairs.add(tuple(sorted((profile_id, conflict_id))))
    if conflict_pairs:
        _append_once(reason_codes, "profile-conflict")
        unknowns.extend(
            f"{left} conflicts with {right}" for left, right in sorted(conflict_pairs)
        )
        selected_profiles: list[str] = []
    else:
        selected_profiles = [profile["id"] for profile in ordered_candidates]

    if (
        not selected_profiles
        and not conflict_pairs
        and not unavailable
        and not candidates
    ):
        _append_once(reason_codes, "no-profile-match")

    return {
        "root": root_label,
        "profiles": selected_profiles,
        "unavailable_profiles": unavailable,
        "reason_codes": reason_codes,
        "unknowns": unknowns,
    }


def route_changed_files(
    repository_root: Path,
    profiles: Sequence[Mapping[str, Any]],
    changed_files: Sequence[str],
    explicit_profiles: Sequence[str] = (),
) -> dict[str, Any]:
    """Return a deterministic test oracle for changed-module profile routing."""

    root = repository_root.resolve()
    normalized_files = [
        _normalize_changed_file(root, changed_file) for changed_file in changed_files
    ]
    modules: dict[PurePosixPath, list[PurePosixPath]] = {}
    for changed_file in normalized_files:
        module_root = _module_root_for_file(root, changed_file, profiles)
        modules.setdefault(module_root, []).append(changed_file)

    routed_modules = [
        _route_module(
            root,
            module_root,
            module_files,
            profiles,
            explicit_profiles,
        )
        for module_root, module_files in modules.items()
    ]
    if any("profile-conflict" in module["reason_codes"] for module in routed_modules):
        outcome = "blocked"
    elif any(module["profiles"] for module in routed_modules):
        outcome = "selected"
    else:
        outcome = "core_only"
    return {"outcome": outcome, "modules": routed_modules}


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


def _read_repository_file(source_root: Path, relative_path: str) -> bytes:
    path, error = _repository_file(source_root, relative_path)
    if error or path is None:
        raise ValueError(error or "path does not resolve to a repository file")
    return path.read_bytes()


def _duplicate_registry_diagnostics(
    profile_entries: Sequence[tuple[str, Mapping[str, Any]]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    ids: dict[str, list[str]] = {}
    references: dict[str, list[str]] = {}
    for path, profile in profile_entries:
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
    return diagnostics


def _cross_file_diagnostics(
    read_repository_file: Callable[[str], bytes],
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
            try:
                read_repository_file(reference)
            except (OSError, ValueError) as error:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        "reference",
                        "reference-invalid",
                        str(error),
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
            try:
                read_repository_file(manifest_path)
            except (OSError, ValueError) as error:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        f"evidence.manifests.{index}",
                        "evidence-path-invalid",
                        str(error),
                    )
                )
        for index, result in enumerate(evidence["results"]):
            result_bytes: bytes | None = None
            try:
                result_bytes = read_repository_file(result["path"])
            except (OSError, ValueError) as error:
                diagnostics.append(
                    Diagnostic(
                        profile_path,
                        f"evidence.results.{index}.path",
                        "evidence-path-invalid",
                        str(error),
                    )
                )
            else:
                actual_digest = hashlib.sha256(result_bytes).hexdigest()
                if actual_digest != result["sha256"]:
                    diagnostics.append(
                        Diagnostic(
                            profile_path,
                            f"evidence.results.{index}.sha256",
                            "evidence-hash-mismatch",
                            "evidence sha256 does not match the repository file",
                        )
                    )
            if result_bytes is not None:
                diagnostics.extend(
                    _evidence_result_diagnostics(
                        profile_path,
                        profile_id,
                        index,
                        result,
                        result_bytes,
                        read_repository_file,
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


def _evidence_result_diagnostics(
    profile_path: str,
    profile_id: str,
    index: int,
    metadata: Mapping[str, Any],
    result_bytes: bytes,
    read_repository_file: Callable[[str], bytes],
) -> list[Diagnostic]:
    field = f"evidence.results.{index}"
    try:
        result = json.loads(result_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return [
            Diagnostic(
                profile_path,
                f"{field}.path",
                "evidence-result-invalid",
                f"public result must be UTF-8 JSON: {error}",
            )
        ]
    if not isinstance(result, Mapping) or result.get("status") != "complete":
        return [
            Diagnostic(
                profile_path,
                f"{field}.path",
                "evidence-result-invalid",
                "public result must be a complete result object",
            )
        ]
    diagnostics: list[Diagnostic] = []
    try:
        schema_path = evidence_schema_path(result.get("schema_version"))
        schema = json.loads(read_repository_file(schema_path).decode("utf-8"))
        Draft202012Validator.check_schema(schema)
        if not isinstance(schema, Mapping) or schema.get("properties", {}).get("schema_version", {}).get("const") != result.get("schema_version"):
            raise ValueError("public result schema does not match the selected version")
        errors = sorted(
            Draft202012Validator(schema).iter_errors(result),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if errors:
            diagnostics.append(
                Diagnostic(
                    profile_path,
                    f"{field}.path",
                    "evidence-result-schema-invalid",
                    f"public result does not match {schema_path}: "
                    f"{errors[0].message}",
                )
            )
    except (OSError, ValueError, SchemaError) as error:
        diagnostics.append(
            Diagnostic(
                profile_path,
                f"{field}.path",
                "evidence-result-schema-invalid",
                f"public result schema is unavailable or invalid: {error}",
            )
        )
    outcomes = result.get("profile_outcomes")
    if not isinstance(outcomes, list):
        return [
            Diagnostic(
                profile_path,
                f"{field}.path",
                "evidence-result-invalid",
                "public result must contain profile_outcomes",
            )
        ]
    matches = [
        item
        for item in outcomes
        if isinstance(item, Mapping) and item.get("profile_id") == profile_id
    ]
    if len(matches) != 1:
        diagnostics.append(
            Diagnostic(
                profile_path,
                f"{field}.path",
                "evidence-profile-mismatch",
                "public result must contain exactly one matching profile outcome",
            )
        )
        return diagnostics
    outcome = matches[0]
    for key in ("stage", "outcome"):
        if outcome.get(key) != metadata.get(key):
            diagnostics.append(
                Diagnostic(
                    profile_path,
                    f"{field}.{key}",
                    "evidence-result-mismatch",
                    f"metadata {key} must match the public profile outcome",
                )
            )
    if metadata.get("public") is not True:
        diagnostics.append(
            Diagnostic(
                profile_path,
                f"{field}.public",
                "evidence-public-required",
                "recorded profile evidence must be public",
            )
        )
    return diagnostics


def validate_loaded_profiles(
    profile_entries: Sequence[tuple[str, Mapping[str, Any]]],
    read_repository_file: Callable[[str], bytes],
) -> tuple[Diagnostic, ...]:
    """Validate cross-file contracts using bytes supplied by the caller."""

    diagnostics = _duplicate_registry_diagnostics(profile_entries)
    diagnostics.extend(
        _cross_file_diagnostics(read_repository_file, profile_entries)
    )
    return tuple(sorted(diagnostics))


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

    diagnostics.extend(_duplicate_registry_diagnostics(raw_entries))
    diagnostics.extend(
        _cross_file_diagnostics(
            lambda relative_path: _read_repository_file(
                source_root,
                relative_path,
            ),
            valid_entries,
        )
    )
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
