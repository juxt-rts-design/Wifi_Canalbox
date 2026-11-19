"""Pages d'administration du portail — identité neutre (Hexaro)."""

import hmac
import html
import secrets
import threading
import time

DUREE_SESSION = 8 * 3600
MAX_ESSAIS = 5
BLOCAGE = 90

_sessions = {}
_essais = {}
_verrou = threading.Lock()


def _balayer(maintenant):
    for jeton, fin in list(_sessions.items()):
        if fin <= maintenant:
            _sessions.pop(jeton, None)
    for ip, (_, debut) in list(_essais.items()):
        if maintenant - debut > BLOCAGE:
            _essais.pop(ip, None)


def bloque(ip):
    maintenant = time.time()
    with _verrou:
        _balayer(maintenant)
        nb, debut = _essais.get(ip, (0, maintenant))
        return nb >= MAX_ESSAIS and (maintenant - debut) <= BLOCAGE


def _noter_echec(ip):
    maintenant = time.time()
    with _verrou:
        nb, debut = _essais.get(ip, (0, maintenant))
        if maintenant - debut > BLOCAGE:
            _essais[ip] = (1, maintenant)
        else:
            _essais[ip] = (nb + 1, debut)


def _effacer_echecs(ip):
    with _verrou:
        _essais.pop(ip, None)


def verifier(ip, fournie, attendue):
    """Renvoie (jeton, message). Le jeton est None si l'accès est refusé."""
    if not attendue:
        return None, "Aucune clé configurée : relance le portail en choisissant la page Wifi."
    if bloque(ip):
        return None, "Trop d'essais incorrects. Patiente une minute."
    if hmac.compare_digest(fournie, attendue):
        _effacer_echecs(ip)
        jeton = secrets.token_urlsafe(24)
        with _verrou:
            _sessions[jeton] = time.time() + DUREE_SESSION
        return jeton, None
    _noter_echec(ip)
    return None, "Clé incorrecte."


def session_valide(jeton):
    if not jeton:
        return False
    maintenant = time.time()
    with _verrou:
        fin = _sessions.get(jeton)
        if fin is None:
            return False
        if fin <= maintenant:
            _sessions.pop(jeton, None)
            return False
        return True


def fermer(jeton):
    with _verrou:
        _sessions.pop(jeton, None)


_STYLE = """
:root{
  /* Palette HEXARO : monochrome noir / blanc, accent froid */
  --hx-noir:#050608;
  --hx-noir-2:#0B0E12;
  --hx-noir-3:#12161C;
  --hx-panneau:#0E1218;
  --hx-bordure:rgba(255,255,255,0.10);
  --hx-bordure-vive:rgba(255,255,255,0.28);
  --hx-blanc:#F2F6FA;
  --hx-gris:#8A97A6;
  --hx-gris-2:#5F6B78;
  --hx-accent:#5FE3C0;
  --hx-accent-2:#3FC9A6;
  --hx-rouge:#FF4D5E;
  --hx-jaune:#FFD84D;

  /* Compatibilité avec les anciens noms utilisés dans le HTML */
  --cb-green:var(--hx-accent);
  --cb-green-dark:var(--hx-accent-2);
  --cb-yellow:var(--hx-jaune);
  --cb-black:#000000;
  --cb-white:var(--hx-blanc);
  --cb-gray-bg:var(--hx-noir);
  --cb-gray-text:var(--hx-blanc);
  --cb-muted:var(--hx-gris);
  --cb-line:var(--hx-bordure);
  --cb-rouge:var(--hx-rouge);

  --radius-pill:100px;
  --radius-card:6px;
  --radius-input:6px;

  --ombre:0 0 0 1px var(--hx-bordure), 0 18px 40px rgba(0,0,0,0.55);
  --ombre-haute:0 0 0 1px var(--hx-bordure-vive), 0 26px 60px rgba(0,0,0,0.7);
  --lueur:0 0 24px rgba(95,227,192,0.22);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}

body{
  font-family:'Inter','Segoe UI',system-ui,sans-serif;
  background:
    radial-gradient(ellipse 70% 45% at 50% -8%, rgba(95,227,192,0.13), transparent 62%),
    radial-gradient(ellipse 55% 40% at 90% 105%, rgba(95,227,192,0.07), transparent 60%),
    repeating-linear-gradient(0deg, rgba(255,255,255,0.022) 0 1px, transparent 1px 3px),
    var(--hx-noir);
  color:var(--hx-blanc);
  font-size:16px; line-height:1.65; min-height:100dvh;
  display:flex; flex-direction:column;
  -webkit-tap-highlight-color:transparent;
  -webkit-font-smoothing:antialiased;
}

h1,h2,h3,h4,.btn,.onglet{
  font-family:'Poppins','Segoe UI',system-ui,sans-serif;
  font-weight:600;
}

.container{max-width:1140px;margin:0 auto;padding:0 22px;width:100%}
main.container{flex:1 0 auto;padding-top:26px;padding-bottom:56px}

/* ══════════════ EN-TÊTE ══════════════ */
header{
  background:rgba(5,6,8,0.94);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  padding:12px 0;
  position:sticky; top:0; z-index:100;
  border-bottom:1px solid var(--hx-bordure);
}
header::after{
  content:"";position:absolute;left:0;right:0;bottom:-1px;height:1px;
  background:linear-gradient(90deg,transparent,rgba(95,227,192,0.55),transparent);
}
header .inner{display:flex;justify-content:space-between;align-items:center;gap:16px}
header .brand{display:flex;align-items:center;gap:13px;min-width:0}
header .brand img{
  height:34px;width:34px;object-fit:contain;flex-shrink:0;
  filter:drop-shadow(0 0 9px rgba(95,227,192,0.45));
}
header .nom{
  font-family:'Poppins',sans-serif;font-weight:600;font-size:0.95rem;
  letter-spacing:0.30em;color:#fff;line-height:1.1;
}
header .nom small{
  display:block;font-size:0.58rem;letter-spacing:0.24em;
  color:var(--hx-accent);font-weight:500;margin-top:2px;
}
header .help{
  display:flex;align-items:center;gap:7px;
  font-size:0.72rem;color:var(--hx-gris);
  letter-spacing:0.08em;text-transform:uppercase;flex-shrink:0;
}
header .help img{width:15px;height:15px;opacity:0.75}

/* ══════════════ BANDEAU D'ÉTAT ══════════════ */
.alert{
  position:relative;
  background:linear-gradient(135deg, rgba(18,22,28,0.96), rgba(10,13,17,0.96));
  color:var(--hx-blanc);
  padding:22px 26px;
  border-radius:var(--radius-card);
  margin-bottom:22px;
  display:flex;align-items:flex-start;gap:16px;
  box-shadow:var(--ombre);
}
.alert::before{
  content:"";position:absolute;left:0;top:0;bottom:0;width:3px;
  background:linear-gradient(180deg,var(--hx-accent),transparent);
}
.alert .icon-badge{
  width:44px;height:44px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
  border:1px solid var(--hx-bordure-vive);
  border-radius:50%;
  background:rgba(95,227,192,0.10);
}
.alert .icon-badge img{width:21px;height:21px;filter:brightness(0) invert(1);opacity:0.92}
.alert h2{font-size:1.06rem;margin-bottom:4px;color:#fff;line-height:1.3}
.alert p{font-size:0.79rem;color:var(--hx-gris);line-height:1.55}
.alert p span{color:var(--hx-blanc);font-variant-numeric:tabular-nums}
.alert .droite{margin-left:auto;display:flex;gap:8px;align-items:center;flex-shrink:0}

/* ══════════════ BADGES ══════════════ */
.badge{
  display:inline-block;background:var(--hx-jaune);color:#141005;
  font-family:'Poppins',sans-serif;font-weight:600;font-size:0.62rem;
  padding:3px 11px;border-radius:var(--radius-pill);
  text-transform:uppercase;letter-spacing:0.12em;margin-bottom:9px;
}
.badge.live{
  display:inline-flex;align-items:center;gap:7px;
  background:rgba(95,227,192,0.13);color:var(--hx-accent);
  border:1px solid rgba(95,227,192,0.35);
  padding:3px 12px;
}
.badge.live::before{
  content:"";width:6px;height:6px;border-radius:50%;
  background:var(--hx-accent);
  box-shadow:0 0 8px var(--hx-accent);
  animation:pouls 1.5s ease-in-out infinite;
}
.badge.live.hors{
  background:rgba(255,77,94,0.12);color:var(--hx-rouge);
  border-color:rgba(255,77,94,0.35);
}
.badge.live.hors::before{animation:none;background:var(--hx-rouge);box-shadow:none}
@keyframes pouls{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.3;transform:scale(0.75)}}

/* ══════════════ ONGLETS ══════════════ */
nav.onglets{
  display:flex;gap:6px;margin-bottom:24px;overflow-x:auto;
  background:rgba(11,14,18,0.85);
  padding:6px;border-radius:var(--radius-pill);
  box-shadow:0 0 0 1px var(--hx-bordure);
  scrollbar-width:none;
}
nav.onglets::-webkit-scrollbar{display:none}
.onglet{
  flex:1 0 auto;padding:11px 20px;border:0;
  border-radius:var(--radius-pill);
  background:transparent;color:var(--hx-gris);
  font-size:0.79rem;letter-spacing:0.05em;cursor:pointer;white-space:nowrap;
  transition:background .2s,color .2s,box-shadow .2s;
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
}
.onglet:hover{background:rgba(255,255,255,0.05);color:var(--hx-blanc)}
.onglet[aria-selected="true"]{
  background:linear-gradient(180deg,rgba(95,227,192,0.16),rgba(95,227,192,0.06));
  color:#fff;
  box-shadow:inset 0 0 0 1px rgba(95,227,192,0.42), 0 0 20px rgba(95,227,192,0.12);
}
.onglet .pastille{
  background:rgba(255,255,255,0.10);color:var(--hx-blanc);
  font-size:0.66rem;padding:1px 8px;border-radius:100px;
  font-family:'Inter',sans-serif;font-weight:600;
  font-variant-numeric:tabular-nums;
}
.onglet[aria-selected="true"] .pastille{
  background:var(--hx-accent);color:#02120E;
}
.panneau{display:none;animation:apparait .35s ease}
.panneau.actif{display:block}
@keyframes apparait{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* ══════════════ CARTES ══════════════ */
.card{
  position:relative;
  background:linear-gradient(160deg, rgba(18,22,28,0.92), rgba(9,12,16,0.92));
  border-radius:var(--radius-card);
  box-shadow:var(--ombre);
  margin-bottom:20px;
  overflow:hidden;
}
.card::before{
  content:"";position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--hx-bordure-vive),transparent);
}
.card-pad{padding:26px 28px}
.card-tete{
  display:flex;align-items:center;justify-content:space-between;
  gap:16px;flex-wrap:wrap;margin-bottom:18px;
}
.card h2.titre{
  font-size:0.70rem;letter-spacing:0.20em;text-transform:uppercase;
  color:var(--hx-accent);margin:0;font-weight:600;
}
.card h2.titre .compte{
  font-family:'Inter',sans-serif;letter-spacing:0.02em;text-transform:none;
  color:var(--hx-gris-2);font-weight:400;font-size:0.76rem;
}

/* ══════════════ CARTES STAT ══════════════ */
.grille-stats{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
  gap:14px;margin-bottom:22px;
}
.stat{
  position:relative;
  background:linear-gradient(160deg, rgba(20,25,32,0.95), rgba(10,13,17,0.95));
  border-radius:var(--radius-card);
  padding:20px 22px 18px;
  box-shadow:var(--ombre);
  transition:transform .22s,box-shadow .22s;
  overflow:hidden;
}
.stat::before{
  content:"";position:absolute;top:0;left:0;width:34px;height:2px;
  background:var(--hx-accent);box-shadow:0 0 12px var(--hx-accent);
}
.stat::after{
  content:"";position:absolute;right:16px;top:16px;
  width:5px;height:5px;border-radius:50%;
  background:var(--hx-accent);opacity:0.6;
  box-shadow:0 0 10px var(--hx-accent);
}
.stat:hover{transform:translateY(-3px);box-shadow:var(--ombre-haute)}
.stat .valeur{
  font-family:'Poppins',sans-serif;font-weight:600;font-size:1.85rem;
  line-height:1.05;color:#fff;letter-spacing:-0.02em;
  font-variant-numeric:tabular-nums;
}
.stat .libelle{
  font-size:0.66rem;color:var(--hx-gris-2);text-transform:uppercase;
  letter-spacing:0.16em;margin-top:8px;
}

/* ══════════════ LISTES ══════════════ */
dl{display:grid;grid-template-columns:150px 1fr;gap:11px 18px;font-size:0.85rem}
dt{color:var(--hx-gris-2);letter-spacing:0.03em}
dd{margin:0;color:var(--hx-blanc);word-break:break-word;font-weight:500}

/* ══════════════ TABLEAUX ══════════════ */
.tableau-englobe{
  overflow-x:auto;
  margin:0 -28px;padding:0 28px;
  scrollbar-width:thin;
}
.tableau-englobe::-webkit-scrollbar{height:8px}
.tableau-englobe::-webkit-scrollbar-thumb{
  background:rgba(255,255,255,0.14);border-radius:10px;
}
table{
  width:100%;border-collapse:separate;border-spacing:0;
  font-size:0.83rem;
}
thead th{
  text-align:left;padding:11px 14px;
  color:var(--hx-gris-2);
  font-family:'Poppins',sans-serif;font-weight:500;
  font-size:0.64rem;letter-spacing:0.14em;text-transform:uppercase;
  white-space:nowrap;
  background:rgba(255,255,255,0.028);
  border-top:1px solid var(--hx-bordure);
  border-bottom:1px solid var(--hx-bordure);
  position:sticky;top:0;z-index:2;
}
thead th:first-child{border-left:1px solid var(--hx-bordure);border-radius:4px 0 0 0}
thead th:last-child{border-right:1px solid var(--hx-bordure);border-radius:0 4px 0 0}
thead th.triable{cursor:pointer;user-select:none;transition:color .16s}
thead th.triable:hover{color:var(--hx-accent)}
thead th .fleche{opacity:0.3;margin-left:5px;font-size:0.66rem}
thead th[aria-sort] .fleche{opacity:1;color:var(--hx-accent)}
tbody td{
  text-align:left;padding:13px 14px;
  border-bottom:1px solid rgba(255,255,255,0.045);
  vertical-align:middle;
}
tbody tr{transition:background .16s}
tbody tr:hover{background:rgba(95,227,192,0.045)}
tbody tr.selectionne{background:rgba(95,227,192,0.09)}
tbody tr.selectionne:hover{background:rgba(95,227,192,0.13)}
tbody tr:last-child td{border-bottom:0}

td.ip,.mono{
  font-family:'Courier New',ui-monospace,monospace;
  color:var(--hx-accent);font-weight:400;letter-spacing:0.02em;
}
td.nom{font-weight:500;color:#fff}
.vide{color:var(--hx-gris-2);font-style:italic;padding:22px 14px !important;text-align:center}

/* pastilles d'état */
.pastille-etat{
  display:inline-flex;align-items:center;gap:6px;
  padding:3px 11px;border-radius:100px;
  font-size:0.70rem;font-weight:500;white-space:nowrap;
  border:1px solid transparent;
}
.pastille-etat.ok{
  background:rgba(95,227,192,0.10);color:var(--hx-accent);
  border-color:rgba(95,227,192,0.28);
}
.pastille-etat.ko{
  background:rgba(255,77,94,0.09);color:var(--hx-rouge);
  border-color:rgba(255,77,94,0.26);
}

/* ══════════════ BARRE D'OUTILS ══════════════ */
.barre-outils{
  display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  margin-bottom:16px;
}
.recherche{position:relative;flex:1 1 240px;min-width:0}
.recherche input{
  width:100%;padding:11px 16px 11px 42px;
  border:1px solid var(--hx-bordure);
  border-radius:var(--radius-input);
  font-size:0.84rem;font-family:'Inter',sans-serif;
  background:rgba(0,0,0,0.42);color:var(--hx-blanc);
  transition:border-color .18s,box-shadow .18s,background .18s;
}
.recherche input::placeholder{color:var(--hx-gris-2)}
.recherche input:focus{
  outline:none;border-color:rgba(95,227,192,0.55);
  background:rgba(0,0,0,0.6);
  box-shadow:0 0 0 3px rgba(95,227,192,0.10);
}
.recherche::before{
  content:"";position:absolute;left:16px;top:50%;transform:translateY(-50%);
  width:13px;height:13px;border:1.5px solid var(--hx-gris-2);border-radius:50%;
  pointer-events:none;
}
.recherche::after{
  content:"";position:absolute;left:26px;top:calc(50% + 5px);
  width:6px;height:1.5px;background:var(--hx-gris-2);
  transform:rotate(45deg);pointer-events:none;
}

/* ══════════════ BOUTONS ══════════════ */
.btn{
  border:1px solid transparent;
  border-radius:var(--radius-pill);
  background:var(--hx-accent);color:#02120E;
  font-family:'Poppins','Segoe UI',sans-serif;font-weight:600;
  cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  text-decoration:none;white-space:nowrap;
  transition:background .18s,transform .12s,box-shadow .18s,border-color .18s,color .18s;
}
.btn img{width:18px;height:18px}
.btn:hover{
  background:var(--hx-accent-2);
  box-shadow:0 0 22px rgba(95,227,192,0.30);
}
.btn:active{transform:scale(0.975)}
.btn:disabled{opacity:0.36;cursor:not-allowed;box-shadow:none;transform:none}

.btn.bloc{width:100%;padding:15px;font-size:0.94rem;margin-top:20px}
.btn.petit{padding:9px 17px;font-size:0.75rem;letter-spacing:0.03em}

.btn.discret{
  background:transparent;color:var(--hx-gris);
  border-color:var(--hx-bordure);
}
.btn.discret:hover{
  background:rgba(255,255,255,0.06);color:#fff;
  border-color:var(--hx-bordure-vive);box-shadow:none;
}
.btn.danger{
  background:transparent;color:var(--hx-rouge);
  border-color:rgba(255,77,94,0.35);
}
.btn.danger:hover{
  background:rgba(255,77,94,0.10);color:#fff;
  border-color:rgba(255,77,94,0.65);
  box-shadow:0 0 20px rgba(255,77,94,0.22);
}

/* ══════════════ JOURNAL ══════════════ */
.journal-zone{position:relative}
pre{
  margin:0;padding:20px;
  border-radius:var(--radius-card);
  background:rgba(0,0,0,0.55);
  color:rgba(140,235,205,0.92);
  font-family:'Courier New',ui-monospace,monospace;
  font-size:0.755rem;line-height:1.72;
  max-height:440px;overflow:auto;
  white-space:pre-wrap;word-break:break-word;
  border:1px solid var(--hx-bordure);
  box-shadow:inset 0 0 40px rgba(95,227,192,0.05);
}
pre::-webkit-scrollbar{width:9px;height:9px}
pre::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.16);border-radius:10px}
.journal-barre{
  display:flex;gap:10px;align-items:center;justify-content:flex-end;
  margin-bottom:12px;flex-wrap:wrap;
}
.auto-defile{
  display:inline-flex;align-items:center;gap:8px;
  font-size:0.74rem;color:var(--hx-gris);cursor:pointer;user-select:none;
}
.auto-defile input{
  accent-color:var(--hx-accent);width:15px;height:15px;cursor:pointer;
}

/* ══════════════ MODALE ══════════════ */
.voile{
  position:fixed;inset:0;background:rgba(0,0,0,0.72);
  backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
  z-index:900;display:flex;align-items:center;justify-content:center;
  padding:20px;opacity:0;pointer-events:none;transition:opacity .22s ease;
}
.voile.ouvert{opacity:1;pointer-events:auto}
.modale{
  background:linear-gradient(160deg,#151A21,#0A0D11);
  border-radius:var(--radius-card);
  width:100%;max-width:440px;
  box-shadow:0 0 0 1px var(--hx-bordure-vive), 0 30px 70px rgba(0,0,0,0.8);
  padding:30px 28px 26px;
  transform:translateY(14px) scale(0.97);opacity:0;
  transition:transform .24s cubic-bezier(0.34,1.3,0.64,1),opacity .2s;
  max-height:calc(100dvh - 40px);overflow:auto;
}
.voile.ouvert .modale{transform:translateY(0) scale(1);opacity:1}
.modale .picto{
  width:54px;height:54px;margin:0 auto 18px;
  display:flex;align-items:center;justify-content:center;
  border:1px solid rgba(95,227,192,0.4);border-radius:50%;
  background:rgba(95,227,192,0.10);
}
.modale .picto img{width:25px;height:25px;filter:brightness(0) invert(1);opacity:0.9}
.modale.danger .picto{
  border-color:rgba(255,77,94,0.45);background:rgba(255,77,94,0.10);
}
.modale h3{
  font-size:1.12rem;text-align:center;margin-bottom:8px;
  color:#fff;line-height:1.35;
}
.modale p{
  font-size:0.83rem;color:var(--hx-gris);text-align:center;
  line-height:1.6;margin-bottom:22px;
}
.modale .actions{display:flex;gap:10px}
.modale .actions .btn{flex:1;padding:12px;font-size:0.83rem}
.modale .detail{
  background:rgba(0,0,0,0.45);
  border:1px solid var(--hx-bordure);
  border-radius:6px;padding:12px 15px;
  font-size:0.77rem;margin-bottom:20px;
  max-height:140px;overflow:auto;
}
.modale .detail div{
  padding:6px 0;display:flex;justify-content:space-between;
  gap:14px;align-items:baseline;
  border-bottom:1px solid rgba(255,255,255,0.045);
}
.modale .detail div:last-child{border-bottom:0}
.modale .detail span:first-child{
  font-weight:500;color:#fff;flex:0 1 auto;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.modale .detail span:last-child{
  font-size:0.72rem;color:var(--hx-gris-2);flex:0 0 auto;
  font-family:'Courier New',ui-monospace,monospace;
}

/* ══════════════ DIVERS ══════════════ */
.erreur{
  margin-top:14px;padding:12px 16px;border-radius:6px;
  background:rgba(255,77,94,0.09);color:#FF8A96;
  font-size:0.80rem;
  border-left:2px solid var(--hx-rouge);
}
.conseil{
  display:flex;align-items:flex-start;gap:11px;margin-top:20px;
  padding-top:18px;border-top:1px solid var(--hx-bordure);
  font-size:0.74rem;color:var(--hx-gris-2);line-height:1.6;
}
.conseil img{width:17px;height:17px;flex-shrink:0;opacity:0.8}

/* formulaire de connexion */
.carte-form{max-width:430px;margin:0 auto}
label.champ{
  display:block;font-family:'Poppins',sans-serif;font-weight:500;
  font-size:0.78rem;margin-bottom:9px;
  color:var(--hx-gris);letter-spacing:0.08em;text-transform:uppercase;
}
input[type=password]{
  width:100%;padding:14px 17px;
  border:1px solid var(--hx-bordure);
  border-radius:var(--radius-input);
  font-size:0.96rem;font-family:'Inter',sans-serif;
  background:rgba(0,0,0,0.45);color:#fff;
  letter-spacing:0.2em;
  transition:border-color .18s,box-shadow .18s;
}
input[type=password]::placeholder{letter-spacing:0.2em;color:var(--hx-gris-2)}
input[type=password]:focus{
  outline:none;border-color:rgba(95,227,192,0.6);
  box-shadow:0 0 0 3px rgba(95,227,192,0.10);
}

.pied-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.pied-actions .btn{flex:1 1 180px;padding:13px;font-size:0.82rem}

.service-actif{
  display:inline-flex;align-items:center;gap:7px;
  background:rgba(95,227,192,0.10);color:var(--hx-accent);
  border:1px solid rgba(95,227,192,0.32);
  font-family:'Inter',sans-serif;font-size:0.70rem;font-weight:500;
  letter-spacing:0.06em;padding:4px 13px;border-radius:100px;
  text-transform:uppercase;
}
.service-actif::before{
  content:"";width:5px;height:5px;border-radius:50%;
  background:var(--hx-accent);box-shadow:0 0 8px var(--hx-accent);
}

/* ══════════════ PIED ══════════════ */
footer{
  background:rgba(3,4,6,0.95);
  margin-top:auto;padding:24px 16px;text-align:center;
  flex-shrink:0;border-top:1px solid var(--hx-bordure);
  position:relative;
}
footer::before{
  content:"";position:absolute;top:-1px;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(95,227,192,0.45),transparent);
}
footer .marque{
  display:flex;align-items:center;justify-content:center;gap:10px;
  margin-bottom:7px;
}
footer .marque img{height:22px;opacity:0.9;filter:drop-shadow(0 0 8px rgba(95,227,192,0.4))}
footer .marque span{
  font-family:'Poppins',sans-serif;font-weight:600;
  letter-spacing:0.30em;color:#fff;font-size:0.86rem;
}
footer .bas{
  font-size:0.66rem;color:var(--hx-gris-2);margin-top:6px;
  letter-spacing:0.06em;
}

/* ══════════════ RESPONSIVE ══════════════ */
@media(max-width:860px){
  .container{padding:0 16px}
  .card-pad{padding:20px 18px}
  .tableau-englobe{margin:0 -18px;padding:0 18px}
  .alert{padding:18px 18px;border-radius:6px;gap:13px}
  .alert h2{font-size:0.98rem}
  .alert .droite{margin-left:0;width:100%}
  dl{grid-template-columns:118px 1fr;font-size:0.82rem}
  table{font-size:0.77rem}
  thead th,tbody td{padding:10px 9px}
  pre{font-size:0.70rem;padding:15px}
  .stat .valeur{font-size:1.5rem}
  .modale{padding:24px 20px 20px}
}
@media(max-width:520px){
  header .nom{font-size:0.82rem;letter-spacing:0.20em}
  header .brand img{height:28px;width:28px}
  header .help span{display:none}
  .onglet{padding:10px 14px;font-size:0.74rem}
  .grille-stats{grid-template-columns:1fr 1fr;gap:11px}
  .barre-outils{gap:9px}
  .recherche{flex:1 1 100%}
  .stat{padding:16px 16px 14px}
  .stat .valeur{font-size:1.35rem}
  .stat .libelle{font-size:0.60rem;letter-spacing:0.12em}
}
@media(pointer:coarse){
  .btn{min-height:44px}
  .onglet{min-height:42px}
}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{
    animation-duration:0.01ms !important;
    animation-iteration-count:1 !important;
    transition-duration:0.01ms !important;
  }
  html{scroll-behavior:auto}
}
"""

_ENTETE = """<header>
  <div class="container">
    <div class="inner">
      <div class="brand">
        <img src="/hexaro-logo.png" alt="Hexaro">
        <span class="nom">HEXARO<small>Supervision</small></span>
      </div>
      <div class="help">
        <img src="/icon-info.png" alt="">
        <span>Espace technique</span>
      </div>
    </div>
  </div>
</header>"""

_PIED = """<footer>
  <div class="marque">
    <img src="/hexaro-logo.png" alt="Hexaro">
    <span>HEXARO</span>
  </div>
  <div class="bas">&copy; 2026 HEXARO — Portail interne de supervision</div>
</footer>"""

_JS = """
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };

  /* ── Éléments ─────────────────────────────────────────────────────── */
  var corps         = $('corps');
  var journal       = $('journal');
  var essais        = $('essais');
  var compteEssais  = $('compte-essais');
  var compte        = $('compte');
  var pastilleEssais    = $('pastille-essais');
  var pastilleAppareils = $('pastille-appareils');
  var maj           = $('maj');
  var etat          = $('etat');
  var recherche     = $('recherche');
  var toutCocher    = $('tout-cocher');
  var btnSupprimer  = $('btn-supprimer');
  var btnToutEffacer = $('btn-tout-supprimer');
  var autoDefile    = $('auto-defile');

  var stats = {
    appareils: $('st-appareils'), essais: $('st-essais'), valides: $('st-valides')
  };

  /* ── État local ───────────────────────────────────────────────────── */
  var donneesEssais = [];
  var selection = new Set();
  var triColonne = 'id';
  var triSens = -1;          // -1 = décroissant
  var filtre = '';

  var MOTIFS = {
    '': 'soumis',
    'criteres': 'refusé (critères)',
    'correspondance': 'refusé (confirmation)',
    'identite': 'refusé (case non cochée)',
    'vide': 'refusé (champ vide)'
  };

  /* ── Onglets ──────────────────────────────────────────────────────── */
  var onglets = Array.prototype.slice.call(document.querySelectorAll('.onglet'));
  onglets.forEach(function (bouton) {
    bouton.addEventListener('click', function () {
      onglets.forEach(function (autre) {
        autre.setAttribute('aria-selected', autre === bouton ? 'true' : 'false');
        var panneau = $('panneau-' + autre.dataset.panneau);
        if (panneau) { panneau.classList.toggle('actif', autre === bouton); }
      });
    });
  });

  /* ── Modale ───────────────────────────────────────────────────────── */
  var voile = $('voile');
  var modale = $('modale');
  var modaleTitre = $('modale-titre');
  var modaleTexte = $('modale-texte');
  var modaleDetail = $('modale-detail');
  var modalePicto = $('modale-picto');
  var modaleConfirmer = $('modale-confirmer');
  var modaleAnnuler = $('modale-annuler');
  var actionModale = null;
  var dernierFocus = null;

  function ouvrirModale(options) {
    dernierFocus = document.activeElement;
    modaleTitre.textContent = options.titre || '';
    modaleTexte.textContent = options.texte || '';
    modalePicto.innerHTML = '<img src="/icon-warning.png" alt="" style="filter:brightness(0) invert(1)">';
    modale.classList.toggle('danger', options.danger !== false);
    modaleConfirmer.textContent = options.confirmer || 'Confirmer';
    modaleConfirmer.className = 'btn ' + (options.danger !== false ? 'danger' : '');
    modaleDetail.innerHTML = '';
    if (options.details && options.details.length) {
      options.details.forEach(function (ligne) {
        var d = document.createElement('div');
        var a = document.createElement('span');
        var b = document.createElement('span');
        a.textContent = ligne[0];
        b.textContent = ligne[1];
        d.appendChild(a); d.appendChild(b);
        modaleDetail.appendChild(d);
      });
    }
    actionModale = options.action || null;
    voile.classList.add('ouvert');
    setTimeout(function () { modaleConfirmer.focus(); }, 60);
  }

  function fermerModale() {
    voile.classList.remove('ouvert');
    actionModale = null;
    if (dernierFocus && dernierFocus.focus) { dernierFocus.focus(); }
  }

  modaleAnnuler.addEventListener('click', fermerModale);
  voile.addEventListener('click', function (e) { if (e.target === voile) { fermerModale(); } });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && voile.classList.contains('ouvert')) { fermerModale(); }
  });
  modaleConfirmer.addEventListener('click', function () {
    var action = actionModale;
    fermerModale();
    if (typeof action === 'function') { action(); }
  });

  /* ── Rendu : appareils ────────────────────────────────────────────── */
  function cellule(texte, classe) {
    var td = document.createElement('td');
    td.textContent = texte;
    if (classe) { td.className = classe; }
    return td;
  }

  function rendre(appareils) {
    corps.innerHTML = '';
    if (!appareils.length) {
      var tr0 = document.createElement('tr');
      var td0 = cellule('Aucun appareil pour le moment.', 'vide');
      td0.colSpan = 5;
      tr0.appendChild(td0);
      corps.appendChild(tr0);
      return;
    }
    appareils.forEach(function (paire) {
      var ip = paire[0];
      var infos = paire[1] || {};
      var tr = document.createElement('tr');
      tr.appendChild(cellule(ip, 'ip'));
      tr.appendChild(cellule(infos.nom || '—', 'nom'));
      tr.appendChild(cellule(infos.systeme || '—'));
      tr.appendChild(cellule(infos.modele || '—'));
      tr.appendChild(cellule(infos.mac || '—', 'mono'));
      corps.appendChild(tr);
    });
  }

  /* ── Rendu : identifications ──────────────────────────────────────── */
  function valeurTri(e, colonne) {
    if (colonne === 'id') { return e.id || 0; }
    if (colonne === 'duree' || colonne === 'longueur') { return Number(e[colonne] || 0); }
    return String(e[colonne] === undefined || e[colonne] === null ? '' : e[colonne]).toLowerCase();
  }

  function essaisAffiches() {
    var liste = donneesEssais.slice();
    if (filtre) {
      var f = filtre.toLowerCase();
      liste = liste.filter(function (e) {
        return [e.utilisateur, e.ip, e.systeme, MOTIFS[e.motif] || '']
          .some(function (v) { return String(v || '').toLowerCase().indexOf(f) !== -1; });
      });
    }
    liste.sort(function (a, b) {
      var va = valeurTri(a, triColonne), vb = valeurTri(b, triColonne);
      if (va < vb) { return -1 * triSens; }
      if (va > vb) { return 1 * triSens; }
      return 0;
    });
    return liste;
  }

  function majBoutons() {
    var n = selection.size;
    btnSupprimer.disabled = n === 0;
    btnSupprimer.innerHTML = '';
    var img = document.createElement('img');
    img.src = '/icon-check.png';
    img.alt = '';
    img.style.cssText = 'filter:none;opacity:' + (n ? '1' : '0.5');
    btnSupprimer.appendChild(img);
    btnSupprimer.appendChild(document.createTextNode(
      n ? ' Supprimer (' + n + ')' : ' Supprimer la sélection'
    ));
    btnToutEffacer.disabled = donneesEssais.length === 0;
    var visibles = essaisAffiches();
    var tousCoches = visibles.length > 0 && visibles.every(function (e) { return selection.has(e.id); });
    toutCocher.checked = tousCoches;
    toutCocher.indeterminate = !tousCoches && visibles.some(function (e) { return selection.has(e.id); });
  }

  function rendreEssais() {
    var liste = essaisAffiches();
    essais.innerHTML = '';
    compteEssais.textContent = donneesEssais.length
      ? '(' + liste.length + (filtre ? ' sur ' + donneesEssais.length : '') + ')'
      : '';
    pastilleEssais.textContent = donneesEssais.length;

    if (!liste.length) {
      var tr0 = document.createElement('tr');
      var td0 = cellule(filtre ? 'Aucun résultat pour ce filtre.' : 'Aucune identification pour le moment.', 'vide');
      td0.colSpan = 7;
      tr0.appendChild(td0);
      essais.appendChild(tr0);
      majBoutons();
      return;
    }

    var fragment = document.createDocumentFragment();
    liste.forEach(function (e) {
      var tr = document.createElement('tr');
      if (selection.has(e.id)) { tr.className = 'selectionne'; }

      var tdCase = document.createElement('td');
      var casee = document.createElement('input');
      casee.type = 'checkbox';
      casee.style.cssText = 'width:17px;height:17px;accent-color:#00BE80;cursor:pointer';
      casee.checked = selection.has(e.id);
      casee.setAttribute('aria-label', 'Sélectionner ' + (e.utilisateur || e.ip));
      casee.addEventListener('change', function () {
        if (casee.checked) { selection.add(e.id); } else { selection.delete(e.id); }
        tr.classList.toggle('selectionne', casee.checked);
        majBoutons();
      });
      tdCase.appendChild(casee);
      tr.appendChild(tdCase);

      tr.appendChild(cellule(e.quand || '—', 'mono'));
      tr.appendChild(cellule(e.utilisateur || '—', 'nom'));
      tr.appendChild(cellule(e.ip || '—', 'ip'));
      tr.appendChild(cellule(e.systeme || 'inconnu'));
      tr.appendChild(cellule((e.duree || 0) + ' s'));

      var tdEtat = document.createElement('td');
      var pastille = document.createElement('span');
      var motif = MOTIFS[e.motif] !== undefined ? MOTIFS[e.motif] : 'soumis';
      pastille.className = 'pastille-etat ' + (e.valide ? 'ok' : 'ko');
      pastille.textContent = motif;
      tdEtat.appendChild(pastille);
      tr.appendChild(tdEtat);

      fragment.appendChild(tr);
    });
    essais.appendChild(fragment);
    majBoutons();
  }

  /* ── Tri ──────────────────────────────────────────────────────────── */
  Array.prototype.slice.call(document.querySelectorAll('th.triable')).forEach(function (th) {
    th.addEventListener('click', function () {
      var colonne = th.dataset.tri;
      if (triColonne === colonne) {
        triSens = -triSens;
      } else {
        triColonne = colonne;
        triSens = colonne === 'id' ? -1 : 1;
      }
      Array.prototype.slice.call(document.querySelectorAll('th.triable')).forEach(function (autre) {
        autre.removeAttribute('aria-sort');
        var fleche = autre.querySelector('.fleche');
        if (fleche) { fleche.textContent = '↕'; }
      });
      th.setAttribute('aria-sort', triSens === 1 ? 'ascending' : 'descending');
      var f = th.querySelector('.fleche');
      if (f) { f.textContent = triSens === 1 ? '↑' : '↓'; }
      rendreEssais();
    });
  });

  /* ── Recherche ────────────────────────────────────────────────────── */
  var minuteur = null;
  recherche.addEventListener('input', function () {
    clearTimeout(minuteur);
    minuteur = setTimeout(function () {
      filtre = recherche.value.trim();
      rendreEssais();
    }, 160);
  });

  /* ── Sélection globale ────────────────────────────────────────────── */
  toutCocher.addEventListener('change', function () {
    var visibles = essaisAffiches();
    if (toutCocher.checked) {
      visibles.forEach(function (e) { selection.add(e.id); });
    } else {
      visibles.forEach(function (e) { selection.delete(e.id); });
    }
    rendreEssais();
  });

  /* ── Suppression ──────────────────────────────────────────────────── */
  var base = '/admin/etat';

  function poster(url, corps) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corps || {})
    }).then(function (r) {
      if (!r.ok) { throw new Error('statut ' + r.status); }
      return r.json();
    });
  }

  btnSupprimer.addEventListener('click', function () {
    var ids = Array.from(selection);
    if (!ids.length) { return; }
    var lignes = donneesEssais.filter(function (e) { return selection.has(e.id); });
    var apercu = lignes.slice(0, 5).map(function (e) {
      return [e.utilisateur || '—', e.quand || ''];
    });
    if (lignes.length > 5) { apercu.push(['… et ' + (lignes.length - 5) + ' autre(s)', '']); }
    ouvrirModale({
      titre: 'Supprimer ' + ids.length + ' identification' + (ids.length > 1 ? 's' : '') + ' ?',
      texte: 'Cette action est définitive. Les lignes choisies seront effacées de la base.',
      details: apercu,
      confirmer: 'Supprimer',
      danger: true,
      action: function () {
        poster(base + '/supprimer', { ids: ids }).then(function () {
          selection.clear();
          rafraichir();
        }).catch(function () { signalerErreur(); });
      }
    });
  });

  btnToutEffacer.addEventListener('click', function () {
    ouvrirModale({
      titre: 'Tout effacer ?',
      texte: 'Les ' + donneesEssais.length + ' identifications enregistrées seront définitivement supprimées. '
           + 'Cette action ne peut pas être annulée.',
      confirmer: 'Tout effacer',
      danger: true,
      action: function () {
        poster(base + '/vider', {}).then(function () {
          selection.clear();
          rafraichir();
        }).catch(function () { signalerErreur(); });
      }
    });
  });

  var erreurAffichee = false;
  function signalerErreur() {
    if (erreurAffichee) { return; }
    erreurAffichee = true;
    ouvrirModale({
      titre: 'Suppression impossible',
      texte: 'Le serveur n\\'a pas confirmé la suppression. Vérifie la connexion puis réessaie.',
      confirmer: 'Fermer',
      danger: true,
      action: null
    });
    setTimeout(function () { erreurAffichee = false; }, 3000);
  }

  /* ── Copier le journal ────────────────────────────────────────────── */
  $('btn-copier').addEventListener('click', function () {
    var bouton = this;
    var texte = journal.textContent || '';
    var fini = function () {
      bouton.textContent = 'Copié';
      setTimeout(function () { bouton.textContent = 'Copier'; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texte).then(fini).catch(function () {
        bouton.textContent = 'Impossible';
      });
    } else {
      var zone = document.createElement('textarea');
      zone.value = texte;
      document.body.appendChild(zone);
      zone.select();
      try { document.execCommand('copy'); fini(); } catch (e) {} 
      document.body.removeChild(zone);
    }
  });

  /* ── Rafraîchissement ─────────────────────────────────────────────── */
  var dernierJournal = '';

  function rafraichir() {
    fetch('/admin/etat', { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) { throw new Error('statut ' + r.status); }
        return r.json();
      })
      .then(function (d) {
        donneesEssais = d.essais || [];
        // On oublie les sélections qui ne correspondent plus à une ligne existante.
        var existants = new Set(donneesEssais.map(function (e) { return e.id; }));
        selection.forEach(function (id) { if (!existants.has(id)) { selection.delete(id); } });

        rendre(d.appareils || []);
        rendreEssais();

        var s = d.stats || {};
        var montrer = function (el, valeur) {
          if (!el) { return; }
          el.textContent = (valeur === undefined || valeur === null) ? '—' : valeur;
        };
        montrer(stats.appareils, s.appareils);
        montrer(stats.essais, s.essais);
        montrer(stats.valides, s.essais_valides);

        compte.textContent = (d.appareils || []).length ? '(' + (d.appareils || []).length + ')' : '';
        pastilleAppareils.textContent = (d.appareils || []).length;

        var texteJournal = (d.journal || []).length ? d.journal.join('\\n') : 'Journal vide.';
        if (texteJournal !== dernierJournal) {
          journal.textContent = texteJournal;
          dernierJournal = texteJournal;
          if (autoDefile.checked) {
            journal.scrollTop = journal.scrollHeight;
          }
        }

        maj.textContent = d.maj || '';
        etat.textContent = 'En direct';
        etat.className = 'badge live';
      })
      .catch(function () {
        etat.textContent = 'Hors ligne';
        etat.className = 'badge live hors';
      });
  }

  rafraichir();
  setInterval(function () {
    // On ne rafraîchit pas pendant une confirmation : ça éviterait de perturber la modale.
    if (!voile.classList.contains('ouvert')) { rafraichir(); }
  }, 2500);
})();
"""


def page_connexion(message=None, erreur=False):
    bloc = f'<p class="erreur">{html.escape(message)}</p>' if message else ""
    return f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Hexaro — Espace technique</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{_STYLE}</style>
</head><body>
{_ENTETE}
<main class="container">
  <div class="alert">
    <div class="icon-badge"><img src="/icon-warning.png" alt=""></div>
    <div>
      <span class="badge">Accès restreint</span>
      <h2>Supervision du portail</h2>
      <p>Espace réservé au personnel technique. Saisis la clé d'accès pour consulter les appareils connectés et le journal du portail.</p>
    </div>
  </div>

  <div class="card"><div class="card-pad carte-form">
    <h2 class="titre">Clé d'accès</h2>
    <form method="post" action="/admin" autocomplete="off">
      <label class="champ" for="cle">Clé</label>
      <input id="cle" name="cle" type="password" inputmode="numeric"
             autocomplete="current-password" required autofocus placeholder="••••">
      <button type="submit" class="btn bloc">
        <img src="/icon-check.png" alt=""> Entrer
      </button>
    </form>
    {bloc}
    <div class="conseil">
      <img src="/icon-info.png" alt="">
      <div>Après 5 clés incorrectes, l'accès est bloqué pendant une minute.</div>
    </div>
  </div></div>
</main>
{_PIED}
</body></html>
"""


def page_tableau(ssid, canal, nom_page):
    return f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Hexaro — Supervision</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{_STYLE}</style>
</head><body>
{_ENTETE}
<main class="container">

  <div class="alert">
    <div class="icon-badge"><img src="/icon-warning.png" alt=""></div>
    <div>
      <span class="badge live" id="etat">En direct</span>
      <h2>Supervision du portail</h2>
      <p>Mise à jour automatique · dernière synchronisation <span id="maj">—</span></p>
    </div>
    <div class="droite">
      <a class="btn discret petit" href="/admin?sortie=1">Déconnexion</a>
    </div>
  </div>

  <nav class="onglets" role="tablist" aria-label="Sections du tableau de bord">
    <button class="onglet" role="tab" data-panneau="apercu" aria-selected="true">
      Vue d'ensemble
    </button>
    <button class="onglet" role="tab" data-panneau="identifications" aria-selected="false">
      Identifications <span class="pastille" id="pastille-essais">0</span>
    </button>
    <button class="onglet" role="tab" data-panneau="appareils" aria-selected="false">
      Appareils <span class="pastille" id="pastille-appareils">0</span>
    </button>
    <button class="onglet" role="tab" data-panneau="journal" aria-selected="false">
      Journal
    </button>
  </nav>

  <!-- ============ VUE D'ENSEMBLE ============ -->
  <section class="panneau actif" id="panneau-apercu" role="tabpanel">
    <div class="grille-stats">
      <div class="stat"><div class="valeur" id="st-essais">—</div><div class="libelle">Identifications</div></div>
      <div class="stat"><div class="valeur" id="st-valides">—</div><div class="libelle">Validées</div></div>
      <div class="stat"><div class="valeur" id="st-appareils">—</div><div class="libelle">Appareils</div></div>
    </div>

    <div class="card"><div class="card-pad">
      <div class="card-tete">
        <h2 class="titre">Portail actif</h2>
        <span class="service-actif">{html.escape(nom_page)}</span>
      </div>
      <dl>
        <dt>Service</dt><dd>{html.escape(nom_page)}</dd>
        <dt>Nom du Wi-Fi</dt><dd>{html.escape(ssid or '—')}</dd>
        <dt>Canal</dt><dd>{html.escape(canal or '—')}</dd>
      </dl>
      <div class="conseil">
        <img src="/icon-info.png" alt="">
        <div>Le portail ne comporte aucun champ de mot de passe : seul le nom d'utilisateur
        saisi est enregistré, avec l'heure, l'appareil et la durée.</div>
      </div>
    </div></div>
  </section>

  <!-- ============ IDENTIFICATIONS ============ -->
  <section class="panneau" id="panneau-identifications" role="tabpanel">
    <div class="card"><div class="card-pad">
      <div class="card-tete">
        <h2 class="titre">Identifications <span class="compte" id="compte-essais"></span></h2>
        <div class="barre-outils" style="margin:0">
          <button class="btn danger petit" id="btn-tout-supprimer" disabled>
            <img src="/icon-check.png" alt="" style="filter:brightness(0) invert(1)"> Tout effacer
          </button>
        </div>
      </div>

      <div class="barre-outils">
        <div class="recherche">
          <input type="search" id="recherche" placeholder="Filtrer par nom, IP, appareil…" aria-label="Rechercher une identification">
        </div>
        <button class="btn discret petit" id="btn-supprimer" disabled>
          <img src="/icon-check.png" alt="" style="filter:none;opacity:0.5"> Supprimer la sélection
        </button>
      </div>

      <div class="tableau-englobe">
        <table>
          <thead><tr>
            <th style="width:38px"><input type="checkbox" id="tout-cocher" aria-label="Tout sélectionner" style="width:17px;height:17px;accent-color:#00BE80;cursor:pointer"></th>
            <th class="triable" data-tri="quand">Heure <span class="fleche">↕</span></th>
            <th class="triable" data-tri="utilisateur">Nom d'utilisateur <span class="fleche">↕</span></th>
            <th class="triable" data-tri="ip">IP <span class="fleche">↕</span></th>
            <th class="triable" data-tri="systeme">Appareil <span class="fleche">↕</span></th>
            <th class="triable" data-tri="duree">Durée <span class="fleche">↕</span></th>
            <th class="triable" data-tri="motif">Résultat <span class="fleche">↕</span></th>
          </tr></thead>
          <tbody id="essais"><tr><td colspan="7" class="vide">Chargement…</td></tr></tbody>
        </table>
      </div>
    </div></div>
  </section>

  <!-- ============ APPAREILS ============ -->
  <section class="panneau" id="panneau-appareils" role="tabpanel">
    <div class="card"><div class="card-pad">
      <div class="card-tete">
        <h2 class="titre">Appareils connectés <span class="compte" id="compte"></span></h2>
      </div>
      <div class="tableau-englobe">
        <table>
          <thead><tr>
            <th>IP</th><th>Nom annoncé</th><th>Système</th><th>Modèle</th><th>MAC</th>
          </tr></thead>
          <tbody id="corps"><tr><td colspan="5" class="vide">Chargement…</td></tr></tbody>
        </table>
      </div>
    </div></div>
  </section>

  <!-- ============ JOURNAL ============ -->
  <section class="panneau" id="panneau-journal" role="tabpanel">
    <div class="card"><div class="card-pad">
      <div class="card-tete"><h2 class="titre">Journal du portail</h2></div>
      <div class="journal-barre">
        <label class="auto-defile">
          <input type="checkbox" id="auto-defile" checked> Suivre la fin
        </label>
        <button class="btn discret petit" id="btn-copier">Copier</button>
      </div>
      <div class="journal-zone"><pre id="journal">Chargement…</pre></div>
    </div></div>
  </section>

</main>

<!-- ============ MODALES ============ -->
<div class="voile" id="voile" role="dialog" aria-modal="true" aria-labelledby="modale-titre">
  <div class="modale" id="modale">
    <div class="picto" id="modale-picto"><img src="/icon-warning.png" alt="" style="filter:brightness(0) invert(1)"></div>
    <h3 id="modale-titre">Titre</h3>
    <p id="modale-texte">Texte</p>
    <div id="modale-detail"></div>
    <div class="actions">
      <button class="btn discret" id="modale-annuler">Annuler</button>
      <button class="btn danger" id="modale-confirmer">Confirmer</button>
    </div>
  </div>
</div>

{_PIED}
<script>{_JS}</script>
</body></html>
"""
