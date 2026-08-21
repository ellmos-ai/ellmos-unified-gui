# EU AI Act component note / Komponentennotiz zur EU-KI-Verordnung

## English

### Component boundary

Unified GUI is a deterministic operator interface. It does not contain, train or serve an
AI model and does not independently determine an outcome. Capability adapters can display
or trigger functions of separately configured model and agent backends. The intended
purpose, provider/deployer roles and legal classification therefore arise from the
deployed system and use case, not from this user-interface package alone.

### Intended and excluded use

The component is intended for authenticated human operators who inspect and control
existing backends. It is not intended to autonomously make or execute decisions about
employment, education, access to essential services, credit, health care, law
enforcement, migration, justice or other high-impact rights. A deployment in those
contexts requires a separate system-level legal, risk and conformity assessment.

### Transparency, oversight and records

An integrating host should identify AI-generated content where required, expose the
responsible model/backend, preserve meaningful human review and apply least-privilege
authorization to write actions. The built-in JSONL audit log is best-effort operational
telemetry; it is not tamper-proof and is not by itself a compliance record. Backend
privacy, logging, retention, security and incident duties remain with the deployed
system. Reassess this boundary before hosting the console for third parties or changing
its intended purpose.

## Deutsch

### Komponentengrenze

Unified GUI ist eine deterministische Bedienoberfläche. Sie enthält, trainiert und
betreibt kein KI-Modell und bestimmt keine Ergebnisse selbstständig. Capability-Adapter
können Funktionen getrennt konfigurierter Modell- und Agenten-Backends anzeigen oder
auslösen. Zweckbestimmung, Anbieter- und Betreiberrolle sowie die rechtliche Einordnung
ergeben sich deshalb aus dem eingesetzten Gesamtsystem und seinem Anwendungsfall, nicht
allein aus diesem Oberflächenpaket.

### Bestimmungsgemäße und ausgeschlossene Nutzung

Die Komponente ist für authentifizierte menschliche Operatoren bestimmt, die bestehende
Backends prüfen und steuern. Sie ist nicht dazu bestimmt, Entscheidungen über Arbeit,
Bildung, Zugang zu wesentlichen Diensten, Kredit, Gesundheitsversorgung,
Strafverfolgung, Migration, Justiz oder andere grundrechtsrelevante Bereiche autonom zu
treffen oder auszuführen. Ein Einsatz in solchen Kontexten verlangt eine eigenständige
rechtliche, Risiko- und Konformitätsprüfung des Gesamtsystems.

### Transparenz, Aufsicht und Aufzeichnungen

Der einbettende Host soll KI-generierte Inhalte kennzeichnen, soweit dies erforderlich
ist, das verantwortliche Modell beziehungsweise Backend sichtbar machen, eine sinnvolle
menschliche Prüfung erhalten und Schreibaktionen nach dem Prinzip der geringsten Rechte
autorisieren. Das eingebaute JSONL-Audit-Log ist bestmögliche Betriebstelemetrie; es ist
nicht manipulationssicher und allein kein Konformitätsnachweis. Datenschutz, Logging,
Aufbewahrung, Sicherheit und Incident-Pflichten der Backends bleiben Aufgabe des
eingesetzten Gesamtsystems. Vor einem Betrieb für Dritte oder einer geänderten
Zweckbestimmung ist diese Abgrenzung neu zu prüfen.
