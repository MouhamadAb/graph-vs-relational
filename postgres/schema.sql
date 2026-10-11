-- Relationales Schema fuer den Facebook-Social-Circles-Datensatz.
--
-- Entschieden:
--   - Kantenrichtung: EINE Zeile pro Paar, wie in facebook_combined.txt (Option A).
--     D.h. Abfragen nach Kontakten brauchen "WHERE person_id = X OR friend_id = X".
--   - IDs kommen direkt aus der Datei (0-4038), daher INTEGER statt SERIAL.
--
-- Entschieden: KEIN zusaetzlicher Index auf friendship.friend_id. Der
-- bestehende PRIMARY KEY (person_id, friend_id) indiziert effizient nur
-- Abfragen nach person_id - die "OR friend_id = X"-Haelfte jeder Query
-- (siehe queries.sql) laeuft dadurch auf einem Sequential Scan ueber die
-- ganze Tabelle. Das ist eine BEWUSST dokumentierte Einschraenkung (nicht
-- behoben), weil Neo4j dieses Problem durch index-free adjacency gar
-- nicht hat.

CREATE TABLE person (
    id INTEGER PRIMARY KEY
);

CREATE TABLE friendship (
    person_id INTEGER NOT NULL REFERENCES person(id),
    friend_id INTEGER NOT NULL REFERENCES person(id),
    PRIMARY KEY (person_id, friend_id)
);
