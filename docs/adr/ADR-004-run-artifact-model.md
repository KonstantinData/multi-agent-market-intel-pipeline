# ADR-004: Run‑Artifact‑Modell

**Status:** Angenommen

## Hintergrund

Die Pipeline erzeugt viele Zwischen- und Endergebnisse. Ohne ein klar definiertes Artefakt‑Modell lassen sich Runs schwer reproduzieren, vergleichen oder auditieren. Außerdem müssen Artefakte versioniert werden, um Änderungen an Daten oder Contracts transparent zu machen.

## Entscheidung

Wir nutzen ein **Run‑Artifact‑Modell**:

- **Run‑ID** als übergeordnete Klammer für alle Artefakte eines Pipeline‑Durchlaufs.
- **Artefakt‑Typen** (z. B. raw, normalized, enriched, merged, report) mit klarer Struktur.
- **Versionierte Metadaten** (Contract‑Version, Erstellungszeit, Upstream‑Inputs).
- **Immutable Artefakte**: einmal erzeugt, werden Artefakte nicht überschrieben; neue Runs erzeugen neue Versionen.

## Konsequenzen

- **Reproduzierbarkeit:** jeder Run ist nachvollziehbar; Inputs und Outputs sind eindeutig verknüpft.
- **Vergleichbarkeit:** unterschiedliche Runs können diff‑fähig und auditierbar verglichen werden.
- **Speicherbedarf:** mehr Artefakte bedeuten höhere Storage‑Kosten.
- **Disziplin:** alle Schritte müssen ihre Artefakte sauber deklarieren und ablegen.

## Alternativen / Non‑Goals

- **Alternative:** Überschreiben von Artefakten (latest‑only). Abgelehnt wegen fehlender Nachvollziehbarkeit.
- **Alternative:** rein ad‑hoc Speicherung ohne Metadaten. Abgelehnt wegen mangelnder Auditierbarkeit.
- **Non‑Goal:** Vollständige Data‑Lineage für jedes einzelne Feld. Das Modell fokussiert auf Artefakt‑Ebene.
