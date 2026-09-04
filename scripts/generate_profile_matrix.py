from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

if __package__:
    from .validate_profiles import (
        Diagnostic,
        load_registry,
        profile_is_available,
    )
else:
    from validate_profiles import Diagnostic, load_registry, profile_is_available


README_PATH = Path("README.md")
RUNTIME_PATH = Path(
    "clean-code-ai-collaboration/references/profile-selection.md"
)
README_MARKERS = (
    "<!-- profile-matrix:generated:start -->",
    "<!-- profile-matrix:generated:end -->",
)
RUNTIME_MARKERS = (
    "<!-- runtime-profile-index:generated:start -->",
    "<!-- runtime-profile-index:generated:end -->",
)


def replace_generated_region(
    document: str,
    markers: tuple[str, str],
    body: str,
) -> str:
    """Replace one well-formed generated region without changing its surroundings."""

    start_marker, end_marker = markers
    if document.count(start_marker) != 1 or document.count(end_marker) != 1:
        raise ValueError("generated markers must each appear exactly once")
    start_index = document.index(start_marker)
    end_index = document.index(end_marker)
    if start_index >= end_index:
        raise ValueError("generated start marker must precede its end marker")
    start_end = start_index + len(start_marker)
    normalized_body = body.strip("\n")
    return (
        document[:start_end]
        + "\n"
        + normalized_body
        + "\n"
        + document[end_index:]
    )


def _display_value(values: Sequence[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def _display_manifests(manifests: Sequence[Mapping[str, Any]]) -> str:
    if not manifests:
        return "none"
    return ", ".join(
        f"`{manifest['pattern']}` ({manifest['boundary']})"
        for manifest in manifests
    )


def render_profile_matrix(profiles: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "| Profile | Kind | Status | Reference | Benchmark |",
        "| --- | --- | --- | --- | --- |",
    ]
    for profile in profiles:
        status = profile["status"]
        reference = profile.get("reference")
        reference_cell = (
            f"[Open]({reference})"
            if profile_is_available(profile)
            else "Not available"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    profile["display_name"],
                    profile["kind"],
                    status,
                    reference_cell,
                    profile["evidence"]["benchmark_status"],
                )
            )
            + " |"
        )
    return "\n".join(lines)


def render_runtime_index(profiles: Sequence[Mapping[str, Any]]) -> str:
    sections: list[str] = []
    for profile in profiles:
        status = profile["status"]
        availability = (
            "available" if profile_is_available(profile) else "unavailable"
        )
        reference = profile.get("reference")
        reference_value = (
            f"[{Path(reference).name}]({Path(reference).name})"
            if reference and availability == "available"
            else "Not available"
        )
        detection = profile["detection"]
        composition = profile["composition"]
        lines = [
            f"### {profile['display_name']}",
            "",
            f"- ID: `{profile['id']}`",
            f"- Kind: `{profile['kind']}`",
            f"- Status / Availability: `{status}` / `{availability}`",
            f"- Reference: {reference_value}",
            f"- Load Order: `{profile['routing']['load_order']}`",
            f"- Owning Manifests: {_display_manifests(detection['owning_manifests'])}",
            f"- Supporting Files: {_display_value(detection['supporting_files'])}",
            f"- Extensions: {_display_value(detection['file_extensions'])}",
            "- Candidate Dependencies: "
            + _display_value(detection["dependency_markers"]),
            "- Supporting Dependencies: "
            + _display_value(detection["supporting_dependencies"]),
            f"- Requires: {_display_value(composition['requires'])}",
            f"- Recommends: {_display_value(composition['recommends'])}",
            f"- Conflicts: {_display_value(composition['conflicts'])}",
            "- Evidence Status: "
            + f"`{profile['evidence']['benchmark_status']}`",
        ]
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def synchronize_generated_regions(
    source_root: Path,
    check: bool,
) -> Sequence[Diagnostic]:
    root = source_root.resolve()
    try:
        profiles = load_registry(root)
    except (OSError, ValueError, yaml.YAMLError) as error:
        return (
            Diagnostic(
                "profiles/catalog.yaml",
                "$",
                "catalog-invalid",
                str(error),
            ),
        )

    documents = (
        (README_PATH, README_MARKERS, render_profile_matrix(profiles)),
        (RUNTIME_PATH, RUNTIME_MARKERS, render_runtime_index(profiles)),
    )
    updates: list[tuple[Path, str]] = []
    diagnostics: list[Diagnostic] = []
    for relative_path, markers, body in documents:
        path = root / relative_path
        try:
            current = path.read_text(encoding="utf-8")
            generated = replace_generated_region(current, markers, body)
        except (OSError, UnicodeError, ValueError) as error:
            diagnostics.append(
                Diagnostic(
                    relative_path.as_posix(),
                    "$",
                    "generated-marker-invalid",
                    str(error),
                )
            )
            continue
        if generated == current:
            continue
        if check:
            diagnostics.append(
                Diagnostic(
                    relative_path.as_posix(),
                    "$",
                    "generated-drift",
                    "generated region is out of date",
                )
            )
        else:
            updates.append((path, generated))

    if diagnostics:
        return tuple(sorted(diagnostics))
    for path, generated in updates:
        path.write_text(generated, encoding="utf-8", newline="\n")
    return ()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize profile documentation.")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    diagnostics = synchronize_generated_regions(args.source_root, args.check)
    for diagnostic in diagnostics:
        print(
            f"{diagnostic.path}:{diagnostic.field}:{diagnostic.code}: "
            f"{diagnostic.message}"
        )
    return 1 if diagnostics else 0


if __name__ == "__main__":
    raise SystemExit(main())
