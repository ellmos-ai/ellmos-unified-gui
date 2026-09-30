# Optionaler Consumer der neutralen Activity-Schale

session: 01a0f189-21d6-7851-a075-0aab0e3ebe77 | codex-gui-program@ASUS-GEI | 2026-09-30

Die bisherigen `create_app()`- und `mount()`-Funktionen bleiben die Lite-GUI.
Die BACH-stämmige Vollschale liegt in einem getrennten Paket; zunächst ist nur
die Activity-/Slots-/Worker-Ressource daraus importierbar. Eine Installation
der Lite-GUI benötigt weder dieses Paket noch BACH.

Bei ausdrücklich vorhandenem `ocean_gui_shell`:

```python
from unified_gui import create_control_shell_app, mount_control_shell

standalone = create_control_shell_app(control_api="/backend/api")
mount_control_shell(host_app, prefix="/ocean", control_api="/backend/api")
```

Die Factory und der Mount sind standardmäßig nur lesend. `read_only=False`
setzt eine ausdrücklich konfigurierte API-Basis voraus und aktiviert nur
die Möglichkeit einer Tokenprüfung im gemeinsamen Client. Der bestehende
Backend-Guard autorisiert weiterhin jeden Befehl; gültige Authentifizierung
ist kein Ersatz für Befehls- oder Zuweisungsrechte. Der Consumer fügt keine
Proxy-/Backendrouten und keine gespeicherten Credentials hinzu.
Ein fehlendes Backend wird auf eine reservierte nicht konfigurierte Basis
abgebildet. Fremde Browser-Ursprünge benötigen die bestehende Backendfreigabe.
Standalone hat den vorhandenen Local-Guard, beim Mount schützt der Host die
Sub-App. Kein eigener Login und keine gelockerte Origin-/CORS-Policy.

Branding wird je App kopiert; mehrere Mounts beeinflussen sich nicht.
Navigation erhält den jeweiligen Mountpräfix. Die gemeinsame Ressource
enthält ihr CSS und JavaScript vollständig; es gibt keine BACH-Static-Pfade
oder zusätzlichen Asset-Fork im Lite-Repo.

## Reproduzierbarer Nachweis

Für den expliziten lokalen Integrationslauf beide Quellverzeichnisse an
`PYTHONPATH` übergeben: dieses Repo `src` und der geprüfte BACH-Worktree
`system` (oder das unabhängig installierte neutrale Paket).
`tests/test_control_shell_mount.py` prüft elf Fälle. Ohne optionales
Paket sind acht Consumer-/Lite-/CI-Unitfälle weiterhin ausführbar; die drei
echten neutralen Integrationsfälle werden ausdrücklich übersprungen.
Es findet keine automatische Suche nach einem BACH-Checkout statt.

Mit `UNIFIED_GUI_REQUIRE_CONTROL_SHELL=1` werden fehlende neutrale Pakete
oder BACH-Consumer zu Fehlern. Der vorbereitete Job in
`CONTROL-SHELL-CI-PIN-DRAFT.yml` prüft den genauen Quellcommit, installiert
ausschließlich das unabhängige Paket ohne BACH-Runtime-Abhängigkeiten und
verlangt elf tatsächlich ausgeführte Tests ohne Skip. Das installierte Paket
wird vor dem ausdrücklich geladenen BACH-Branding-Consumer importiert; eine
Quellkopie darf den Installationsnachweis nicht ersetzen.

Dieser Job ist ein **inaktiver, nicht veröffentlichter Entwurf**. Sein
SHA `973e8c0edd178ca04deee47658d67a389e19a543` wurde unabhängig lokal geprüft,
ist aber noch kein bestätigter öffentlicher Paketpin. Vor Aktivierung sind
der tatsächliche BACH-Shell-PR, dessen Integration und die Erreichbarkeit des
endgültigen unveränderlichen Commits erneut zu belegen. Der bestehende
Lite-CI-Workflow bleibt unverändert.

Lokaler Autorencheck vom 30.09.2026: Das separat gebaute geprüfte Wheel
`ocean_gui_shell-0.1.0-py3-none-any.whl` (SHA256
`b955fdc6d509fc3943a8c33a8aaad029497c023c5ff4eae2de50e8d5f73f41ef`)
wurde mit `pip install --no-index --no-deps --target` in einen eigenen
Tempbereich installiert. Mit verpflichtendem Modus bestanden **11 Tests,
keine Skips**, einschließlich der tatsächlichen BACH-/Mount-Parität.
Metadaten haben keine Runtime-Abhängigkeiten; der verwendete Modulpfad blieb
der installierte Paketpfad und keine BACH-Backendmodule wurden geladen.
Ohne dieses optionale Paket scheiterte ein frischer separater Lauf wie
erwartet mit **RC 1, acht bestanden und drei Importfehlern, null Skips**.
Das ist ein lokaler Gegenbeleg zum unbeabsichtigt grünen Integrationslauf,
kein Nachweis ausgeführter GitHub-CI. Ruff, YAML-Parse und unveränderter
aktiver Lite-Workflow wurden ebenfalls geprüft.

Der Abgleich von PR164, der genaue Backend-Vertrag und die Restgates stehen
im BACH-Delta unter `docs/REVIEW-T652-SHELL-EXTRACTION-20260930.md` und
`system/ocean_gui_shell/README.md`. Boards, Chat/Settings, Gesamtvollschale,
Deployment und vollständige Browser-/Geräteabnahme sind noch offen.
