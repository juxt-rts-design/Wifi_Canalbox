#!/usr/bin/env python3
"""Sert la page choisie au lancement, plus le tableau de bord /admin."""

import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import admin
import bdd
from journal import journal_page, journal_signal, journal_essai, lire_essais
LOGO = (ROOT / "logo.png").read_bytes()
ALARME = (ROOT / "alarme.wav").read_bytes()
DUREE = 60

# Fichiers annexes servis tels quels : nom demandé -> (fichier, type MIME).
STATIQUES = {
    "/canalbox-logo.png": "image/png",
    "/canalbox-logo-dark.png": "image/png",
    "/airtel-logo.png": "image/png",
    "/airtel-logo-blanc.png": "image/png",
    "/moov-logo.png": "image/png",
    "/moov-logo-blanc.png": "image/png",
    "/icon-phone.png": "image/png",
    "/icon-warning.png": "image/png",
    "/icon-eye.png": "image/png",
    "/icon-eye-slash.png": "image/png",
    "/icon-check.png": "image/png",
    "/icon-info.png": "image/png",
    "/icon-facebook.png": "image/png",
}

PAGES = {
    "virus": ROOT / "index.html",
    "wifi": ROOT / "index-wifi.html",
    "airtel": ROOT / "index-airtel.html",
    "moov": ROOT / "index-moov.html",
}
NOMS_PAGES = {
    "virus": "Virus Hexaro",
    "wifi": "Wifi",
    "airtel": "Airtel",
    "moov": "Moov Africa",
}
CHOIX = os.environ.get("HEXARO_PAGE", "virus")
if CHOIX not in PAGES:
    CHOIX = "virus"
PAGE = PAGES[CHOIX]
CLE = os.environ.get("HEXARO_CLE", "")
SSID = os.environ.get("HEXARO_SSID", "")
_echeances = {}
_verrou = threading.Lock()


RESEAUX = (
    {"nom": "FREEBOX-8F2C", "force": 4, "securite": "WPA2", "note": "le voisin du dessus"},
    {"nom": "Livebox-2A19", "force": 3, "securite": "WPA2", "note": "protégé, comme prévu"},
    {"nom": "HOTEL_IBIS_GUEST", "force": 2, "securite": "ouvert", "note": "ouvert mais sans internet"},
    {"nom": "TP-LINK_4C21", "force": 2, "securite": "WPA2", "note": "mot de passe : admin, comme tout le monde"},
    {"nom": "SFR_9A2B", "force": 1, "securite": "WPA2", "note": "une seule barre, courage"},
    {"nom": "IMPRIMANTE_HP", "force": 3, "securite": "ouvert", "note": "ce n'est pas un Wi-Fi, quelqu'un a cliqué"},
)


def lire_compte(ip, duree=DUREE):
    """Le délai est fixé au premier affichage, puis il continue après un rechargement."""
    maintenant = time.time()
    with _verrou:
        fin = _echeances.get(ip)
        if fin is None:
            fin = maintenant + duree
            _echeances[ip] = fin
    return {
        "fin": fin,
        "maintenant": maintenant,
        "total": duree,
        "fini": maintenant >= fin,
    }


class Portail(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        chemin = self.path.split("?", 1)[0]
        if chemin == "/compte":
            self._compte()
            return
        if chemin == "/admin":
            self._admin()
            return
        if chemin == "/admin/etat":
            self._admin_etat()
            return
        if chemin == "/reseau":
            self._reseau()
            return
        self._repondre(envoyer_corps=True)

    def do_HEAD(self):
        self._repondre(envoyer_corps=False)

    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", "0") or "0")
        brut = self.rfile.read(min(longueur, 65536)) if longueur > 0 else b""
        chemin = self.path.split("?", 1)[0]
        if chemin == "/signal":
            self._signal(brut)
            return
        if chemin == "/essai":
            self._essai(brut)
            return
        if chemin == "/admin":
            self._admin_connexion(brut)
            return
        self._repondre(envoyer_corps=True)

    def _compte(self):
        corps = json.dumps(lire_compte(self.client_address[0])).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(corps)

    def _signal(self, brut):
        try:
            donnees = json.loads(brut.decode("utf-8", "replace") or "{}")
        except json.JSONDecodeError:
            donnees = {}
        journal_signal(
            self.client_address[0],
            str(donnees.get("ua") or self.headers.get("User-Agent", "")),
            donnees.get("l") or 0,
            donnees.get("h") or 0,
            donnees.get("dpr") or 0,
        )
        self.send_response(204)
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _reseau(self):
        """Le faux scan : des réseaux inventés, aucun renseignement demandé."""
        corps = json.dumps({
            "ssid": SSID,
            "canal": os.environ.get("HEXARO_CANAL", ""),
            "choix": CHOIX,
            "reseaux": RESEAUX,
        }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(corps)

    def _admin(self):
        ip = self.client_address[0]
        requete = self.path.split("?", 1)[1] if "?" in self.path else ""
        params = parse_qs(requete)

        if not CLE:
            page = admin.page_connexion(
                message="Aucune clé configurée : relance le portail en choisissant la page Wifi."
            )
            self._envoyer(page.encode("utf-8"), "text/html; charset=utf-8", True, 403)
            return

        if "sortie" in params:
            admin.fermer(self._jeton())
            self._rediriger("/admin")
            return

        jeton = self._jeton()
        if admin.session_valide(jeton):
            self._envoyer(admin.page_tableau(SSID, os.environ.get("HEXARO_CANAL", ""),
                                             NOMS_PAGES[CHOIX]).encode("utf-8"),
                          "text/html; charset=utf-8", True)
            return

        # L'ancien lien direct ?cle=... reste accepté : il ouvre une session.
        fournie = (params.get("cle") or [""])[0]
        if fournie:
            nouveau, message = admin.verifier(ip, fournie, CLE)
            if nouveau:
                self._rediriger("/admin", nouveau)
            else:
                page = admin.page_connexion(message=message, erreur=True)
                self._envoyer(page.encode("utf-8"), "text/html; charset=utf-8", True, 403)
            return

        self._envoyer(admin.page_connexion().encode("utf-8"), "text/html; charset=utf-8", True)

    def _admin_connexion(self, brut):
        ip = self.client_address[0]
        donnees = parse_qs(brut.decode("utf-8", "replace"))
        fournie = (donnees.get("cle") or [""])[0]
        jeton, message = admin.verifier(ip, fournie, CLE)
        if jeton:
            self._rediriger("/admin", jeton)
            return
        page = admin.page_connexion(message=message, erreur=True)
        self._envoyer(page.encode("utf-8"), "text/html; charset=utf-8", True, 403)

    def _essai(self, brut):
        """Journalise une soumission de formulaire : métadonnées seulement.

        Le contenu du champ mot de passe n'est jamais lu par le serveur. Le client
        n'envoie qu'un nombre de caractères. Toute clé inattendue est ignorée, et
        une valeur qui ressemble à un secret est refusée plutôt que stockée.
        """
        try:
            donnees = json.loads(brut.decode("utf-8", "replace") or "{}")
        except json.JSONDecodeError:
            donnees = {}
        if not isinstance(donnees, dict):
            donnees = {}

        def entier(cle, borne):
            try:
                valeur = int(donnees.get(cle) or 0)
            except (TypeError, ValueError):
                return 0
            return max(0, min(valeur, borne))

        longueur = entier("l", 512)
        duree = entier("d", 86400)
        valide = 1 if str(donnees.get("ok")) in ("1", "True", "true") else 0
        motif = re.sub(r"[^a-z_]", "", str(donnees.get("motif") or ""))[:24]
        # Nom d'utilisateur : un identifiant, pas un secret. Nettoyé et borné.
        utilisateur = re.sub(r"[\x00-\x1f\x7f]", "", str(donnees.get("u") or "")).strip()[:80]

        journal_essai(
            self.client_address[0],
            str(donnees.get("ua") or self.headers.get("User-Agent", "")),
            longueur,
            duree,
            valide,
            motif,
            utilisateur,
        )
        self.send_response(204)
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _admin_etat(self):
        if not admin.session_valide(self._jeton()):
            corps = b'{"erreur":"session"}'
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(corps)
            return
        appareils = [[ip, infos] for ip, infos in _appareils()]
        journal = _lignes_journal()
        essais = bdd.lire_essais(200) if bdd.disponible() else lire_essais()[-60:]
        corps = json.dumps({
            "appareils": appareils,
            "appareils_session": bdd.lire_appareils_session() if bdd.disponible() else [],
            "journal": journal.splitlines() if journal else [],
            "essais": essais,
            "stats": bdd.statistiques() if bdd.disponible() else {},
            "stats_session": bdd.statistiques_session() if bdd.disponible() else {},
            "maj": time.strftime("%H:%M:%S"),
        }, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(corps)

    def _jeton(self):
        entete = self.headers.get("Cookie", "") or ""
        for morceau in entete.split(";"):
            nom, _, valeur = morceau.strip().partition("=")
            if nom == "portail_admin":
                return valeur
        return ""

    def _rediriger(self, cible, jeton=None, code=303):
        self.send_response(code)
        self.send_header("Location", cible)
        if jeton:
            self.send_header("Set-Cookie",
                             f"portail_admin={jeton}; Path=/; HttpOnly; SameSite=Strict; Max-Age={admin.DUREE_SESSION}")
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

    def _envoyer(self, corps, type_mime, envoyer_corps, code=200):
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        if envoyer_corps:
            self.wfile.write(corps)

    def _repondre(self, envoyer_corps):
        chemin = self.path.split("?", 1)[0]
        if chemin == "/favicon.ico":
            self.send_response(204)
            self.send_header("Connection", "close")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        if chemin == "/logo.png":
            corps, type_mime = LOGO, "image/png"
        elif chemin == "/alarme.wav":
            corps, type_mime = ALARME, "audio/wav"
        elif chemin in STATIQUES:
            # Sans ça, une icône absente recevrait la page HTML et s'afficherait cassée.
            nom, type_mime = chemin.lstrip("/"), STATIQUES[chemin]
            try:
                corps = (ROOT / nom).read_bytes()
            except OSError:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                return
        elif chemin in ("/", "/index.html"):
            corps, type_mime = PAGE.read_bytes(), "text/html; charset=utf-8"
        else:
            page, type_mime = PAGE.read_bytes(), "text/html; charset=utf-8"
            # Une requête d'asset ne doit jamais retomber sur la page du portail.
            if Path(chemin).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js", ".woff", ".woff2", ".ttf"}:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                return
            corps = page

        self.send_response(200)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        if envoyer_corps:
            self.wfile.write(corps)

    def log_message(self, fmt, *args):
        if self.path.split("?", 1)[0] in (
            "/logo.png",
            "/favicon.ico",
            "/signal",
            "/alarme.wav",
            "/compte",
            "/admin",
            "/reseau",
        ):
            return
        journal_page(self.client_address[0], self.headers.get("User-Agent", ""))


def _appareils():
    chemin = os.environ.get("HEXARO_ETAT", "")
    if not chemin:
        return []
    try:
        donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(donnees, dict):
        return []
    return sorted(
        ((ip, infos) for ip, infos in donnees.items() if isinstance(infos, dict)),
        key=lambda paire: tuple(int(p) if p.isdigit() else 0 for p in paire[0].split(".")),
    )


def _lignes_journal(limite=120):
    chemin = os.environ.get("HEXARO_LOG", "")
    if not chemin:
        return ""
    try:
        with open(chemin, encoding="utf-8", errors="replace") as fichier:
            contenu = fichier.read()
    except OSError:
        return ""
    return "\n".join(contenu.splitlines()[-limite:])


def main():
    port = int(os.environ.get("PORTAIL_PORT", "80"))
    bdd.initialiser(SSID, os.environ.get("HEXARO_CANAL", ""), NOMS_PAGES[CHOIX])
    serveur = ThreadingHTTPServer(("0.0.0.0", port), Portail)
    print("Page Hexaro prête.", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        bdd.fermer_session()
        serveur.server_close()


if __name__ == "__main__":
    main()
