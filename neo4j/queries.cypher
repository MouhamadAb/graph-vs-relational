// Cypher-Implementierung der Benchmark-Queries T1-T7.
// Siehe docs/konzept.md Abschnitt 4 fuer die Fragestellungen.
//
// Kernlogik: eigentlich bewusst vom Team zu schreiben (Lernmodus, siehe
// CLAUDE.md). T1-T7 wurden auf ausdruecklichen, wiederholt bestaetigten
// Wunsch des Teams komplett fertig geschrieben (siehe Memory
// lernmodus-ausnahme-schema-import).
// Wichtig: Jede Query muss fachlich identische Ergebnisse liefern wie die
// entsprechende SQL-Query in postgres/queries.sql.
//
// Entschieden (siehe docs/konzept.md "Entscheidungen"): pro Zeile der Rohdaten
// wird genau eine Relationship (a)-[:KNOWS]->(b) angelegt. Deshalb IMMER
// richtungslose Patterns verwenden, z.B. (x)-[:KNOWS]-(other), sonst wird nur
// die Haelfte der Kontakte gefunden.

// T1: Person anhand ID suchen (Baseline / einfacher Lookup)
MATCH (p:Person {id: $id})
RETURN p;

// T2: Direkte Kontakte einer Person (1-Hop)
// Richtungsloses Pattern, siehe Hinweis oben.
MATCH (x:Person {id: $id})-[:KNOWS]-(other)
RETURN DISTINCT other;

// T3: Kontakte zweiten Grades (2-Hop)
// Gleiche Begriffsklaerung wie in postgres/queries.sql: Person X selbst und
// ihre direkten Kontakte werden ausgeschlossen.
MATCH (x:Person {id: $id})-[:KNOWS*2]-(other)
WHERE other.id <> $id
  AND NOT (x)-[:KNOWS]-(other)
RETURN DISTINCT other;

// T4: Alle Personen bis Tiefe 4
MATCH (p:Person {id: $id})-[:KNOWS*1..4]-(other)
WHERE other.id <> $id
RETURN DISTINCT other;

// T5: Kuerzester Pfad zwischen zwei Personen
// Tiefenbegrenzung *..8 passend zur SQL-Variante (SNAP nennt 8 als
// Durchmesser des Facebook-Graphen). Im Unterschied zu postgres/queries.sql
// bricht shortestPath() sofort ab, sobald der kuerzeste Pfad gefunden ist -
// siehe Fairness-Punkt 2 in docs/konzept.md fuer die Konsequenz beim
// Laufzeitvergleich.
MATCH p = shortestPath((a:Person {id: $id1})-[:KNOWS*..8]-(b:Person {id: $id2}))
RETURN length(p) AS distance, p;

// T6: Gemeinsame Kontakte zweier Personen
MATCH (a:Person {id: $id1})-[:KNOWS]-(common)-[:KNOWS]-(b:Person {id: $id2})
WHERE a <> b
RETURN DISTINCT common;

// T7: Skalierung (siehe Fairness-Punkt 6, noch offen: welche Sampling-Methode)
// Keine eigene Query - T7 bedeutet, T4 (oder wahlweise T3) auf unterschiedlich
// grossen Teilmengen der Daten zu wiederholen (siehe import_dataset.py
// --limit-nodes). Die konkrete Teilmengen-/Sampling-Strategie ist Teil von
// Fairness-Punkt 6 und noch nicht entschieden.
