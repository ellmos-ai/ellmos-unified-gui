# SPDX-License-Identifier: MIT
"""skills-catalog-Adapter: strukturierte Skill-Neuanlage ueber `catalog.py`
(kanonischer Klon `C:\\_Local_DEV\\repos\\skills`).

Schliesst Ampel-Zeile 6 ("Skillgenerator mit Wizard", CORPORATE-LLM-KONZEPT
Sec. 2, Re-Check `SOVEREIGN_AMPEL_RECHECK_2026-08-17.md`): bisher lieferte
`p9_skills.py` nur Inventar + Intent-Matching (rein lesend, ControlCenterAdapter
gegen den MCP-Server); es gab keinen GUI-Weg, tatsaechlich einen neuen Skill
anzulegen. `skill-creator`/`skill-extractor` bleiben bewusst die konversationellen
Skills fuer INHALTLICHE Autorenschaft (Interview, Testfaelle, Subagent-Evals,
Beschreibungs-Optimierung per LLM-Loop) — das kann und soll ein zustandsloses
FastAPI-Panel nicht nachbauen. Was dieser Adapter WIRKLICH schliesst: den
strukturierten, deterministischen Teil (Geruest anlegen, Pflichtfelder
ausfuellen, S-Tests laufen lassen) — siehe `panels/p11_skill_wizard.py` fuer
die genaue Grenzziehung.

Wiederverwendung statt Neubau: `catalog.py create`/`quality` existieren bereits
und werden hier per Subprozess aufgerufen (nicht re-implementiert) --
`cmd_create`/`cmd_quality` rufen intern `sys.exit()`/`raise SystemExit` auf,
ein Direktimport wuerde also den GUI-Prozess selbst beenden. `parse_frontmatter`
dagegen ist eine reine Funktion (nie `sys.exit`) und wird direkt importiert --
sie ist die einzige Instanz, gegen die `set_description()` seinen eigenen
Schreibvorgang zurueckliest (Round-Trip-Beweis statt Annahme).
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from ..capabilities import Capability, HealthInfo
from ..config import SkillsCatalogConfig
from .base import AdapterError, BaseAdapter

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SkillsCatalogAdapter(BaseAdapter):
    name = "skills-catalog"
    label = "skills-catalog (Skill-Wizard)"

    def __init__(self, config: SkillsCatalogConfig | None = None) -> None:
        self.config = config or SkillsCatalogConfig()
        self._catalog_module: ModuleType | None = None
        self._ready = False

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _catalog_path(self) -> Path | None:
        if not self.config.repo_path:
            return None
        path = Path(self.config.repo_path).expanduser() / "catalog.py"
        return path if path.is_file() else None

    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            self._ready = self._catalog_path() is not None
            if self._ready:
                caps.add(Capability.SKILLS_CREATE)
        except Exception:  # noqa: BLE001 -- probe wirft nie
            self._ready = False
        return caps

    def health(self) -> HealthInfo:
        if self._ready:
            return HealthInfo("ok", str(self._catalog_path()))
        return HealthInfo("offline", f"catalog.py nicht gefunden unter {self.config.repo_path}")

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    def _skills_dir(self) -> Path:
        catalog = self._catalog_path()
        if catalog is None:
            raise AdapterError("skills_catalog_missing", str(self.config.repo_path))
        return catalog.parent / "skills"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        catalog = self._catalog_path()
        if catalog is None:
            raise AdapterError("skills_catalog_missing", str(self.config.repo_path))
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            return subprocess.run(
                [self.config.python_exe or sys.executable, str(catalog), *args],
                cwd=str(catalog.parent), env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.config.timeout_s, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterError("skills_catalog_timeout", f"{args[:1]} > {self.config.timeout_s}s") from exc

    def _parse_frontmatter_fn(self):
        """Laedt `parse_frontmatter` direkt aus dem echten catalog.py -- keine
        eigene YAML-Logik. Reine Funktion (siehe Modul-Docstring), deshalb
        anders als `create`/`quality` per Import statt Subprozess nutzbar."""
        if self._catalog_module is None:
            catalog = self._catalog_path()
            if catalog is None:
                raise AdapterError("skills_catalog_missing", str(self.config.repo_path))
            spec = importlib.util.spec_from_file_location("_skills_catalog_ro", catalog)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)
            self._catalog_module = module
        return self._catalog_module.parse_frontmatter

    # ------------------------------------------------------------------
    # Lesend
    # ------------------------------------------------------------------
    def categories(self) -> list[dict[str, Any]]:
        """Direkte Verzeichnis-Auflistung -- dieselbe Logik wie `cmd_categories`,
        aber ohne CLI-Text zu parsen (Subprozess+Stdout-Parsing waere fuer eine
        reine Verzeichnisliste unnoetig fragil)."""
        skills_dir = self._skills_dir()
        if not skills_dir.is_dir():
            return []
        cats = []
        for item in sorted(skills_dir.iterdir(), key=lambda p: p.name):
            if item.is_dir() and not item.name.startswith("_"):
                count = len(list(item.rglob("SKILL.md")))
                cats.append({"name": item.name, "count": count})
        return cats

    # ------------------------------------------------------------------
    # Schreibend (Aufrufer gated -- siehe Panel)
    # ------------------------------------------------------------------
    def create(self, skill_name: str, category: str, skill_type: str) -> dict[str, Any]:
        if not _NAME_RE.match(skill_name):
            raise AdapterError("invalid_name", "nur kebab-case (a-z, 0-9, Bindestriche), z. B. 'mein-neuer-skill'")
        if not category or "/" in category or ".." in category:
            raise AdapterError("invalid_category", repr(category))
        proc = self._run("create", skill_name, "-c", category, "-t", skill_type or "skill")
        if proc.returncode != 0:
            raise AdapterError("create_failed", (proc.stdout + proc.stderr).strip() or f"exit {proc.returncode}")
        skill_file = self._skills_dir() / category / skill_name / "SKILL.md"
        if not skill_file.is_file():
            # catalog.py meldete Erfolg (exit 0), aber die Datei fehlt -- lieber
            # das melden als eine "erfolgreiche" Anlage vortaeuschen, die keine ist.
            raise AdapterError("create_reported_ok_but_missing", str(skill_file))
        return {"name": skill_name, "category": category, "type": skill_type, "path": str(skill_file)}

    def set_description(self, skill_name: str, category: str, description: str) -> dict[str, Any]:
        """Ersetzt den `description: >`-Block per Read-Modify-Write und liest
        danach ueber `parse_frontmatter()` zurueck, um den echten Rundlauf zu
        beweisen statt nur "die Datei enthaelt meinen String" zu pruefen --
        genau der Unterschied, den ein naiver String-Replace bei eingebetteten
        Zeilenumbruechen verfehlen wuerde."""
        skill_file = self._skills_dir() / category / skill_name / "SKILL.md"
        if not skill_file.is_file():
            raise AdapterError("skill_not_found", str(skill_file))
        text = description.strip()
        if not text:
            raise AdapterError("empty_description", "")
        # Ein YAML-"folded scalar" (>) faltet ohnehin jeden Zeilenumbruch zu
        # einem Leerzeichen -- eingebettete \n im Nutzertext werden deshalb
        # VORHER selbst gefaltet, statt roh in eine Datei zu schreiben, deren
        # Folgezeilen dann nicht mehr eingerueckt waeren (siehe Docstring).
        folded = re.sub(r"\s+", " ", text).strip()

        original = skill_file.read_text(encoding="utf-8")
        new_block = self._render_description_block(folded)
        updated = self._replace_description_block(original, new_block)
        if updated is None:
            raise AdapterError("no_description_field", "SKILL.md hat kein `description:`-Feld im Frontmatter")

        skill_file.write_text(updated, encoding="utf-8")
        try:
            parsed = self._parse_frontmatter_fn()(skill_file)
        except Exception as exc:  # noqa: BLE001 -- Rueckschreiben bei jedem Parserfehler
            skill_file.write_text(original, encoding="utf-8")
            raise AdapterError("frontmatter_reparse_failed", str(exc)) from exc

        if parsed is None or parsed.get("description") != folded:
            skill_file.write_text(original, encoding="utf-8")
            raise AdapterError(
                "description_roundtrip_mismatch",
                f"catalog.py's eigener parse_frontmatter() lieferte {parsed.get('description') if parsed else None!r}, "
                f"erwartet {folded!r} -- Schreibvorgang zurueckgerollt",
            )
        return {"name": skill_name, "category": category, "description": folded}

    @staticmethod
    def _render_description_block(folded_text: str, width: int = 96) -> str:
        """`description: >` + eine oder mehrere 2-Leerzeichen-eingerueckte
        Zeilen. Mehrere Zeilen sind rein kosmetisch (parse_frontmatter faltet
        sie ohnehin wieder zu einem String) -- Softwrap fuer Lesbarkeit in der
        Datei, kein semantischer Unterschied zu einer einzigen langen Zeile."""
        words = folded_text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        body = "\n".join(f"  {line}" for line in lines)
        return f"description: >\n{body}\n"

    @staticmethod
    def _replace_description_block(text: str, new_block: str) -> str | None:
        """Ersetzt `description: >` samt aller eingerueckten Folgezeilen (bis
        zur naechsten Zeile auf Spalte 0) durch `new_block`. Arbeitet nur
        innerhalb des Frontmatter-Bereichs (zwischen den ersten zwei `---`)."""
        fm_match = re.match(r"^(---\s*\n)(.*?\n)(---.*)$", text, re.DOTALL)
        if not fm_match:
            return None
        head, frontmatter, tail = fm_match.groups()

        desc_match = re.search(r"^description:\s*>\s*\n((?:[ \t]+\S.*\n?)*)", frontmatter, re.MULTILINE)
        if not desc_match:
            return None
        new_frontmatter = frontmatter[:desc_match.start()] + new_block + frontmatter[desc_match.end():]
        return head + new_frontmatter + tail

    def quality(self, skill_name: str) -> dict[str, Any]:
        """Fuehrt NUR die S-Tests aus (`--type static`) -- automatisierte
        Frontmatter-/Struktur-Pruefung, kein LLM-Judge-Aufruf, kein Netzwerk,
        deterministisch und darum vertretbar aus einem Web-Panel heraus
        auszuloesen. `catalog.py quality --run` startet das intern selbst."""
        proc = self._run("quality", skill_name, "--run")
        results_dir = Path(self.config.repo_path).expanduser() / "testing" / "results" / skill_name
        results = sorted(results_dir.glob("*.json"), reverse=True) if results_dir.is_dir() else []
        if not results:
            raise AdapterError(
                "quality_no_result",
                (proc.stdout + proc.stderr).strip() or f"kein Ergebnis unter {results_dir}",
            )
        import json
        data = json.loads(results[0].read_text(encoding="utf-8"))
        return {
            "name": skill_name,
            "quality_score": data.get("quality_score"),
            "rating": data.get("rating"),
            "dimensions": data.get("dimensions", {}),
            "exit_code": proc.returncode,
        }
