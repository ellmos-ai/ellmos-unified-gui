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
`tests/test_control_shell_mount.py` prüft sieben Fälle. Ohne optionales
Paket sind vier Consumer-/Lite-Unitfälle weiterhin ausführbar; die drei
echten neutralen Integrationsfälle werden ausdrücklich übersprungen.
Es findet keine automatische Suche nach einem BACH-Checkout statt.

Der Abgleich von PR164, der genaue Backend-Vertrag und die Restgates stehen
im BACH-Delta unter `docs/REVIEW-T652-SHELL-EXTRACTION-20260930.md` und
`system/ocean_gui_shell/README.md`. Boards, Chat/Settings, Gesamtvollschale,
Deployment und vollständige Browser-/Geräteabnahme sind noch offen.
