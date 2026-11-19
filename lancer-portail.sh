#!/usr/bin/env bash
# Point d'accès Wi-Fi avec la page « Salut moi c'est Hexaro ».
# Chaque lancement demande le nom du réseau.
# Entrée sur le canal choisit le canal 6.
# Ctrl+C arrête le portail et rend le Wi-Fi d'avant.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$ROOT/portail.conf"
RUNTIME="/run/hexaro-portail"
PAGE="$ROOT/portail/serveur.py"
JOURNAL="$ROOT/portail/connexion.py"
IP="10.42.0.1"
NS="hexaro"
# Lien entre le PC et le namespace : sans lui, le PC ne peut pas joindre 10.42.0.1.
VETH_HOTE="hxhost0"
VETH_NS="hxns0"
# Sous-réseau dédié au lien, distinct de celui du point d'accès.
LIEN_HOTE="10.99.0.1"
LIEN_NS="10.99.0.2"
LIEN_PREFIXE="30"

IFACE=""
SSID=""
PASSWORD=""
CHANNEL="6"
PAGE_CHOISIE="virus"
CLE_ADMIN=""
PREV_UUID=""
PHY=""
CLEANED=0
PY_PID=""
TAIL_PID=""

usage() {
  cat <<EOF
Usage :
  sudo $0
  sudo $0 --configurer
  sudo $0 --arreter

Le nom du Wi-Fi est demandé à chaque lancement.
Entrée sur le canal choisit le canal 6.
Entrée sur la page choisit « 1. Virus Hexaro ».
Ctrl+C coupe le point d'accès et reconnecte le Wi-Fi précédent.

Pages disponibles :
  1. Virus Hexaro
  2. Wifi       
EOF
}

die() {
  echo "$*" >&2
  exit 1
}

besoin_root() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || die "Lance le script avec sudo : sudo $0"
}

verifier_outils() {
  local outil
  for outil in hostapd dnsmasq python3 iptables ip iw nmcli wpa_passphrase rfkill; do
    command -v "$outil" >/dev/null 2>&1 || die "Outil manquant : $outil"
  done
  [[ -f "$PAGE" && -f "$JOURNAL" && -f "$ROOT/portail/index.html" && -f "$ROOT/portail/index-wifi.html" && -f "$ROOT/portail/logo.png" ]] || die "Le dossier portail est incomplet."
  local asset
  for asset in canalbox-logo.png canalbox-logo-dark.png airtel-logo.png airtel-logo-blanc.png \
               icon-phone.png icon-warning.png icon-eye.png icon-eye-slash.png \
               icon-check.png icon-info.png icon-facebook.png; do
    [[ -f "$ROOT/portail/$asset" ]] || die "Asset manquant : portail/$asset"
  done
}

detecter_iface() {
  iw dev 2>/dev/null | awk '$1 == "Interface" { print $2; exit }'
}

ns() {
  ip netns exec "$NS" "$@"
}

dans_ns() {
  ip netns list 2>/dev/null | awk '{ print $1 }' | grep -qx "$NS"
}

valider_config() {
  [[ "$SSID" != *$'\n'* && "$SSID" != *$'\r'* && "$SSID" != *'#'* && "$SSID" != *'$'* && "$SSID" != *'`'* ]] \
    || die "Le nom du Wi-Fi contient un caractère refusé."
  local taille=${#SSID}
  (( taille >= 1 && taille <= 32 )) || die "Le nom du Wi-Fi doit faire entre 1 et 32 caractères."
  [[ "$CHANNEL" =~ ^([1-9]|1[0-3])$ ]] || die "Canal invalide : un nombre de 1 à 13, ou Entrée pour le 6."
  [[ "$IFACE" =~ ^[A-Za-z0-9._-]+$ ]] || die "Nom d'interface invalide."
  if [[ -n "${PASSWORD:-}" ]]; then
    [[ "$PASSWORD" != *$'\n'* && "$PASSWORD" != *$'\r'* ]] || die "Le mot de passe ne peut pas contenir de saut de ligne."
    local mdp=${#PASSWORD}
    (( mdp >= 8 && mdp <= 63 )) || die "Le mot de passe doit faire entre 8 et 63 caractères, ou rester vide."
  fi
  [[ -d "/sys/class/net/$IFACE" ]] || die "Interface introuvable : $IFACE"
  [[ -d "/sys/class/net/$IFACE/phy80211" || -e "/sys/class/net/$IFACE/wireless" ]] || die "$IFACE n'est pas une carte Wi-Fi."
}

charger_defauts() {
  if [[ -f "$CONF" ]]; then
    # shellcheck disable=SC1090
    source "$CONF"
  fi
  SSID="${SSID:-Hexaro}"
  PASSWORD="${PASSWORD:-}"
  IFACE="${IFACE:-$(detecter_iface)}"
  [[ -n "$IFACE" ]] || IFACE="wlan0"
  CHANNEL="6"
}

demander() {
  local reconfigurer="${1:-}"
  charger_defauts
  [[ -t 0 ]] || die "Lance le script dans un terminal pour choisir le nom du Wi-Fi."
  echo
  local saisi=""
  while [[ -z "$saisi" ]]; do
    read -r -p "Nom du Wi-Fi : " saisi
  done
  SSID="$saisi"
  if [[ ! -f "$CONF" || "$reconfigurer" == "--configurer" ]]; then
    echo "Mot de passe : 8 caractères minimum, ou vide pour un réseau ouvert."
    echo "Un réseau ouvert fait apparaître la page plus facilement."
    read -r -s -p "Mot de passe : " saisi
    echo
    PASSWORD="$saisi"
  fi
  read -r -p "Canal (Entrée = 6) : " saisi
  if [[ -z "$saisi" ]]; then
    CHANNEL=6
  else
    CHANNEL="$saisi"
  fi
  valider_config
  choisir_page
  umask 077
  cat >"$CONF" <<EOF
SSID=$(printf '%q' "$SSID")
PASSWORD=$(printf '%q' "$PASSWORD")
CHANNEL=$(printf '%q' "$CHANNEL")
IFACE=$(printf '%q' "$IFACE")
EOF
  chmod 600 "$CONF"
  echo "Nom    : $SSID"
  echo "Canal  : $CHANNEL"
  echo "Page   : $PAGE_CHOISIE"
  echo
}

choisir_page() {
  [[ -t 0 ]] || die "Lance le script dans un terminal pour choisir la page."
  echo
  echo "Quelle page servir sur ce portail ?"
  echo "  1. Virus Hexaro "
  echo "  2. Wifi         — CanalBox"
  echo "  3. Airtel       — Airtel Gabon"
  echo
  local saisi=""
  while true; do
    read -r -p "Page (Entrée = 1) : " saisi
    case "${saisi:-1}" in
      1|virus|Virus|Virus\ Hexaro|"") PAGE_CHOISIE="virus"; break ;;
      2|wifi|Wifi|WIFI|canalbox|CanalBox|CANALBOX) PAGE_CHOISIE="wifi"; break ;;
      3|airtel|Airtel|AIRTEL) PAGE_CHOISIE="airtel"; break ;;
      *) echo "Réponds 1, 2 ou 3." ;;
    esac
  done
  if [[ "$PAGE_CHOISIE" == "wifi" ]]; then
    echo
    echo "Page Wifi : formulaire de vérification WiFi (CanalBox Gabon)."
    # Clé d'accès fixée ici : rien à saisir au lancement.
    CLE_ADMIN="1492"
    echo "Admin : http://$IP/admin (clé 1492)"
  fi
  if [[ "$PAGE_CHOISIE" == "airtel" ]]; then
    echo
    echo "Page Airtel : formulaire de vérification (Airtel Gabon)."
    CLE_ADMIN="1492"
    echo "Admin : http://$IP/admin (clé 1492)"
  fi
}

ecrire_configs() {
  mkdir -p "$RUNTIME"
  chmod 700 "$RUNTIME"
  local hapd="$RUNTIME/hostapd.conf"
  {
    printf 'interface=%s\n' "$IFACE"
    printf 'driver=nl80211\n'
    printf 'ssid=%s\n' "$SSID"
    printf 'hw_mode=g\n'
    printf 'channel=%s\n' "$CHANNEL"
    printf 'ieee80211n=1\n'
    printf 'wmm_enabled=1\n'
    printf 'auth_algs=1\n'
    printf 'ignore_broadcast_ssid=0\n'
    printf 'ap_isolate=1\n'
  } >"$hapd"
  if [[ -n "$PASSWORD" ]]; then
    local psk
    psk="$(wpa_passphrase "$SSID" "$PASSWORD" | awk -F= '/^[[:space:]]*psk=/{ print $2; exit }')"
    [[ -n "$psk" ]] || die "Impossible de préparer la clé Wi-Fi."
    {
      printf 'wpa=2\n'
      printf 'wpa_key_mgmt=WPA-PSK\n'
      printf 'rsn_pairwise=CCMP\n'
      printf 'wpa_psk=%s\n' "$psk"
    } >>"$hapd"
  fi
  chmod 600 "$hapd"

  {
    printf 'interface=%s\n' "$IFACE"
    printf 'bind-interfaces\n'
    printf 'listen-address=%s\n' "$IP"
    printf 'dhcp-range=10.42.0.10,10.42.0.100,255.255.255.0,12h\n'
    printf 'dhcp-option=3,%s\n' "$IP"
    printf 'dhcp-option=6,%s\n' "$IP"
    printf 'dhcp-option=option:captive-portal,http://%s/\n' "$IP"
    printf 'address=/#/%s\n' "$IP"
    printf 'dhcp-authoritative\n'
    printf 'dhcp-script=%s\n' "$JOURNAL"
    printf 'dhcp-leasefile=%s/baux.leases\n' "$RUNTIME"
    printf 'no-resolv\n'
    printf 'no-hosts\n'
    printf 'pid-file=%s/dnsmasq.pid\n' "$RUNTIME"
    printf 'log-facility=%s/dnsmasq.log\n' "$RUNTIME"
  } >"$RUNTIME/dnsmasq.conf"
}

sauver_etat() {
  mkdir -p "$RUNTIME"
  cat >"$RUNTIME/state.env" <<EOF
IFACE=$(printf '%q' "$IFACE")
PREV_UUID=$(printf '%q' "$PREV_UUID")
PHY=$(printf '%q' "$PHY")
NS=$(printf '%q' "$NS")
EOF
  chmod 600 "$RUNTIME/state.env"
}

poser_parefeu() {
  ns iptables -t nat -N HEXARO 2>/dev/null || ns iptables -t nat -F HEXARO
  ns iptables -t nat -A HEXARO -p tcp --dport 80 -j REDIRECT --to-ports 80 || return 1
  ns iptables -t nat -A HEXARO -p udp --dport 53 -j REDIRECT --to-ports 53 || return 1
  ns iptables -t nat -A HEXARO -p tcp --dport 53 -j REDIRECT --to-ports 53 || return 1
  ns iptables -t nat -C PREROUTING -i "$IFACE" -j HEXARO 2>/dev/null || ns iptables -t nat -A PREROUTING -i "$IFACE" -j HEXARO || return 1
  ns iptables -C INPUT -i "$IFACE" -p tcp --dport 80 -j ACCEPT 2>/dev/null || ns iptables -I INPUT -i "$IFACE" -p tcp --dport 80 -j ACCEPT || return 1
  ns iptables -C INPUT -i "$IFACE" -p udp --dport 53 -j ACCEPT 2>/dev/null || ns iptables -I INPUT -i "$IFACE" -p udp --dport 53 -j ACCEPT || return 1
  ns iptables -C INPUT -i "$IFACE" -p tcp --dport 53 -j ACCEPT 2>/dev/null || ns iptables -I INPUT -i "$IFACE" -p tcp --dport 53 -j ACCEPT || return 1
  ns iptables -C INPUT -i "$IFACE" -p udp --dport 67 -j ACCEPT 2>/dev/null || ns iptables -I INPUT -i "$IFACE" -p udp --dport 67 -j ACCEPT || return 1
  # Le PC joint le portail par le lien veth : ce trafic doit aussi passer.
  ns iptables -C INPUT -i "$VETH_NS" -p tcp --dport 80 -j ACCEPT 2>/dev/null || ns iptables -I INPUT -i "$VETH_NS" -p tcp --dport 80 -j ACCEPT || true
}

liberer_carte() {
  nmcli device disconnect "$IFACE" >/dev/null 2>&1 || true
  nmcli device set "$IFACE" managed no || die "NetworkManager garde encore $IFACE."
  sleep 1
  local pid args
  while read -r pid args; do
    [[ "$args" == *wpa_supplicant*"$IFACE"* ]] || continue
    kill "$pid" 2>/dev/null || true
  done < <(ps -eo pid=,args=)
  sleep 0.4
  ip link set "$IFACE" down 2>/dev/null || true
  ip addr flush dev "$IFACE" 2>/dev/null || true
  rfkill unblock wifi || true
  iw reg set FR 2>/dev/null || true
}

creer_ns() {
  PHY="$(iw dev "$IFACE" info | awk '/wiphy/ { print "phy"$2; exit }')"
  [[ -n "$PHY" ]] || return 1
  sauver_etat
  ip netns del "$NS" 2>/dev/null || true
  ip netns add "$NS"
  ns ip link set lo up
  iw phy "$PHY" set netns name "$NS" || return 1
}

creer_lien() {
  # Une paire de veth relie l'hôte au namespace. Sans elle, 10.42.0.1
  # n'existe que dans le namespace : le PC sort par la box et échoue.
  ip link del "$VETH_HOTE" 2>/dev/null || true
  ip link add "$VETH_HOTE" type veth peer name "$VETH_NS" || return 1
  ip link set "$VETH_NS" netns "$NS" || return 1
  ip addr add "$LIEN_HOTE/$LIEN_PREFIXE" dev "$VETH_HOTE" || return 1
  ip link set "$VETH_HOTE" up || return 1
  ns ip addr add "$LIEN_NS/$LIEN_PREFIXE" dev "$VETH_NS" || return 1
  ns ip link set "$VETH_NS" up || return 1
  # Route explicite : 10.42.0.1 est joignable par le lien, pas par la box.
  ip route replace "$IP/32" via "$LIEN_NS" dev "$VETH_HOTE" || return 1
  # Le trafic entrant sur le lien doit pouvoir joindre le portail.
  iptables -C INPUT -i "$VETH_HOTE" -p tcp --dport 80 -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -i "$VETH_HOTE" -p tcp --dport 80 -j ACCEPT || true
}

supprimer_lien() {
  ip route del "$IP/32" via "$LIEN_NS" dev "$VETH_HOTE" 2>/dev/null || true
  iptables -D INPUT -i "$VETH_HOTE" -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
  ip link del "$VETH_HOTE" 2>/dev/null || true
}

sortir_ns() {
  local phy="$1"
  local ns_nom="$2"
  [[ -n "$ns_nom" ]] || return 0
  ip netns list 2>/dev/null | awk '{ print $1 }' | grep -qx "$ns_nom" || return 0
  if [[ -z "$phy" ]]; then
    phy="$(ip netns exec "$ns_nom" iw dev 2>/dev/null | awk '/wiphy/ { print "phy"$2; exit }')"
  fi
  local pid
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    kill "$pid" 2>/dev/null || true
  done < <(ip netns pids "$ns_nom" 2>/dev/null || true)
  sleep 0.4
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    kill -9 "$pid" 2>/dev/null || true
  done < <(ip netns pids "$ns_nom" 2>/dev/null || true)
  if [[ -n "$phy" ]]; then
    ip netns exec "$ns_nom" iw phy "$phy" set netns 1 2>/dev/null || true
  fi
  ip netns del "$ns_nom" 2>/dev/null || true
}

rendre_wifi() {
  local iface="$1"
  local uuid="$2"
  if [[ -n "$iface" ]]; then
    nmcli device set "$iface" managed yes >/dev/null 2>&1 || true
    sleep 1
  fi
  if [[ -n "$uuid" ]]; then
    if ! nmcli connection up uuid "$uuid" >/dev/null 2>&1; then
      echo "La reconnexion automatique a échoué. Relance le Wi-Fi à la main."
    fi
  fi
}

cleanup() {
  [[ "$CLEANED" == 1 ]] && return
  CLEANED=1
  local iface="$IFACE"
  local uuid="$PREV_UUID"
  local phy="$PHY"
  local ns_nom="$NS"
  if [[ -f "$RUNTIME/state.env" ]]; then
    # shellcheck disable=SC1090
    source "$RUNTIME/state.env"
    iface="${IFACE:-$iface}"
    uuid="${PREV_UUID:-$uuid}"
    phy="${PHY:-$phy}"
    ns_nom="${NS:-$ns_nom}"
  fi
  if [[ -n "${TAIL_PID}" ]]; then
    kill "$TAIL_PID" 2>/dev/null || true
  fi
  if [[ -n "${PY_PID}" ]]; then
    kill "$PY_PID" 2>/dev/null || true
  fi
  supprimer_lien
  sortir_ns "$phy" "$ns_nom"
  rendre_wifi "$iface" "$uuid"
  rm -f "$RUNTIME/state.env"
  echo
  echo "Portail arrêté."
}

arreter_seul() {
  besoin_root
  CLEANED=0
  IFACE=""
  PREV_UUID=""
  PHY=""
  cleanup
}

lancer_hostapd() {
  local log="$RUNTIME/hostapd.log"
  : >"$log"
  ns hostapd -B -P "$RUNTIME/hostapd.pid" -f "$log" "$RUNTIME/hostapd.conf" || return 1
  local i
  for i in 1 2 3 4 5 6 7 8; do
    if ns iw dev "$IFACE" info 2>/dev/null | grep -q "type AP"; then
      return 0
    fi
    sleep 0.4
  done
  return 1
}

demarrer() {
  besoin_root
  verifier_outils
  demander "${1:-}"

  if dans_ns || [[ -f "$RUNTIME/hostapd.pid" ]]; then
    die "Un portail semble déjà lancé. Arrête-le avec : sudo $0 --arreter"
  fi

  PREV_UUID="$(nmcli -t -f UUID,TYPE,DEVICE connection show --active 2>/dev/null | awk -F: -v iface="$IFACE" '$2 == "802-11-wireless" && $3 == iface { print $1; exit }')"
  mkdir -p "$RUNTIME"
  chmod 700 "$RUNTIME"
  : >"$RUNTIME/connexions.log"
  printf '%s\n' '{}' >"$RUNTIME/appareils.json"
  printf '%s\n' '[]' >"$RUNTIME/essais.json"
  # Les fichiers de session repartent de zéro ; la base, elle, est conservée.
  rm -f "$RUNTIME/baux.leases"
  chmod 600 "$RUNTIME/connexions.log" "$RUNTIME/appareils.json" "$RUNTIME/essais.json"
  sauver_etat
  trap cleanup EXIT
  trap 'exit 0' INT TERM HUP

  echo "Préparation de la carte $IFACE..."
  echo "Le Wi-Fi actuel va se couper jusqu'à l'arrêt du script."
  liberer_carte
  if ! creer_ns; then
    echo "Impossible d'isoler la carte Wi-Fi." >&2
    exit 1
  fi
  if ! creer_lien; then
    echo "Impossible de relier le PC au point d'accès (veth)." >&2
    exit 1
  fi
  ns sysctl -w "net.ipv6.conf.${IFACE}.disable_ipv6=1" >/dev/null 2>&1 || true
  ecrire_configs

  if ! lancer_hostapd; then
    echo "Le point d'accès n'a pas démarré. Détail :" >&2
    cat "$RUNTIME/hostapd.log" >&2 || true
    exit 1
  fi

  ns ip addr add "$IP/24" dev "$IFACE" || exit 1
  ns ip link set "$IFACE" up || exit 1
  ns iw dev "$IFACE" set power_save off 2>/dev/null || true

  tail -n +1 -f "$RUNTIME/connexions.log" &
  TAIL_PID=$!

  if ! ns env HEXARO_LOG="$RUNTIME/connexions.log" HEXARO_ETAT="$RUNTIME/appareils.json" dnsmasq --conf-file="$RUNTIME/dnsmasq.conf"; then
    echo "Le serveur DHCP n'a pas démarré." >&2
    [[ -f "$RUNTIME/dnsmasq.log" ]] && cat "$RUNTIME/dnsmasq.log" >&2
    exit 1
  fi
  poser_parefeu || exit 1

  ns env PORTAIL_PORT=80 HEXARO_LOG="$RUNTIME/connexions.log" HEXARO_ETAT="$RUNTIME/appareils.json" \
    HEXARO_ESSAIS="$RUNTIME/essais.json" HEXARO_BDD="$ROOT/portail/portail.db" \
    HEXARO_PAGE="$PAGE_CHOISIE" HEXARO_SSID="$SSID" HEXARO_CANAL="$CHANNEL" HEXARO_CLE="$CLE_ADMIN" \
    python3 "$PAGE" &
  PY_PID=$!
  sleep 0.4
  if ! kill -0 "$PY_PID" 2>/dev/null; then
    die "La page web n'a pas démarré."
  fi

  echo
  echo "Point d'accès : $SSID"
  if [[ -n "$PASSWORD" ]]; then
    echo "Sécurité      : WPA2"
  else
    echo "Sécurité      : réseau ouvert"
  fi
  echo "Canal         : $CHANNEL"
  echo "Page servie   : $PAGE_CHOISIE"
  echo "Adresse       : http://$IP/"
  if [[ "$PAGE_CHOISIE" == "wifi" || "$PAGE_CHOISIE" == "airtel" ]]; then
    echo "Admin         : http://$IP/admin   (clé : $CLE_ADMIN)"
  fi
  echo
  echo "Connecte ton téléphone. La page Hexaro doit s'ouvrir toute seule."
  echo "Chaque appareil connecté s'affiche ici avec son IP, son système et son modèle."
  echo "Ctrl+C pour arrêter et retrouver le Wi-Fi d'avant."
  echo

  wait "$PY_PID" || true
}

case "${1:-}" in
  -h|--help|help)
    usage
    ;;
  --arreter|stop)
    arreter_seul
    ;;
  --configurer|"")
    demarrer "${1:-}"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
