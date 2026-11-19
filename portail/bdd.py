"""Base de données du portail — SQLite, sans dépendance externe.

Une seule base, quatre tables :

  sessions   une ligne par lancement du portail
  appareils  un appareil vu sur le réseau (identifié par sa MAC)
  essais     une ligne par soumission du formulaire (métadonnées seulement)
  visites    une ligne par page réellement chargée

Règle tenue partout : aucune colonne n'est prévue pour un contenu de mot de
passe. Le schéma ne peut donc pas en stocker, même par erreur de code.
"""

import os
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    debut       TEXT    NOT NULL,
    fin         TEXT,
    ssid        TEXT,
    canal       TEXT,
    page        TEXT,
    -- 1 quand le portail a été arrêté proprement
    close       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS appareils (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    mac         TEXT    NOT NULL,
    ip          TEXT    NOT NULL,
    nom         TEXT,
    vendor      TEXT,
    systeme     TEXT,
    modele      TEXT,
    fabricant   TEXT,
    mac_aleatoire INTEGER NOT NULL DEFAULT 0,
    premier_vu  TEXT    NOT NULL,
    dernier_vu  TEXT    NOT NULL,
    UNIQUE(session_id, mac)
);

CREATE TABLE IF NOT EXISTS essais (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    appareil_id INTEGER REFERENCES appareils(id) ON DELETE SET NULL,
    ip          TEXT    NOT NULL,
    quand       TEXT    NOT NULL,
    systeme     TEXT,
    longueur    INTEGER NOT NULL DEFAULT 0,
    duree       INTEGER NOT NULL DEFAULT 0,
    valide      INTEGER NOT NULL DEFAULT 0,
    motif       TEXT    NOT NULL DEFAULT '',
    -- Nom d'utilisateur déclaré (identifiant, pas un secret).
    utilisateur TEXT
);

CREATE TABLE IF NOT EXISTS visites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    appareil_id INTEGER REFERENCES appareils(id) ON DELETE SET NULL,
    ip          TEXT    NOT NULL,
    quand       TEXT    NOT NULL,
    chemin      TEXT    NOT NULL,
    user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS idx_appareils_mac   ON appareils(mac);
CREATE INDEX IF NOT EXISTS idx_essais_quand    ON essais(quand);
CREATE INDEX IF NOT EXISTS idx_visites_quand   ON visites(quand);
"""

_verrou = threading.Lock()
_session_id = None

# Conservation : au-delà, les données du test sont effacées automatiquement.
# Réglable avec HEXARO_RETENTION (en jours).
RETENTION_JOURS = 30


def chemin():
    return os.environ.get("HEXARO_BDD", "")


def disponible():
    return bool(chemin())


def _maintenant():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _connecter():
    fichier = chemin()
    if not fichier:
        return None
    Path(fichier).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(fichier, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrer(conn):
    """Ajoute les colonnes apparues après la création initiale."""
    attendues = {"essais": {"utilisateur": "TEXT"}}
    for table, colonnes in attendues.items():
        try:
            existantes = {ligne[1] for ligne in conn.execute(f"PRAGMA table_info({table})")}
        except sqlite3.Error:
            continue
        for nom, type_sql in colonnes.items():
            if nom not in existantes:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {type_sql}")
    conn.commit()


def _retention():
    try:
        jours = int(os.environ.get("HEXARO_RETENTION", RETENTION_JOURS))
    except (TypeError, ValueError):
        jours = RETENTION_JOURS
    return max(0, jours)


def purger(conn):
    """Efface ce qui dépasse la durée de conservation. Renvoie un compte-rendu."""
    jours = _retention()
    if jours <= 0:
        return {}
    limite = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - jours * 86400))
    bilan = {}
    for table, colonne in (("sessions", "debut"), ("appareils", "dernier_vu"),
                           ("essais", "quand"), ("visites", "quand")):
        try:
            curseur = conn.execute(f"DELETE FROM {table} WHERE {colonne} < ?", (limite,))
            bilan[table] = curseur.rowcount
        except sqlite3.Error:
            bilan[table] = 0
    conn.commit()
    return bilan


def initialiser(ssid="", canal="", page=""):
    """Crée le schéma, purge les données trop anciennes, ouvre la session en cours."""
    global _session_id
    conn = _connecter()
    if conn is None:
        return None
    with _verrou:
        try:
            conn.executescript(SCHEMA)
            _migrer(conn)
            # Toute session restée ouverte vient d'un arrêt brutal.
            conn.execute(
                "UPDATE sessions SET close=1, fin=COALESCE(fin, ?) WHERE close=0",
                (_maintenant(),),
            )
            conn.commit()
            purge = purger(conn)
            if any(purge.values()):
                print(f"Purge (> {_retention()} j) : {purge}", flush=True)
            curseur = conn.execute(
                "INSERT INTO sessions (debut, ssid, canal, page) VALUES (?, ?, ?, ?)",
                (_maintenant(), ssid, canal, page),
            )
            conn.commit()
            _session_id = curseur.lastrowid
        finally:
            conn.close()
    return _session_id


def fermer_session():
    conn = _connecter()
    if conn is None or _session_id is None:
        return
    with _verrou:
        try:
            conn.execute(
                "UPDATE sessions SET fin=?, close=1 WHERE id=?",
                (_maintenant(), _session_id),
            )
            conn.commit()
        finally:
            conn.close()


def _appareil_id(conn, ip, mac, nom="", vendor="", systeme="", modele="", fabricant="", aleatoire=False):
    if not mac:
        return None
    maintenant = _maintenant()
    ligne = conn.execute(
        "SELECT id FROM appareils WHERE session_id=? AND mac=?",
        (_session_id, mac),
    ).fetchone()
    if ligne:
        # On enrichit sans jamais écraser une information par du vide.
        conn.execute(
            """UPDATE appareils SET
                   ip=?, dernier_vu=?,
                   nom      = CASE WHEN ?<>'' THEN ? ELSE nom END,
                   vendor   = CASE WHEN ?<>'' THEN ? ELSE vendor END,
                   systeme  = CASE WHEN ?<>'' THEN ? ELSE systeme END,
                   modele   = CASE WHEN ?<>'' THEN ? ELSE modele END,
                   fabricant= CASE WHEN ?<>'' THEN ? ELSE fabricant END
               WHERE id=?""",
            (ip, maintenant,
             nom, nom, vendor, vendor, systeme, systeme,
             modele, modele, fabricant, fabricant, ligne["id"]),
        )
        return ligne["id"]
    curseur = conn.execute(
        """INSERT INTO appareils
           (session_id, mac, ip, nom, vendor, systeme, modele, fabricant,
            mac_aleatoire, premier_vu, dernier_vu)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_session_id, mac, ip, nom, vendor, systeme, modele, fabricant,
         1 if aleatoire else 0, maintenant, maintenant),
    )
    return curseur.lastrowid


def enregistrer_appareil(ip, mac, nom="", vendor="", systeme="", modele="",
                         fabricant="", aleatoire=False):
    conn = _connecter()
    if conn is None:
        return
    with _verrou:
        try:
            _appareil_id(conn, ip, mac, nom, vendor, systeme, modele, fabricant, aleatoire)
            conn.commit()
        finally:
            conn.close()


def preciser(ip, systeme="", modele=""):
    if not systeme and not modele:
        return
    conn = _connecter()
    if conn is None:
        return
    with _verrou:
        try:
            ligne = conn.execute(
                "SELECT id FROM appareils WHERE session_id=? AND ip=? ORDER BY dernier_vu DESC LIMIT 1",
                (_session_id, ip),
            ).fetchone()
            if ligne:
                conn.execute(
                    """UPDATE appareils SET
                           systeme = CASE WHEN ?<>'' THEN ? ELSE systeme END,
                           modele  = CASE WHEN ?<>'' THEN ? ELSE modele END
                       WHERE id=?""",
                    (systeme, systeme, modele, modele, ligne["id"]),
                )
                conn.commit()
        finally:
            conn.close()


def enregistrer_visite(ip, chemin_page, user_agent=""):
    conn = _connecter()
    if conn is None:
        return
    with _verrou:
        try:
            ligne = conn.execute(
                "SELECT id FROM appareils WHERE session_id=? AND ip=? ORDER BY dernier_vu DESC LIMIT 1",
                (_session_id, ip),
            ).fetchone()
            conn.execute(
                "INSERT INTO visites (session_id, appareil_id, ip, quand, chemin, user_agent)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (_session_id, ligne["id"] if ligne else None, ip,
                 _maintenant(), chemin_page, user_agent[:300]),
            )
            conn.commit()
        finally:
            conn.close()


def enregistrer_essai(ip, systeme, longueur, duree, valide, motif="", utilisateur=""):
    conn = _connecter()
    if conn is None:
        return
    with _verrou:
        try:
            ligne = conn.execute(
                "SELECT id FROM appareils WHERE session_id=? AND ip=? ORDER BY dernier_vu DESC LIMIT 1",
                (_session_id, ip),
            ).fetchone()
            conn.execute(
                """INSERT INTO essais
                   (session_id, appareil_id, ip, quand, systeme, longueur, duree, valide, motif, utilisateur)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (_session_id, ligne["id"] if ligne else None, ip, _maintenant(),
                 systeme, int(longueur), int(duree), 1 if valide else 0, motif,
                 utilisateur or None),
            )
            conn.commit()
        finally:
            conn.close()


def lire_essais(limite=200):
    conn = _connecter()
    if conn is None:
        return []
    try:
        lignes = conn.execute(
            """SELECT e.quand, e.ip, e.systeme, e.longueur, e.duree, e.valide, e.motif,
                      e.utilisateur, a.modele, a.nom
               FROM essais e LEFT JOIN appareils a ON a.id = e.appareil_id
               ORDER BY e.id DESC LIMIT ?""",
            (limite,),
        ).fetchall()
        return [dict(ligne) for ligne in lignes]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def statistiques():
    """Chiffres cumulés de tout le test, toutes sessions confondues."""
    conn = _connecter()
    if conn is None:
        return {}
    try:
        ligne = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM appareils) AS appareils,
                 (SELECT COUNT(*) FROM essais)    AS essais,
                 (SELECT COUNT(*) FROM essais WHERE valide=1) AS essais_valides,
                 (SELECT COALESCE(AVG(duree),0) FROM essais)  AS duree_moyenne,
                 (SELECT COUNT(*) FROM visites)   AS visites,
                 (SELECT COUNT(*) FROM sessions)  AS sessions"""
        ).fetchone()
        return dict(ligne)
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


def statistiques_session():
    """Chiffres de la session en cours seulement, pour la vue en direct."""
    conn = _connecter()
    if conn is None:
        return {}
    try:
        ligne = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM appareils WHERE session_id=?) AS appareils,
                 (SELECT COUNT(*) FROM essais    WHERE session_id=?) AS essais,
                 (SELECT COUNT(*) FROM essais    WHERE session_id=? AND valide=1) AS essais_valides,
                 (SELECT COALESCE(AVG(duree),0)  FROM essais WHERE session_id=?) AS duree_moyenne,
                 (SELECT COUNT(*) FROM visites   WHERE session_id=?) AS visites""",
            (_session_id,) * 5,
        ).fetchone()
        return dict(ligne)
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


def lire_appareils(limite=500):
    """Tous les appareils vus, toutes sessions confondues."""
    conn = _connecter()
    if conn is None:
        return []
    try:
        lignes = conn.execute(
            """SELECT a.ip, a.mac, a.nom, a.systeme, a.modele, a.fabricant,
                      a.mac_aleatoire, a.dernier_vu, s.debut AS session_debut
               FROM appareils a LEFT JOIN sessions s ON s.id = a.session_id
               ORDER BY a.dernier_vu DESC, a.ip LIMIT ?""",
            (limite,),
        ).fetchall()
        return [dict(ligne) for ligne in lignes]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def lire_appareils_session():
    """Seulement les appareils de la session en cours, pour le direct."""
    conn = _connecter()
    if conn is None:
        return []
    try:
        lignes = conn.execute(
            """SELECT ip, mac, nom, systeme, modele, fabricant, mac_aleatoire, dernier_vu
               FROM appareils WHERE session_id=? ORDER BY ip""",
            (_session_id,),
        ).fetchall()
        return [dict(ligne) for ligne in lignes]
    except sqlite3.Error:
        return []
    finally:
        conn.close()
