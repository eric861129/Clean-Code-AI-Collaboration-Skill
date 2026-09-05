from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Literal, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
import yaml

if __package__:
    from .generate_profile_matrix import (
        RUNTIME_MARKERS,
        render_runtime_index,
        replace_generated_region,
    )
    from .validate_profiles import (
        EVIDENCE_SCHEMA_PATH,
        profile_is_available,
        profile_sort_key,
        validate_loaded_profiles,
    )
else:
    from generate_profile_matrix import (
        RUNTIME_MARKERS,
        render_runtime_index,
        replace_generated_region,
    )
    from validate_profiles import (
        EVIDENCE_SCHEMA_PATH,
        profile_is_available,
        profile_sort_key,
        validate_loaded_profiles,
    )


MANIFEST_SCHEMA_VERSION = "1.0"
PACKAGER_VERSION = "1.0"
PACKAGE_MANIFEST_PATH = "PACKAGE-MANIFEST.json"
MANIFEST_SCHEMA_PATH = "scripts/package-manifest.schema.json"
PROFILE_SCHEMA_PATH = "profiles/profile.schema.json"
PROFILE_CATALOG_PATH = "profiles/catalog.yaml"
SKILL_PATH = "clean-code-ai-collaboration/SKILL.md"
ADAPTER_PATH = "clean-code-ai-collaboration/agents/openai.yaml"
PROFILE_SELECTION_PATH = (
    "clean-code-ai-collaboration/references/profile-selection.md"
)
CORE_REFERENCE_PATHS = (
    "clean-code-ai-collaboration/references/clean-code-for-agent-legibility.md",
    "clean-code-ai-collaboration/references/code-readability.md",
    "clean-code-ai-collaboration/references/collaboration-and-estimation.md",
    "clean-code-ai-collaboration/references/design-and-dependency-boundaries.md",
    "clean-code-ai-collaboration/references/repository-context-template.md",
    "clean-code-ai-collaboration/references/review-output-contract.md",
    "clean-code-ai-collaboration/references/testing-and-change-safety.md",
)


class PackagingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sort_paths(paths: Sequence[str]) -> list[str]:
    return sorted(paths, key=lambda path: (path.casefold(), path))


def _digest_entries(values: Mapping[str, bytes]) -> list[dict[str, str]]:
    return [
        {"path": path, "sha256": hashlib.sha256(values[path]).hexdigest()}
        for path in _sort_paths(list(values))
    ]


def build_manifest(
    *,
    source_commit: str,
    source_mode: Literal["release", "worktree"],
    suite_version: str,
    profile_ids: Sequence[str],
    inputs: Mapping[str, bytes],
    files: Mapping[str, bytes],
) -> dict[str, Any]:
    ordered_ids = sorted(set(profile_ids))
    if len(ordered_ids) != len(profile_ids):
        raise PackagingError("profile-duplicate", "profile ids must be unique")
    manifest_without_digest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "source_commit": source_commit,
        "source_mode": source_mode,
        "suite_version": suite_version,
        "packager_version": PACKAGER_VERSION,
        "profile_ids": ordered_ids,
        "inputs": _digest_entries(inputs),
        "files": _digest_entries(files),
    }
    overall_digest = hashlib.sha256(
        canonical_json_bytes(manifest_without_digest)
    ).hexdigest()
    return {**manifest_without_digest, "overall_digest": overall_digest}


def compose_profiles(
    profiles_by_id: Mapping[str, Mapping[str, Any]],
    selected_ids: Sequence[str],
) -> Sequence[str]:
    if not selected_ids:
        raise PackagingError("profile-missing", "at least one profile is required")
    if len(set(selected_ids)) != len(selected_ids):
        raise PackagingError("profile-duplicate", "profile ids must be unique")

    resolved: set[str] = set()
    active: list[str] = []

    def visit(profile_id: str, required_by: str | None = None) -> None:
        profile = profiles_by_id.get(profile_id)
        if profile is None:
            if required_by:
                raise PackagingError(
                    "profile-requires-unknown",
                    f"{required_by} requires unknown profile {profile_id}",
                )
            raise PackagingError("profile-unknown", f"unknown profile: {profile_id}")
        if not profile_is_available(profile):
            status = profile.get("status", "unknown")
            if required_by:
                raise PackagingError(
                    "profile-requires-unavailable",
                    f"{required_by} requires unavailable {profile_id} ({status})",
                )
            raise PackagingError(
                "profile-unavailable",
                f"profile {profile_id} is {status} and cannot be packaged",
            )
        if profile_id in active:
            cycle = " -> ".join([*active, profile_id])
            raise PackagingError(
                "profile-cycle",
                f"profile requires cycle: {cycle}",
            )
        if profile_id in resolved:
            return
        active.append(profile_id)
        for required_id in profile["composition"]["requires"]:
            if required_id == profile_id:
                raise PackagingError(
                    "profile-self-requirement",
                    f"profile {profile_id} requires itself",
                )
            visit(required_id, profile_id)
        active.pop()
        resolved.add(profile_id)

    for selected_id in selected_ids:
        visit(selected_id)

    conflicts: set[tuple[str, str]] = set()
    for profile_id in resolved:
        for conflict_id in profiles_by_id[profile_id]["composition"]["conflicts"]:
            if conflict_id in resolved:
                conflicts.add(tuple(sorted((profile_id, conflict_id))))
    if conflicts:
        details = ", ".join(
            f"{left} conflicts with {right}"
            for left, right in sorted(conflicts)
        )
        raise PackagingError("profile-conflict", details)
    return tuple(
        sorted(
            resolved,
            key=lambda profile_id: profile_sort_key(profiles_by_id[profile_id]),
        )
    )


def _validate_relative_path(relative_path: str) -> PurePosixPath:
    path = PurePosixPath(relative_path)
    if (
        not relative_path
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in relative_path
        or ":" in relative_path
    ):
        raise PackagingError(
            "source-path-invalid",
            f"source path must be repository-relative POSIX: {relative_path}",
        )
    return path


def _git(
    source_root: Path,
    arguments: Sequence[str],
    *,
    text: bool,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(source_root), *arguments],
        capture_output=True,
        check=False,
        text=text,
    )
    if result.returncode != 0:
        error = (
            result.stderr.strip()
            if text
            else result.stderr.decode("utf-8", "replace").strip()
        )
        raise PackagingError("git-source-invalid", error or "git command failed")
    return result


def _head_commit(source_root: Path) -> str:
    commit = _git(
        source_root,
        ["rev-parse", "--verify", "HEAD^{commit}"],
        text=True,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PackagingError("git-source-invalid", "HEAD is not a full commit SHA")
    return commit


class _SourceReader:
    def __init__(
        self,
        source_root: Path,
        source_mode: Literal["release", "worktree"],
    ) -> None:
        self.root = source_root.resolve(strict=True)
        self.mode = source_mode
        if not self.root.is_dir():
            raise PackagingError(
                "source-root-invalid",
                "source root must be a directory",
            )
        if source_mode not in {"release", "worktree"}:
            raise PackagingError(
                "source-mode-invalid",
                f"unknown source mode: {source_mode}",
            )
        self.commit = _head_commit(self.root)
        if source_mode == "release":
            status = _git(
                self.root,
                ["status", "--porcelain", "--untracked-files=all"],
                text=True,
            ).stdout
            if status.strip():
                raise PackagingError(
                    "release-worktree-dirty",
                    "release source requires a clean worktree",
                )

    def read(self, relative_path: str) -> bytes:
        relative = _validate_relative_path(relative_path)
        if self.mode == "release":
            return _git(
                self.root,
                ["show", f"{self.commit}:{relative.as_posix()}"],
                text=False,
            ).stdout
        return self._read_worktree(relative)

    def _read_worktree(self, relative: PurePosixPath) -> bytes:
        candidate = self.root
        for part in relative.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise PackagingError(
                    "source-symlink",
                    f"source input is a symlink: {relative.as_posix()}",
                )
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.root)
        except (OSError, ValueError) as error:
            raise PackagingError(
                "source-path-escapes",
                f"source input escapes or is missing: {relative.as_posix()}",
            ) from error
        if not resolved.is_file():
            raise PackagingError(
                "source-file-invalid",
                f"source input is not a regular file: {relative.as_posix()}",
            )
        return resolved.read_bytes()


def _load_yaml_bytes(content: bytes, path: str) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise PackagingError(
            "source-yaml-invalid",
            f"invalid YAML {path}: {error}",
        ) from error
    if not isinstance(value, Mapping):
        raise PackagingError(
            "source-yaml-invalid",
            f"YAML must be an object: {path}",
        )
    return value


def _load_registry(
    reader: _SourceReader,
) -> tuple[list[Mapping[str, Any]], list[str]]:
    try:
        schema = json.loads(reader.read(PROFILE_SCHEMA_PATH).decode("utf-8"))
        Draft202012Validator.check_schema(schema)
    except (UnicodeDecodeError, json.JSONDecodeError, SchemaError) as error:
        raise PackagingError("profile-schema-invalid", str(error)) from error
    validator = Draft202012Validator(schema)
    catalog = _load_yaml_bytes(
        reader.read(PROFILE_CATALOG_PATH),
        PROFILE_CATALOG_PATH,
    )
    if set(catalog) != {"schema_version", "profiles"}:
        raise PackagingError(
            "profile-catalog-invalid",
            "catalog has unknown or missing fields",
        )
    if catalog["schema_version"] != "1.0":
        raise PackagingError(
            "profile-catalog-invalid",
            "catalog schema_version must be 1.0",
        )
    entries = catalog.get("profiles")
    if not isinstance(entries, list) or not all(
        isinstance(item, str) for item in entries
    ):
        raise PackagingError(
            "profile-catalog-invalid",
            "catalog profiles must be paths",
        )
    if len({entry.casefold() for entry in entries}) != len(entries):
        raise PackagingError(
            "profile-catalog-invalid",
            "catalog profile paths must be case-insensitively unique",
        )

    profiles: list[Mapping[str, Any]] = []
    metadata_paths: list[str] = []
    for entry in entries:
        relative = PurePosixPath(entry)
        if (
            relative.parent != PurePosixPath(".")
            or relative.suffix != ".yaml"
            or "\\" in entry
            or ":" in entry
        ):
            raise PackagingError(
                "profile-catalog-invalid",
                f"invalid profile path: {entry}",
            )
        metadata_path = f"profiles/{relative.name}"
        profile = _load_yaml_bytes(reader.read(metadata_path), metadata_path)
        errors = sorted(
            validator.iter_errors(profile),
            key=lambda error: tuple(
                str(part) for part in error.absolute_path
            ),
        )
        if errors:
            raise PackagingError(
                "profile-schema-invalid",
                f"{metadata_path}: {errors[0].message}",
            )
        profiles.append(profile)
        metadata_paths.append(metadata_path)
    return profiles, metadata_paths


def _input_paths(
    profiles: Sequence[Mapping[str, Any]],
    metadata_paths: Sequence[str],
) -> list[str]:
    paths = {
        "LICENSE",
        MANIFEST_SCHEMA_PATH,
        PROFILE_SCHEMA_PATH,
        PROFILE_CATALOG_PATH,
        SKILL_PATH,
        ADAPTER_PATH,
        PROFILE_SELECTION_PATH,
        *CORE_REFERENCE_PATHS,
        *metadata_paths,
    }
    for profile in profiles:
        reference = profile.get("reference")
        if isinstance(reference, str):
            paths.add(reference)
        for manifest in profile["evidence"]["manifests"]:
            paths.add(manifest)
        for result in profile["evidence"]["results"]:
            paths.add(result["path"])
            paths.add(EVIDENCE_SCHEMA_PATH)
    return _sort_paths(list(paths))


def _decode_text(content: bytes, path: str) -> str:
    try:
        return (
            content.decode("utf-8")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
    except UnicodeDecodeError as error:
        raise PackagingError(
            "source-text-invalid",
            f"source text is not UTF-8: {path}",
        ) from error


def _package_name(profile_ids: Sequence[str]) -> str:
    return "clean-code-ai-" + "-".join(sorted(profile_ids))


def _render_skill(source: bytes, package_name: str) -> bytes:
    content = _decode_text(source, SKILL_PATH)
    replaced, count = re.subn(
        r"(?m)^name:\s+[^\n]+$",
        f"name: {package_name}",
        content,
        count=1,
    )
    if count != 1:
        raise PackagingError(
            "skill-template-invalid",
            "SKILL.md must contain one name field",
        )
    return replaced.encode("utf-8")


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _render_adapter(
    package_name: str,
    selected_profiles: Sequence[Mapping[str, Any]],
) -> bytes:
    display_suffix = " + ".join(
        profile["display_name"] for profile in selected_profiles
    )
    display_name = f"Clean Code AI {display_suffix}"
    short_description = (
        "Use conditional repository-aware Clean Code profile guidance"
    )
    default_prompt = (
        "Use $"
        + package_name
        + " for this repository change. Determine applicability by Changed Module; "
        "bundled profiles are conditional and Core Only remains valid. Preserve "
        "repository gates, behavior, risk controls, and authorization boundaries."
    )
    content = "\n".join(
        (
            "interface:",
            f"  display_name: {_yaml_string(display_name)}",
            f"  short_description: {_yaml_string(short_description)}",
            f"  default_prompt: {_yaml_string(default_prompt)}",
            "policy:",
            "  allow_implicit_invocation: false",
            "",
        )
    )
    return content.encode("utf-8")


def _render_selection(
    source: bytes,
    selected_profiles: Sequence[Mapping[str, Any]],
) -> bytes:
    content = _decode_text(source, PROFILE_SELECTION_PATH)
    try:
        generated = replace_generated_region(
            content,
            RUNTIME_MARKERS,
            render_runtime_index(selected_profiles),
        )
    except ValueError as error:
        raise PackagingError("runtime-index-invalid", str(error)) from error
    return generated.encode("utf-8")


def _package_files(
    source_inputs: Mapping[str, bytes],
    selected_profiles: Sequence[Mapping[str, Any]],
    package_name: str,
) -> dict[str, bytes]:
    files = {
        "SKILL.md": _render_skill(source_inputs[SKILL_PATH], package_name),
        "agents/openai.yaml": _render_adapter(
            package_name,
            selected_profiles,
        ),
        "references/profile-selection.md": _render_selection(
            source_inputs[PROFILE_SELECTION_PATH],
            selected_profiles,
        ),
        "LICENSE": source_inputs["LICENSE"],
    }
    for source_path in CORE_REFERENCE_PATHS:
        files[
            f"references/{PurePosixPath(source_path).name}"
        ] = source_inputs[source_path]
    for profile in selected_profiles:
        reference = profile["reference"]
        package_path = f"references/{PurePosixPath(reference).name}"
        if package_path in files:
            raise PackagingError(
                "package-path-duplicate",
                f"duplicate package path: {package_path}",
            )
        files[package_path] = source_inputs[reference]
    return files


def _validate_manifest(
    manifest: Mapping[str, Any],
    schema_bytes: bytes,
    inputs: Mapping[str, bytes],
    files: Mapping[str, bytes],
) -> None:
    try:
        schema = json.loads(schema_bytes.decode("utf-8"))
        Draft202012Validator.check_schema(schema)
    except (UnicodeDecodeError, json.JSONDecodeError, SchemaError) as error:
        raise PackagingError("manifest-schema-invalid", str(error)) from error
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise PackagingError("manifest-invalid", errors[0].message)
    if manifest["inputs"] != _digest_entries(inputs):
        raise PackagingError(
            "manifest-input-hash-invalid",
            "input hashes are not reproducible",
        )
    if manifest["files"] != _digest_entries(files):
        raise PackagingError(
            "manifest-file-hash-invalid",
            "file hashes are not reproducible",
        )
    without_digest = dict(manifest)
    digest = without_digest.pop("overall_digest")
    expected = hashlib.sha256(
        canonical_json_bytes(without_digest)
    ).hexdigest()
    if digest != expected:
        raise PackagingError(
            "manifest-overall-digest-invalid",
            "overall digest is invalid",
        )


def _write_exclusive(path: Path, content: bytes) -> None:
    created = False
    try:
        with path.open("xb") as stream:
            created = True
            stream.write(content)
    except BaseException:
        if created and path.exists():
            path.unlink()
        raise


def _create_output_directories(
    output: Path,
    created_directories: list[Path],
) -> None:
    missing: list[Path] = []
    current = output
    while not current.exists() and not current.is_symlink():
        missing.append(current)
        parent = current.parent
        if parent == current:
            raise FileNotFoundError(
                f"output path has no existing ancestor: {output}"
            )
        current = parent

    if current == output:
        raise FileExistsError(
            f"output directory already exists: {output}"
        )
    if current.is_symlink() or not current.is_dir():
        raise FileExistsError(
            f"output ancestor is not a physical directory: {current}"
        )

    for directory in reversed(missing):
        directory.mkdir()
        created_directories.append(directory)


def _write_package(
    output: Path,
    files: Mapping[str, bytes],
    manifest_bytes: bytes,
) -> None:
    created_files: list[Path] = []
    created_directories: list[Path] = []
    try:
        _create_output_directories(output, created_directories)
        entries = [
            *[(path, files[path]) for path in _sort_paths(list(files))],
            (PACKAGE_MANIFEST_PATH, manifest_bytes),
        ]
        for relative_path, content in entries:
            relative = _validate_relative_path(relative_path)
            parent = output
            for part in relative.parent.parts:
                parent = parent / part
                if not parent.exists():
                    parent.mkdir()
                    created_directories.append(parent)
                elif not parent.is_dir() or parent.is_symlink():
                    raise FileExistsError(
                        f"package directory path already exists: {parent}"
                    )
            destination = output.joinpath(*relative.parts)
            _write_exclusive(destination, content)
            created_files.append(destination)

        for relative_path, expected in entries:
            actual = output.joinpath(
                *PurePosixPath(relative_path).parts
            ).read_bytes()
            if actual != expected:
                raise OSError(
                    f"package write verification failed: {relative_path}"
                )
    except BaseException:
        for created_file in reversed(created_files):
            if created_file.exists() and created_file.is_file():
                created_file.unlink()
        for created_directory in sorted(
            created_directories,
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                created_directory.rmdir()
            except OSError:
                pass
        raise


def build_package(
    source_root: Path,
    output: Path,
    source_mode: Literal["release", "worktree"],
    profile_ids: Sequence[str],
) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise FileExistsError(
            f"output directory already exists: {output}"
        )

    reader = _SourceReader(source_root, source_mode)
    profiles, metadata_paths = _load_registry(reader)
    repository_diagnostics = validate_loaded_profiles(
        list(zip(metadata_paths, profiles, strict=True)),
        reader.read,
    )
    if repository_diagnostics:
        first = repository_diagnostics[0]
        raise PackagingError(
            "profile-registry-invalid",
            f"{first.path}:{first.field}:{first.code}: {first.message}",
        )
    profiles_by_id = {profile["id"]: profile for profile in profiles}
    composed_ids = compose_profiles(profiles_by_id, profile_ids)
    selected_profiles = [
        profiles_by_id[profile_id] for profile_id in composed_ids
    ]
    suite_versions = {
        profile["suite_version"] for profile in selected_profiles
    }
    if len(suite_versions) != 1:
        raise PackagingError(
            "suite-version-conflict",
            "selected profiles must use one suite version",
        )
    suite_version = next(iter(suite_versions))

    input_paths = _input_paths(profiles, metadata_paths)
    source_inputs = {path: reader.read(path) for path in input_paths}
    package_name = _package_name(composed_ids)
    files = _package_files(
        source_inputs,
        selected_profiles,
        package_name,
    )
    manifest = build_manifest(
        source_commit=reader.commit,
        source_mode=source_mode,
        suite_version=suite_version,
        profile_ids=composed_ids,
        inputs=source_inputs,
        files=files,
    )
    _validate_manifest(
        manifest,
        source_inputs[MANIFEST_SCHEMA_PATH],
        source_inputs,
        files,
    )
    _write_package(output, files, canonical_json_bytes(manifest))
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a specialist Agent Skill package."
    )
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--source-mode",
        required=True,
        choices=("release", "worktree"),
    )
    parser.add_argument("--profile", required=True, action="append")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    try:
        build_package(
            args.source_root,
            args.output,
            args.source_mode,
            args.profile,
        )
    except PackagingError as error:
        print(f"package:$:{error.code}: {error}")
        return 1
    except FileExistsError as error:
        print(f"package:$:output-exists: {error}")
        return 1
    except (OSError, subprocess.SubprocessError) as error:
        print(f"package:$:package-io-failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
