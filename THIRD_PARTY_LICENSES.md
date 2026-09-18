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

- `assets/banner.png` is tracked as repository artwork. It was generated for this
  repository and carries no third-party source material. Provenance record: commit
  `772e389a562234f96c4c37cd5b2a4ca513e235b3` ("feat(banner): generate and embed missing
  banner image", 2026-07-30), authored by the project maintainer; the `[G]` marker in that
  commit subject denotes generation by the project's own AI assistant under the house
  convention, not an imported work. No stock library, no external commission and no
  third-party licence applies. The file has never been replaced since; `git log --follow
  -- assets/banner.png` returns this single commit. Reused elsewhere it follows the
  repository licence in `LICENSE`.
- The code and documentation include AI-assisted contributions that were reviewed and
  edited by a human maintainer. No third-party expression is intentionally incorporated
  as project-owned material; suspected matches must be reviewed before distribution.
- Runtime data, configured backend content and external model output are not part of the
  repository license merely because Unified GUI displays or routes them.

## Governance and operational invariants

The following invariants define the operational and security perimeter for ellmos Unified GUI:

| Invariant | Scope | Operational guarantee | Verification evidence |
|---|---|---|---|
| `INV-LOCAL-01` | Network Privacy | 100% Local-First / Zero-Egress: Server binds to `127.0.0.1`; zero outbound tracking or telemetry. | AST inspections; `tests/test_degradation.py` |
| `INV-CANON-02` | Data Ownership | Single Data Canon: No duplicate domain database; views and delegates directly to canonical backends. | Architectural audit; zero local SQLite schemas |
| `INV-PROBE-03` | Lifecycle | Dynamic Capability Probing: Panels activate only when `probe()` validates backend availability within 2s. | `src/unified_gui/capabilities.py`; 15 panel tests |
| `INV-AUDIT-04` | Compliance | Append-Only JSONL Audit Trail: Every state-changing request (POST/PUT/PATCH/DELETE) is logged. | `src/unified_gui/audit_log.py`; `tests/test_audit_integration.py` |
| `INV-LOCK-05` | Safety | Pre-Flight Permission and Lock Enforcement: Write routes check locks and permissions fail-closed. | `tests/test_p5_role_gating.py`; `LOCK.permissions.json` |
| `INV-INJECT-06` | Security | Untrusted Content Protection: External strings are rendered exclusively via safe text assignments (`textContent`). | `tests/test_p15_messages_panel.py`; template audits |
| `INV-MOUNT-07` | Embedding | Dual-Mode Embedding Parity: Identical panel features available in standalone mode or mounted sub-app. | `src/unified_gui/web/app.py`; `mount()` tests |
| `INV-HOST-08` | Portability | Host-Neutral Paths: Standardized `~` expansion and cascading hostname configurations. | `src/unified_gui/config.py`; `tests/test_p8_console_root.py` |
| `INV-ZERO-09` | Simplicity | Zero Frontend Build Overhead: Pure FastAPI + Jinja2 + HTMX; no node/npm build dependencies. | Repository file inventory; zero package.json |
| `INV-SLA-10` | Security SLA | 48-Hour Acknowledgment & 5-Day Triage: Formal incident response commitments for security reports. | `SECURITY.md`; maintainer triage policy |
