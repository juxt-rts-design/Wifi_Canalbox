"""Identifie un appareil à partir de ce qu'il envoie vraiment."""

import csv
import json
import os
import re
import threading
import time
from pathlib import Path

import bdd

_verrou_essais = threading.Lock()

OUI_CSV = Path("/usr/share/ieee-data/oui.csv")
_OUI = None

# Largeur, hauteur, densité, iOS minimum, iOS maximum, nom.
_IPHONES = (
    ((440, 956, 3), (27, 0), None, "iPhone 18 Pro Max"),
    ((402, 874, 3), (27, 0), None, "iPhone 18 Pro"),
    ((440, 956, 3), (26, 0), None, "iPhone 17 Pro Max"),
    ((402, 874, 3), (26, 0), None, "iPhone 17 Pro"),
    ((402, 874, 3), (26, 0), None, "iPhone 17"),
    ((420, 912, 3), (26, 0), None, "iPhone Air"),
    ((390, 844, 3), (26, 0), None, "iPhone 17e"),
    ((440, 956, 3), (18, 0), None, "iPhone 16 Pro Max"),
    ((402, 874, 3), (18, 0), None, "iPhone 16 Pro"),
    ((430, 932, 3), (18, 0), None, "iPhone 16 Plus"),
    ((393, 852, 3), (18, 0), None, "iPhone 16"),
    ((390, 844, 3), (18, 3), None, "iPhone 16e"),
    ((430, 932, 3), (17, 0), None, "iPhone 15 Pro Max"),
    ((430, 932, 3), (17, 0), None, "iPhone 15 Plus"),
    ((393, 852, 3), (17, 0), None, "iPhone 15 Pro"),
    ((393, 852, 3), (17, 0), None, "iPhone 15"),
    ((430, 932, 3), (16, 0), None, "iPhone 14 Pro Max"),
    ((428, 926, 3), (16, 0), None, "iPhone 14 Plus"),
    ((393, 852, 3), (16, 0), None, "iPhone 14 Pro"),
    ((390, 844, 3), (16, 0), None, "iPhone 14"),
    ((428, 926, 3), (15, 0), None, "iPhone 13 Pro Max"),
    ((390, 844, 3), (15, 0), None, "iPhone 13 Pro"),
    ((390, 844, 3), (15, 0), None, "iPhone 13"),
    ((375, 812, 3), (15, 0), None, "iPhone 13 mini"),
    ((375, 667, 2), (15, 4), None, "iPhone SE (2022)"),
    ((428, 926, 3), (14, 1), None, "iPhone 12 Pro Max"),
    ((390, 844, 3), (14, 1), None, "iPhone 12 Pro"),
    ((390, 844, 3), (14, 1), None, "iPhone 12"),
    ((375, 812, 3), (14, 1), None, "iPhone 12 mini"),
    ((375, 667, 2), (13, 4), None, "iPhone SE (2020)"),
    ((414, 896, 3), (13, 0), None, "iPhone 11 Pro Max"),
    ((375, 812, 3), (13, 0), None, "iPhone 11 Pro"),
    ((414, 896, 2), (13, 0), None, "iPhone 11"),
    ((414, 896, 3), (12, 0), (18, 7, 99), "iPhone XS Max"),
    ((375, 812, 3), (12, 0), (18, 7, 99), "iPhone XS"),
    ((414, 896, 2), (12, 0), (18, 7, 99), "iPhone XR"),
    ((375, 812, 3), (11, 1), (16, 7, 99), "iPhone X"),
)


def ecrire(lignes):
    bloc = "\n".join(lignes) + "\n\n"
    journal = os.environ.get("HEXARO_LOG", "")
    if not journal:
        print(bloc, end="", flush=True)
        return
    with open(journal, "a", encoding="utf-8") as fichier:
        fichier.write(bloc)
        fichier.flush()


def mac_aleatoire(mac):
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except (ValueError, IndexError):
        return False


def fabricant(mac):
    global _OUI
    if not mac or mac_aleatoire(mac) or not OUI_CSV.is_file():
        return ""
    if _OUI is None:
        table = {}
        with OUI_CSV.open(newline="", encoding="utf-8", errors="replace") as fichier:
            for ligne in csv.reader(fichier):
                if len(ligne) >= 3 and ligne[0] == "MA-L":
                    table[ligne[1].upper()] = ligne[2].strip()
        _OUI = table
    return _OUI.get(mac.replace(":", "").upper()[:6], "")


def _modele_android(brut):
    brut = re.split(r"\s+Build\b", brut or "", maxsplit=1)[0].strip(" ;")
    if not brut or brut.upper() in {"K", "N", "U", "MOBILE", "LINUX"} or len(brut) <= 1:
        return ""
    return brut


def depuis_dhcp(vendor, nom):
    vendor = (vendor or "").strip()
    nom = (nom or "").strip()
    bas = vendor.lower()
    nom_bas = nom.lower()
    android = re.match(r"android-dhcp-([0-9]+(?:\.[0-9]+)*)", bas)
    if android:
        return f"Android {android.group(1)}", ""
    if nom_bas.startswith("iphone"):
        return "iOS", ""
    if nom_bas.startswith("ipad"):
        return "iPadOS", ""
    if bas.startswith("msft"):
        return "Windows", ""
    if "cros" in bas or nom_bas.startswith("chromebook"):
        return "ChromeOS", ""
    if nom_bas.startswith("android"):
        return "Android", ""
    return "", ""


def _version_tuple(texte):
    nombres = [int(morceau) for morceau in re.findall(r"\d+", texte or "")][:3]
    while len(nombres) < 3:
        nombres.append(0)
    return tuple(nombres)


def version_ios(ua):
    # iOS 26 fige Safari sur « OS 18_6 » ou « OS 18_7 », sans numéro de correctif.
    # Un vrai 18.7 envoie le correctif (18_7_2). Le XR s'arrête à 18.7, l'iPhone 11 va jusqu'à 26.
    for motif in (
        r"iPhone OS (\d+(?:[_.]\d+){0,2})",
        r"CPU OS (\d+(?:[_.]\d+){0,2})",
    ):
        correspondance = re.search(motif, ua or "")
        if correspondance:
            version = correspondance.group(1).replace("_", ".")
            if version in ("18.6", "18.7"):
                return "26"
            return version
    return ""


def _formuler_modeles(noms):
    noms = list(dict.fromkeys(noms))
    if not noms:
        return ""
    if len(noms) == 1:
        return noms[0]
    if len(noms) == 2:
        return f"{noms[0]} ou {noms[1]}"
    return ", ".join(noms[:-1]) + f" ou {noms[-1]}"


def _choisir_iphone(largeur, hauteur, dpr, actuel):
    retenus = []
    for (base_l, base_h, base_dpr), minimum, maximum, nom in _IPHONES:
        if abs(largeur - base_l) > 2 or abs(hauteur - base_h) > 2:
            continue
        if dpr and abs(dpr - base_dpr) > 0.25:
            continue
        if actuel is not None:
            if actuel < _version_tuple(".".join(str(n) for n in minimum)):
                continue
            if maximum is not None and actuel > _version_tuple(".".join(str(n) for n in maximum)):
                continue
        retenus.append(nom)
    return _formuler_modeles(retenus)


def modeles_iphone(largeur, hauteur, dpr, version):
    if not largeur or not hauteur:
        return ""
    largeur, hauteur = sorted((int(largeur), int(hauteur)))
    try:
        dpr = float(dpr or 0)
    except (TypeError, ValueError):
        dpr = 0
    actuel = _version_tuple(version) if version else None
    direct = _choisir_iphone(largeur, hauteur, dpr, actuel)
    if direct:
        return direct
    if dpr and dpr > 1:
        return _choisir_iphone(round(largeur / dpr), round(hauteur / dpr), dpr, actuel)
    return ""


def depuis_navigateur(ua):
    ua = ua or ""
    version = version_ios(ua)
    if "iPhone" in ua and version:
        return f"iOS {version}", ""
    ipad = re.search(r"iPad; CPU OS ([0-9_]+)", ua)
    if ipad:
        return f"iPadOS {ipad.group(1).replace('_', '.')}", ""
    android = re.search(r"Android ([0-9]+(?:\.[0-9]+)*)\s*;\s*([^;)]*)", ua)
    if android:
        return f"Android {android.group(1)}", _modele_android(android.group(2))
    windows = re.search(r"Windows NT ([0-9.]+)", ua)
    if windows:
        numero = windows.group(1)
        if numero == "10.0":
            return "Windows NT 10.0 (10 ou 11)", ""
        return f"Windows NT {numero}", ""
    mac = re.search(r"Mac OS X ([0-9_]+)", ua)
    if mac:
        return f"macOS {mac.group(1).replace('_', '.')}", ""
    if "CrOS" in ua:
        return "ChromeOS", ""
    return "", ""


def texte_modele(systeme, modele):
    if modele:
        return modele
    if systeme.startswith("iOS"):
        return "iPhone, écran pas encore mesuré"
    if systeme.startswith("iPadOS"):
        return "iPad, numéro exact non transmis"
    if systeme.startswith("macOS"):
        return "Mac, numéro exact non transmis"
    return "non transmis par l'appareil"


def _etat():
    chemin = os.environ.get("HEXARO_ETAT", "")
    if not chemin:
        return {}
    try:
        return json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _sauver(etat):
    chemin = os.environ.get("HEXARO_ETAT", "")
    if not chemin:
        return
    Path(chemin).write_text(json.dumps(etat), encoding="utf-8")


def _mieux(systeme, modele, ancien):
    if systeme and systeme != ancien.get("systeme", ""):
        return True
    if modele and modele != ancien.get("modele", ""):
        return True
    return False


def _preciser(ip, systeme, modele):
    if not systeme and not modele:
        return
    etat = _etat()
    ancien = etat.get(ip, {})
    if not _mieux(systeme, modele, ancien):
        return
    fusion_s = systeme or ancien.get("systeme", "")
    fusion_m = modele or ancien.get("modele", "")
    ancien.update({"systeme": fusion_s, "modele": fusion_m})
    etat[ip] = ancien
    _sauver(etat)
    bdd.preciser(ip, fusion_s, fusion_m)
    ecrire([
        "── Modèle précisé ──",
        f"IP        : {ip}",
        f"Système   : {fusion_s or 'pas encore déterminé'}",
        f"Modèle    : {texte_modele(fusion_s, fusion_m)}",
        "─────────────────────",
    ])


def journal_dhcp(argv):
    if len(argv) < 4:
        return
    action, mac, ip = argv[1], argv[2], argv[3]
    if action == "del":
        ecrire(["── Appareil parti ──", f"IP       : {ip}", "────────────────────"])
        return
    if action != "add":
        return
    nom = argv[4] if len(argv) > 4 and argv[4] not in {"*", ""} else ""
    nom = os.environ.get("DNSMASQ_SUPPLIED_HOSTNAME", "") or nom
    vendor = os.environ.get("DNSMASQ_VENDOR_CLASS", "")
    systeme, modele = depuis_dhcp(vendor, nom)
    marque = fabricant(mac)
    etat = _etat()
    etat[ip] = {"mac": mac, "nom": nom, "vendor": vendor, "systeme": systeme, "modele": modele}
    _sauver(etat)
    bdd.enregistrer_appareil(
        ip, mac, nom, vendor, systeme, modele, marque, mac_aleatoire(mac)
    )
    lignes = [
        "── Appareil connecté ──",
        f"IP        : {ip}",
        f"MAC       : {mac}",
        f"Nom       : {nom or 'non annoncé'}",
        f"Système   : {systeme or 'pas encore déterminé'}",
        f"Modèle    : {texte_modele(systeme, modele)}",
    ]
    if marque:
        lignes.append(f"Fabricant : {marque}")
    elif mac_aleatoire(mac):
        lignes.append("Fabricant : masqué (adresse MAC aléatoire)")
    lignes.append("────────────────────────")
    ecrire(lignes)


def journal_page(ip, ua):
    systeme, modele = depuis_navigateur(ua)
    bdd.enregistrer_visite(ip, "/", ua)
    if not modele:
        return
    _preciser(ip, systeme, modele)


def journal_signal(ip, ua, largeur=0, hauteur=0, dpr=0):
    systeme, modele = depuis_navigateur(ua)
    version = version_ios(ua)
    if "iPhone" in (ua or "") or systeme.startswith("iOS"):
        trouve = modeles_iphone(largeur, hauteur, dpr, version)
        if trouve:
            modele = trouve
        if version:
            systeme = f"iOS {version}"
    _preciser(ip, systeme, modele)


# ── Journal des essais de formulaire ───────────────────────────────────────────
# On ne conserve que des métadonnées : jamais le contenu saisi.
# Le fichier est une liste JSON, une entrée par soumission.
MOTIFS = {
    "": "soumis",
    "criteres": "refusé (critères)",
    "correspondance": "refusé (confirmation)",
    "identite": "refusé (case non cochée)",
}


def _fichier_essais():
    return os.environ.get("HEXARO_ESSAIS", "")


def journal_essai(ip, ua, longueur, duree, valide, motif, utilisateur=""):
    chemin = _fichier_essais()
    if not chemin and not bdd.disponible():
        return
    # Bornage : une valeur aberrante ne doit pas polluer le fichier.
    try:
        longueur = max(0, min(int(longueur), 512))
    except (TypeError, ValueError):
        longueur = 0
    try:
        duree = max(0, min(int(duree), 86400))
    except (TypeError, ValueError):
        duree = 0
    systeme, _ = depuis_navigateur(ua)
    entree = {
        "quand": time.strftime("%H:%M:%S"),
        "ip": ip,
        "systeme": systeme or "inconnu",
        "longueur": int(longueur),
        "duree": int(duree),
        "valide": bool(valide),
        "motif": motif if motif in MOTIFS else "",
        "utilisateur": utilisateur,
    }
    if chemin:
        with _verrou_essais:
            try:
                Path(chemin).parent.mkdir(parents=True, exist_ok=True)
                essais = lire_essais()
                essais.append(entree)
                # On garde les 500 derniers : un test ne justifie pas d'archive longue.
                Path(chemin).write_text(
                    json.dumps(essais[-500:], ensure_ascii=False), encoding="utf-8"
                )
            except OSError:
                pass
    bdd.enregistrer_essai(
        ip, entree["systeme"], longueur, duree, bool(valide), entree["motif"], utilisateur
    )
    ecrire([
        "── Identification ──",
        f"IP        : {ip}",
        f"Système   : {entree['systeme']}",
        f"Utilisateur : {utilisateur or 'non renseigné'}",
        f"Durée     : {duree} s",
        f"Résultat  : {MOTIFS[entree['motif']]}",
        "────────────────────",
    ])


def lire_essais():
    chemin = _fichier_essais()
    if not chemin:
        return []
    try:
        donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return donnees if isinstance(donnees, list) else []
