# Windows ESP-IDF Environment

## Contents

1. [Core Invariants](#core-invariants)
2. [Discovery Order](#discovery-order)
3. [Classify the Installation](#classify-the-installation)
4. [Select the Project IDF](#select-the-project-idf)
5. [VS Code Consistency Check](#vs-code-consistency-check)
6. [Activate Without Contaminating the Parent Shell](#activate-without-contaminating-the-parent-shell)
7. [Validation Gate](#validation-gate)
8. [uv and Python Ownership](#uv-and-python-ownership)
9. [Failure Handling](#failure-handling)
10. [Required Scenarios](#required-scenarios)

Use this workflow before any Windows ESP-IDF build, flash, monitor, debug, `menuconfig`, component
manager, `esptool`, or other SDK-managed command. Discovery is read-only. Activation and commands
must run only after the intended project and IDF revision are known.

## Core Invariants

- Treat an ESP-IDF environment as one tuple: IDF checkout, IDF revision, tools root, IDF Python
  environment, target toolchain, and activation mechanism. Do not mix members from different tuples.
- Treat `PATH`, `IDF_PATH`, an EIM global selection, VS Code settings, and build metadata as evidence.
  Validate paths and versions before treating any of them as authoritative.
- Keep uv/general-purpose Python ownership separate from ESP-IDF ownership. ESP-IDF may use a Python
  installed by uv as the base interpreter while still owning a separate virtual environment.
- Fail closed. Do not build, flash, monitor, or debug with a partially valid environment.
- Use structured parsers for JSON and CMake metadata. Do not infer versions or paths with ad hoc
  substring matching when a structured field is available.

## Discovery Order

Collect evidence before changing the current shell:

1. Read the closest `AGENTS.md`, project documentation, CI configuration, and canonical build command.
2. Inspect explicit IDE/project configuration such as `.vscode/settings.json`. Relevant ESP-IDF
   extension keys include `idf.currentSetup` and older path/tools/Python keys.
3. Inspect `build/project_description.json` for `idf_path`, `git_revision`, `target`, and `c_compiler`.
   Inspect `build/CMakeCache.txt` for `IDF_TARGET`, `PYTHON`, and compiler paths when needed.
4. Inspect the current environment with `Get-ChildItem Env:IDF_*`, `Get-Command python`,
   `Get-Command idf.py`, and `Get-Command eim`. Do not activate anything yet.
5. Inventory bounded installation locations referenced by the evidence. Do not recursively search an
   entire drive when project, IDE, EIM, or build metadata already supplies candidate roots.

Build outputs describe the last configure and may be stale or copied. Confirm that their project path,
IDF checkout, target, Python, and compiler still exist before reusing them.

## Classify the Installation

| Installation owner | Strong evidence | Activation rule |
| --- | --- | --- |
| ESP-IDF Installation Manager (EIM) | `eim_idf.json` with an `idfInstalled` entry, `activationScript`, installation-specific PowerShell profiles, or an EIM executable | Parse the EIM registry and dot-source the chosen entry's `activationScript` |
| Standard ESP-IDF tools install | Checkout `export.ps1`, compatible `IDF_TOOLS_PATH` layout, and the Python/tool records expected by that checkout's `idf_tools.py` | Dot-source that checkout's `export.ps1` |
| Project/CI wrapper | Repository script or documented command explicitly sets the full tuple | Use the wrapper, then run the same validation gate |

For EIM, locate `eim_idf.json` through configured tools roots, IDE metadata, or the directory containing
the installation-specific profiles. Search only bounded candidate roots. Parse it with PowerShell
JSON APIs:

```powershell
$registry = Get-Content -Raw -LiteralPath $eimRegistryPath | ConvertFrom-Json
$install = $registry.idfInstalled | Where-Object {
    (Resolve-Path -LiteralPath $_.path).Path -eq (Resolve-Path -LiteralPath $requiredIdfPath).Path
}
$profile = $install.activationScript
```

Require exactly one matching, existing installation entry. Validate `path`, `python`,
`idfToolsPath`, and `activationScript` before activation. The registry's `idfSelectedId` is a global
preference, not project authority. A generated EIM profile may update that global preference when
activated; do not use this side effect as revision evidence.

Do not assume a checkout's generic `export.ps1` can consume an EIM tool registry. If it reports tools
missing while an EIM entry and version profile exist, first treat that as an activation/layout mismatch,
not as permission to install duplicate tools.

## Select the Project IDF

Resolve conflicts using this precedence:

1. IDF revision/path explicitly requested for the task.
2. Project-owned documentation, CI, or checked-in IDE configuration.
3. Valid, project-matching build metadata as evidence of the last known working tuple.
4. A currently activated tuple only when it agrees with the project.
5. EIM global selection or the newest installed IDF only as a last-resort candidate.

Canonicalize paths with `Resolve-Path` before comparison. Obtain the checkout version from
`git -C <idf-path> describe --tags --always` or the checkout's version metadata, then confirm it with
`idf.py --version` after activation. If high-priority sources disagree, report the conflict and stop
unless the task or project gives a defensible choice. Never silently choose the newest version.

## VS Code Consistency Check

Treat VS Code as another source of environment evidence, not as the owner of project SDK policy:

1. Identify the active VS Code Profile, then inspect its user settings and the project's
   `.vscode/settings.json`. Project-owned configuration and documented build commands take
   precedence over profile defaults.
2. Resolve ESP-IDF extension setup fields, explicit IDF/tools/Python paths, and environment variables
   to existing locations. Require them to belong to the same selected installation tuple.
3. For clangd, inspect the effective executable, arguments, project `.clangd`, and compilation
   database location. Confirm that `compile_commands.json` came from a build using the selected IDF
   checkout, target, and compiler.
4. When multiple C/C++ language-service extensions are enabled, verify which one owns diagnostics
   and completion for the workspace. Avoid duplicate indexing or conflicting diagnostics unless the
   project intentionally configures both.
5. Before flash or debug, verify the effective target, serial port, OpenOCD configuration, and debug
   adapter settings against the selected board. Never infer a port or target from a profile default.

Do not encode machine-local SDK paths, profile names, or extension release numbers in reusable
instructions. Keep reproducibility requirements in project documentation, CI, lock files, and
checked-in workspace configuration.

## Activate Without Contaminating the Parent Shell

Prefer a fresh child PowerShell for diagnostics and execution. Dot-source the selected activation
script and run all dependent commands in that same child process; environment changes do not persist
across separate processes.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `
  "& { . '<activation-script>'; Set-Location -LiteralPath '<project>'; idf.py --version }"
```

Replace placeholders with already validated literal paths and quote them safely. For EIM, use the
selected entry's matching `activationScript`. For a standard installation, use the selected
checkout's `export.ps1`. If diagnostics must run in the current shell, record the prior environment and
use the matching deactivation script when one is provided; do not rely on manually editing `PATH` back.

Do not activate multiple ESP-IDF profiles or a uv project environment on top of one another. Start a
new child shell when switching IDF versions.

## Validation Gate

Inside the activated child process, validate every row before running the requested SDK operation:

| Check | Pass condition |
| --- | --- |
| IDF checkout | `IDF_PATH` exists and canonically equals the selected checkout |
| IDF version | `idf.py --version` agrees with the selected/project version |
| IDF tools root | `IDF_TOOLS_PATH` exists and belongs to the selected installation tuple |
| Python identity | `python -c "import sys; print(sys.executable)"` resolves inside `IDF_PYTHON_ENV_PATH`; both paths exist |
| SDK command | `idf.py` invokes successfully; a PowerShell alias/function is acceptable when it binds the selected IDF Python and checkout |
| Target | Project configuration and reusable build metadata agree on `IDF_TARGET`, or a deliberate target change is documented |
| Toolchain | The target compiler selected by existing build metadata exists, or the expected compiler for a fresh configure resolves on `PATH` |
| Build tools | The activated `cmake` and `ninja` commands resolve and run |

Use `Get-Command -All` when duplicate commands are possible. Compare resolved executable paths, not
only version strings. Matching Python versions are insufficient: two Python 3.x executables can have
different packages and ownership.

If a build directory exists, compare its recorded IDF, Python, compiler, and target with the validated
tuple. Reconfigure or use a separate build directory when they differ; do not let stale CMake state
silently select another toolchain.

## uv and Python Ownership

uv can safely coexist with ESP-IDF. Normal arrangements include:

- uv manages the user's default Python while ESP-IDF owns a dedicated virtual environment.
- EIM creates its IDF virtual environment from a Python distribution originally installed by uv.
- A project uses uv for host-side tooling while firmware commands use the ESP-IDF environment.

Do not run `uv run idf.py`, install IDF requirements into the project's uv environment, or replace the
EIM/ESP-IDF virtual environment merely because uv's Python appears first on the parent `PATH`. Activate
the IDF-owned environment, then verify `sys.executable` and `IDF_PYTHON_ENV_PATH` agree.

## Failure Handling

Stop before build, flash, monitor, debug, or package installation when any of these occurs:

- No unique project-required IDF revision can be selected.
- The selected activation script, checkout, Python environment, or tools root is missing.
- `IDF_PATH`, `idf.py --version`, Python identity, target, or compiler disagree.
- Generic `export.ps1` reports missing tools for an installation identified as EIM-managed.
- The only apparent fix would create or mutate an environment whose owner is not yet known.

Report the conflicting evidence and the exact failing check. Do not run `install.ps1`,
`idf_tools.py install`, `pip install`, or `uv pip install` until the installation owner and intended
tuple are established. Installation and repair change persistent machine state and require explicit
scope from the user.

## Required Scenarios

Apply the workflow correctly in all of these cases:

- uv Python is first on the parent `PATH`, while EIM owns the project IDF environment.
- EIM has multiple IDF installations and its global selection differs from project metadata.
- A standard `.espressif` installation has no EIM registry and the checkout's `export.ps1` is valid.
- Existing build metadata identifies a complete tuple, but is accepted only after path and project checks.
- Activation or validation fails, so no build, flash, monitor, debug, or tool installation occurs.
