# Third-party licenses and provenance

This repository does not vendor third-party source code or dependency wheels. Python
packages are resolved separately by the installer and remain under their own licenses.
The following inventory describes direct dependencies declared in `pyproject.toml` at
the verified repository state; transitive packages must be reviewed from the concrete
environment lock or software bill of materials used for a release.

| Package | Use | Declared range | Upstream license |
|---|---|---:|---|
| FastAPI | Runtime web application | `>=0.110` | MIT |
| Jinja2 | Runtime HTML templates | `>=3.1` | BSD-3-Clause |
| Uvicorn | Optional standalone server | `>=0.27` | BSD-3-Clause |
| build | Development/package build | `>=1.2` | MIT |
| HTTPX | Development and tests | `>=0.27` | BSD-3-Clause |
| pytest | Tests | `>=8` | MIT |
| Ruff | Development linting | `>=0.12` | MIT |
| tomli | Python 3.10 development compatibility | `>=2` | MIT |
| Twine | Distribution validation | `>=6` | Apache-2.0 |

License identifiers summarize upstream package metadata; the upstream license texts
govern those packages. A future published release should generate and archive an exact,
versioned dependency inventory from its locked build environment.

## Repository assets and AI assistance

- `assets/banner.png` is tracked as repository artwork. Its source-rights record is not
  present in this repository, so owner confirmation remains mandatory before public or
  commercial use.
- The code and documentation include AI-assisted contributions that were reviewed and
  edited by a human maintainer. No third-party expression is intentionally incorporated
  as project-owned material; suspected matches must be reviewed before distribution.
- Runtime data, configured backend content and external model output are not part of the
  repository license merely because Unified GUI displays or routes them.
