// Cypher-Implementierung der Benchmark-Queries T1-T7.
// Siehe docs/konzept.md Abschnitt 4 fuer die Fragestellungen.
//
// Kernlogik: bewusst von euch zu schreiben (Lernmodus, siehe CLAUDE.md).
// Wichtig: Jede Query muss fachlich identische Ergebnisse liefern wie die
// entsprechende SQL-Query in postgres/queries.sql.

// T1: Person anhand ID suchen (Baseline / einfacher Lookup)
// TODO

// T2: Direkte Kontakte einer Person (1-Hop)
// TODO

// T3: Kontakte zweiten Grades (2-Hop)
// TODO

// T4: Alle Personen bis Tiefe 4
// TODO

// T5: Kuerzester Pfad zwischen zwei Personen
// Hinweis aus dem Konzept als Ausgangspunkt:
// MATCH (p:Person {id: $id})-[:KNOWS*1..4]-(other)
// RETURN DISTINCT other
// TODO: an die tatsaechliche Fragestellung (kuerzester Pfad) anpassen

// T6: Gemeinsame Kontakte zweier Personen
// TODO

// T7: Skalierung (wird auf Teilmengen/anderem Datensatz wiederholt, siehe Fairness-Punkt 6)
// TODO
