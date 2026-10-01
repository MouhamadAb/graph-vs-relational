-- Relationales Schema fuer den Facebook-Social-Circles-Datensatz.
--
-- Entschieden (siehe docs/konzept.md "Entscheidungen"):
--   - Kantenrichtung: EINE Zeile pro Paar, wie in facebook_combined.txt (Option A).
--     D.h. Abfragen nach Kontakten brauchen "WHERE person_id = X OR friend_id = X".
--   - IDs kommen direkt aus der Datei (0-4038), daher INTEGER statt SERIAL.
--
-- Noch offen (Fairness-Punkt 3): zusaetzliche Indizes auf friendship.person_id /
-- friendship.friend_id. Bewusst noch nicht angelegt, bis die Index-Strategie
-- fuer beide Systeme gemeinsam diskutiert wurde.

CREATE TABLE person (
    id INTEGER PRIMARY KEY
);

CREATE TABLE friendship (
    person_id INTEGER NOT NULL REFERENCES person(id),
    friend_id INTEGER NOT NULL REFERENCES person(id),
    PRIMARY KEY (person_id, friend_id)
);
