# Projekt: Graphdatenbank vs. relationale Datenbank

Studentisches Teamprojekt (2 Personen). Vergleich PostgreSQL vs. Neo4j
mit SNAP-Datensätzen. Konzept: docs/konzept.md

## Lernmodus – WICHTIG
Wir wollen lernen, nicht nur fertigen Code bekommen.
- Arbeite schrittweise: immer nur EIN Schritt, dann warten.
- Erkläre vor jedem Schritt WAS wir tun und WARUM (kurz, auf Deutsch).
- Schreibe Kernlogik (SQL-Queries, Cypher-Queries, Messlogik) NICHT selbst.
  Gib uns stattdessen Hinweise, Struktur oder Lückencode mit TODOs,
  und reviewe dann unsere Lösung.
- Boilerplate (Docker-Config, Dateistruktur, Plot-Code) darfst du schreiben,
  aber erkläre die wichtigen Zeilen.
- Stelle uns gelegentlich Verständnisfragen, bevor wir weitergehen.
- Weise auf Fairness-Probleme im Benchmark aktiv hin.

## Konventionen
- Python für Import & Benchmark
- Commits klein und aussagekräftig, Arbeit auf Feature-Branches
- Messwerte als CSV in results/