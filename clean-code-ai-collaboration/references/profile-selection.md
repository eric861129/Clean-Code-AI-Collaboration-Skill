# Profile Selection

## Use This Reference When

Use this reference for repository code changes where language or framework semantics may change the approach, behavior boundary, or validation.

## Changed Module Discovery

Group candidate changed files by their nearest owning manifest. Prefer the shortest directory distance, then project over package over workspace, then metadata order. Root evidence is supplemental.

## Candidate Detection

Language extensions are primary signals. Framework syntax is auxiliary; a framework candidate requires its dependency marker or explicit repository policy.

## Availability and Composition

Bundled means available, not automatically applied. Reject planned, deprecated, missing-reference, inapplicable, conflicted, or incomplete profiles. Expand requires transitively; treat recommends as advice only. Use Core Only when no applicable profile remains.

## Explicit Selection

Honor a valid explicit profile or Core Only request, but never use explicit selection to bypass availability, applicability, dependency, conflict, risk, or authorization gates.

## Stage Evidence

Planning uses Expected Diff. Implementation compares Expected and Actual Diff. Review uses Actual Diff first and reports deviations.

## Output Additions

Standard output records Profiles Applied and Profile Basis per Changed Module. Full Audit records references, facts, and unknowns in the existing sections. Core Only records Profiles Applied: none.

## Runtime Profile Index

<!-- runtime-profile-index:generated:start -->
### C# / .NET

- ID: `csharp`
- Kind: `language`
- Status / Availability: `experimental` / `available`
- Reference: [language-csharp.md](language-csharp.md)
- Load Order: `100`
- Owning Manifests: `*.csproj` (project)
- Supporting Files: `*.sln`, `*.slnx`, `Directory.Build.props`, `Directory.Build.targets`, `global.json`
- Extensions: `.cs`
- Candidate Dependencies: none
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`

### Python

- ID: `python`
- Kind: `language`
- Status / Availability: `experimental` / `available`
- Reference: [language-python.md](language-python.md)
- Load Order: `100`
- Owning Manifests: `pyproject.toml` (project), `setup.py` (project), `setup.cfg` (project)
- Supporting Files: `requirements*.txt`, `Pipfile`, `poetry.lock`, `uv.lock`
- Extensions: `.py`, `.pyi`
- Candidate Dependencies: none
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`

### TypeScript

- ID: `typescript`
- Kind: `language`
- Status / Availability: `planned` / `unavailable`
- Reference: Not available
- Load Order: `100`
- Owning Manifests: `package.json` (package), `tsconfig.json` (project), `tsconfig.*.json` (project)
- Supporting Files: none
- Extensions: `.ts`, `.tsx`, `.mts`, `.cts`
- Candidate Dependencies: none
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`

### React

- ID: `react`
- Kind: `framework`
- Status / Availability: `planned` / `unavailable`
- Reference: Not available
- Load Order: `200`
- Owning Manifests: `package.json` (package)
- Supporting Files: none
- Extensions: `.jsx`, `.tsx`
- Candidate Dependencies: `react`
- Supporting Dependencies: `react-dom`, `react-native`
- Requires: none
- Recommends: `typescript`
- Conflicts: none
- Evidence Status: `not_started`

### Go

- ID: `go`
- Kind: `language`
- Status / Availability: `planned` / `unavailable`
- Reference: Not available
- Load Order: `100`
- Owning Manifests: `go.mod` (project)
- Supporting Files: `go.work`
- Extensions: `.go`
- Candidate Dependencies: none
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`

### Rust

- ID: `rust`
- Kind: `language`
- Status / Availability: `planned` / `unavailable`
- Reference: Not available
- Load Order: `100`
- Owning Manifests: `Cargo.toml` (project)
- Supporting Files: `Cargo.lock`
- Extensions: `.rs`
- Candidate Dependencies: none
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`

### Java

- ID: `java`
- Kind: `language`
- Status / Availability: `planned` / `unavailable`
- Reference: Not available
- Load Order: `100`
- Owning Manifests: `pom.xml` (project), `build.gradle` (project), `build.gradle.kts` (project)
- Supporting Files: `settings.gradle`, `settings.gradle.kts`
- Extensions: `.java`
- Candidate Dependencies: none
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`

### Vue

- ID: `vue`
- Kind: `framework`
- Status / Availability: `planned` / `unavailable`
- Reference: Not available
- Load Order: `200`
- Owning Manifests: `package.json` (package)
- Supporting Files: none
- Extensions: `.vue`
- Candidate Dependencies: `vue`
- Supporting Dependencies: none
- Requires: none
- Recommends: none
- Conflicts: none
- Evidence Status: `not_started`
<!-- runtime-profile-index:generated:end -->
