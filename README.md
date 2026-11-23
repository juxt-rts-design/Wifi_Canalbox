# 🌐 Portail Captif Hexaro — Système Rogue AP & Démonstration de Sensibilisation

[![Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://www.kernel.org/)
[![Python 3](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Shell-Bash-green.svg)](https://www.gnu.org/software/bash/)
[![Security Awareness](https://img.shields.io/badge/Focus-Cybersecurity%20Awareness-red.svg)](#-éthique--protection-de-la-vie-privée)
[![Privacy by Design](https://img.shields.io/badge/Privacy-No%20Password%20Stored-brightgreen.svg)](#-éthique--protection-de-la-vie-privée)

Le **Portail Captif Hexaro** est une suite d'outils d'audit réseau et de sensibilisation à la cybersécurité. Il permet de déployer instantanément un **point d'accès Wi-Fi (Rogue AP / Evil Twin)** isolé avec un portail captif interactif, un serveur DHCP/DNS menteur, un mécanisme passif d'identification des appareils connectés (*device fingerprinting*), ainsi qu'un tableau de bord d'administration en temps réel.

---

## ⚠️ Éthique & Protection de la Vie Privée

> [!IMPORTANT]
> **Utilisation strictement encadrée :**
> Cet outil est conçu exclusivement à des fins de **sensibilisation, de démonstration pédagogique, d'audit de sécurité autorisé et de recherche**. Son utilisation sur des personnes ou réseaux tiers sans leur accord préalable et explicite est strictement interdite par la loi.

### 🛡️ Privacy by Design (Conception respectueuse de la vie privée)
Contrairement aux outils offensifs d'hameçonnage malveillant :
- **Aucun mot de passe réel n'est intercepté, transféré ou stocké** : le code client JavaScript et le serveur HTTP ne lisent ni n'enregistrent le contenu des champs de mot de passe.
- **Seules des métadonnées de sensibilisation sont mesurées** : longueur du mot de passe saisi, délai de frappe, conformité du format.
- **Schéma de base de données inviolable** : la base SQLite (`portail.db`) ne possède **aucune colonne** dédiée aux secrets ou mots de passe.
- **Droit à l'oubli automatique** : les baux, visites et métadonnées sont automatiquement purgés après une période de rétention paramétrable (30 jours par défaut).

---

## 📑 Sommaire

1. [Fonctionnalités](#-fonctionnalités)
2. [Pages et Thèmes Inclus](#-pages-et-thèmes-inclus)
3. [Architecture Technique](#-architecture-technique)
4. [Prérequis](#-prérequis)
5. [Installation](#-installation)
6. [Commandes & Guide d'Utilisation](#-commandes--guide-dutilisation)
7. [Interface d'Administration](#-interface-dadministration)
8. [Mode Test & Développement Local](#-mode-test--développement-local)
9. [Configuration Avancée](#-configuration-avancée)
10. [Arborescence du Projet](#-arborescence-du-projet)
11. [Dépannage & FAQ](#-dépannage--faq)

---

## ✨ Fonctionnalités

- **Isolation par Namespace Réseau Linux (`ip netns`)** :
  La carte Wi-Fi est déplacée dans un espace réseau virtuel hermétique (`hexaro`). Cela protège la machine hôte et garantit qu'aucun flux parasite n'interfère avec votre propre connexion réseau.
- **Liaison VETH bidirectionnelle** :
  Une paire d'interfaces virtuelles (`hxhost0` ↔ `hxns0`) permet à la machine exécutant le script d'accéder au portail captif et à l'interface d'administration sur `http://10.42.0.1/admin` sans altérer sa passerelle par défaut.
- **Redirection Captive Universelle (DNS & HTTP)** :
  Grâce à `dnsmasq` et `iptables`, toutes les requêtes DNS renvoient l'adresse du portail (`10.42.0.1`), et le trafic HTTP est redirigé vers le serveur web embarqué.
- **Fingerprinting Passif Multi-Critères** :
  - **OS & Modèle** : Analyse combinée du User-Agent, des requêtes DHCP (option Vendor) et de l'écran du navigateur (largeur, hauteur, Device Pixel Ratio).
  - **Détection fine des modèles d'iPhone** : Reconnaissance précise des modèles d'iPhone (du 11 jusqu'aux générations récentes) via la matrice d'écran et la version Safari/iOS.
  - **Constructeur MAC** : Résolution du constructeur via la base officielle IEEE OUI (`/usr/share/ieee-data/oui.csv`) et détection des adresses MAC aléatoires (MAC randomisées).
- **Restauration Propre du Réseau** :
  À l'arrêt (`Ctrl+C` ou commande `--arreter`), le script détruit le namespace, replace la carte Wi-Fi dans le namespace principal, réactive NetworkManager et reconnecte automatiquement votre réseau Wi-Fi d'origine.

---

## 🎨 Pages et Thèmes Inclus

Lors du lancement, vous pouvez choisir parmi 4 pages selon le scénario de sensibilisation :

| N° | Nom | Description | Cas d'usage |
| :---: | :--- | :--- | :--- |
| **1** | **Virus Hexaro** | Écran rouge d'alerte sécurité, alarme sonore (`alarme.wav`), compte à rebours dynamique et faux scan de réseaux Wi-Fi voisins. | Sensibilisation choc aux risques des réseaux Wi-Fi publics ouverts. |
| **2** | **Wifi (CanalBox)** | Réplique soignée d'un portail captif d'assistance opérateur (CanalBox Gabon). | Démonstration des risques liés aux faux points d'accès opérateurs (Evil Twin). |
| **3** | **Airtel** | Portail captif aux couleurs d'Airtel Gabon (thème rouge & blanc). | Sensibilisation sur les accès mobiles / hotspots 4G/5G. |
| **4** | **Moov Africa** | Portail captif aux couleurs de Moov Africa Gabon Telecom (thème bleu & orange). | Démonstration sur les accès d'entreprise et opérateurs télécoms. |

---

## 🏗️ Architecture Technique

```
                              ┌──────────────────────────────────────────────────────────────┐
                              │                   NAMESPACE VIRTUEL "hexaro"                 │
                              │                                                              │
[Appareil Client Wi-Fi]       │  ┌───────────────┐     ┌──────────────┐     ┌─────────────┐  │
          │                   │  │    hostapd    │     │   dnsmasq    │     │  iptables   │  │
          ├─(Connexion Wi-Fi)─┼─►│ (Point d'Accès│◄───►│ (DHCP + DNS  │◄───►│(Redirection│  │
          │                   │  │  802.11 / AP) │     │  Menteur)    │     │  Port 80)   │  │
          │                   │  └───────────────┘     └──────┬───────┘     └──────┬──────┘  │
          │                   │                               │                    │         │
          │                   │                               │ DHCP Leases        │ HTTP    │
          │                   │                               ▼                    ▼         │
          │                   │                      ┌─────────────────┐  ┌───────────────┐  │
          │                   │                      │  connexion.py   │  │  serveur.py   │  │
          │                   │                      │ (Hook Baux DHCP)│  │ (Serveur Web) │  │
          │                   │                      └────────┬────────┘  └───────┬───────┘  │
          │                   │                               │                   │          │
          │                   │                               ▼                   ▼          │
          │                   │                   ┌────────────────────────────────────────┐ │
          │                   │                   │        journal.py & bdd.py             │ │
          │                   │                   │    (Fingerprinting & SQLite DB)        │ │
          │                   │                   └────────────────────────────────────────┘ │
          │                   │                                        ▲                     │
          │                   │                                        │ VETH (10.99.0.2)    │
          │                   └────────────────────────────────────────┼─────────────────────┘
          │                                                            │
          │                                                    [Lien hxhost0 / hxns0]
          │                                                            │
[Machine Hôte (Admin)] ────────────────────────────────────────────────┴─► http://10.42.0.1/admin
```

---

## 📦 Prérequis

### Matériel
- Une carte réseau Wi-Fi supportant le **mode Master / Point d'Accès (AP)** avec pilote Linux `nl80211`.
  *Pour vérifier la compatibilité de votre carte :*
  ```bash
  iw list | grep -A 10 "Supported interface modes"
  ```
  *(La mention `AP` doit apparaître dans la liste).*

### Logiciels & Outils Système
Le script s'appuie sur des utilitaires Linux standards :
- `bash` (version 4+)
- `python3` (3.8 ou supérieur, bibliothèque standard uniquement)
- `hostapd` (gestion du point d'accès 802.11)
- `dnsmasq` (serveur DHCP et redirection DNS)
- `iptables` (pare-feu et translation de ports)
- `iproute2` (`ip`)
- `iw` (configuration sans-fil)
- `network-manager` (`nmcli`)
- `wpa_supplicant` (`wpa_passphrase`)
- `rfkill`
- `ieee-data` *(recommandé pour résoudre le nom des fabricants de cartes réseau)*

---

## 🚀 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-compte/Nasa_Student.git
cd Nasa_Student
```

### 2. Installer les dépendances système

#### Sur Debian / Ubuntu / Kali Linux / Parrot OS :
```bash
sudo apt update
sudo apt install -y hostapd dnsmasq python3 iptables iproute2 iw network-manager wpasupplicant rfkill ieee-data
```

#### Sur Arch Linux / Manjaro :
```bash
sudo pacman -S hostapd dnsmasq python iptables iproute2 iw networkmanager wpa_supplicant rfkill
```

#### Sur Fedora / RHEL :
```bash
sudo dnf install -y hostapd dnsmasq python3 iptables iproute iw NetworkManager wpa_supplicant rfkill
```

### 3. Rendre les scripts exécutables
```bash
chmod +x lancer-portail.sh portail/connexion.py portail/serveur.py
```

---

## 💻 Commandes & Guide d'Utilisation

### 1. Démarrer le portail (Mode Interactif)
Lancez simplement le script avec les privilèges `root` :
```bash
sudo ./lancer-portail.sh
```

Le script vous guidera pas-à-pas :
1. **Nom du Wi-Fi (SSID)** : Saisissez le nom du réseau diffusé (ex: `Wifi_Gratuit`, `CanalBox_Invite`, etc.).
2. **Mot de passe** :
   - Laissez **vide** (Entrée directe) pour un **réseau ouvert** *(recommandé : les téléphones ouvrent automatiquement le portail captif)*.
   - Ou tapez un mot de passe (8 à 63 caractères) pour un réseau WPA2 sécurisé.
3. **Canal Wi-Fi** : Tapez un canal de 1 à 13 (par défaut : canal `6`).
4. **Choix de la page** :
   - `1` : Virus Hexaro
   - `2` : Wifi (CanalBox)
   - `3` : Airtel
   - `4` : Moov Africa

Dès le lancement, les connexions et appareils détectés s'affichent en temps réel dans votre terminal.

---

### 2. Forcer la reconfiguration
Pour modifier le mot de passe ou l'interface réseau mémorisée dans `portail.conf` :
```bash
sudo ./lancer-portail.sh --configurer
```

---

### 3. Arrêter proprement le portail
- **Méthode normale** : Pressez `Ctrl + C` dans le terminal où tourne le script.
- **Méthode de secours / arrêt explicite** (en cas de plantage ou redémarrage du terminal) :
  ```bash
  sudo ./lancer-portail.sh --arreter
  ```
  *Cette commande supprime le namespace `hexaro`, libère la carte réseau et rétablit automatiquement votre Wi-Fi habituel.*

---

## 📊 Interface d'Administration

Lorsque les pages **Wifi (CanalBox)**, **Airtel** ou **Moov Africa** sont sélectionnées, une interface d'administration temps réel est accessible.

- **URL d'accès** : [`http://10.42.0.1/admin`](http://10.42.0.1/admin)
- **Clé d'administration par défaut** : `1492`
- **Accès direct pré-authentifié** : [`http://10.42.0.1/admin?cle=1492`](http://10.42.0.1/admin?cle=1492)

### Fonctionnalités du tableau de bord :
- **Appareils actifs** : Adresse IP, MAC, Fabricant (Apple, Samsung, etc.), Type de MAC (réelle ou privée/randomisée), Système d'exploitation, Modèle exact, Première et dernière détection.
- **Statistiques des sessions** : Nombre total d'appareils, nombre de pages visitées, nombre de formulaires testés.
- **Métadonnées des essais** : Longueur du mot de passe testé, vitesse de frappe en secondes, motif de validation.
- **Journal d'activité en continu** : Flux des connexions et requêtes sans rechargement de page.
- **Sécurité de l'admin** : Session chiffrée par cookie HttpOnly, comparaison en temps constant (`hmac.compare_digest`), et blocage temporaire (90 secondes) après 5 échecs consécutifs.

---

## 🧪 Mode Test & Développement Local

Il est possible de tester le serveur web, les pages HTML et l'interface d'administration en local sur votre ordinateur, **sans carte Wi-Fi, sans droits root et sans perturber votre réseau** :

```bash
HEXARO_PAGE=wifi HEXARO_CLE=1492 PORTAIL_PORT=8080 python3 portail/serveur.py
```

Ouvrez ensuite votre navigateur sur :
- **Page du portail** : [http://localhost:8080/](http://localhost:8080/)
- **Dashboard Admin** : [http://localhost:8080/admin?cle=1492](http://localhost:8080/admin?cle=1492)

*Remplacez `HEXARO_PAGE=wifi` par `virus`, `airtel` ou `moov` pour prévisualiser les autres thèmes.*

---

## ⚙️ Configuration Avancée

### Variables d'environnement supportées

| Variable | Description | Valeur par défaut |
| :--- | :--- | :--- |
| `PORTAIL_PORT` | Port d'écoute du serveur web | `80` (ou `8080` en local) |
| `HEXARO_PAGE` | Page servie (`virus`, `wifi`, `airtel`, `moov`) | `virus` |
| `HEXARO_CLE` | Clé d'accès à l'interface `/admin` | `1492` |
| `HEXARO_SSID` | Nom du point d'accès diffusé | Variable selon le prompt |
| `HEXARO_CANAL` | Canal radio Wi-Fi | `6` |
| `HEXARO_BDD` | Chemin du fichier SQLite | `portail/portail.db` |
| `HEXARO_RETENTION`| Rétention des données d'audit (en jours) | `30` |
| `HEXARO_LOG` | Fichier de journalisation textuelle | `/run/hexaro-portail/connexions.log` |
| `HEXARO_ETAT` | Fichier JSON d'état instantané des appareils | `/run/hexaro-portail/appareils.json` |

---

## 📁 Arborescence du Projet

```
.
├── lancer-portail.sh      # Script principal d'orchestration (Bash, root)
├── .gitignore             # Exclusion des logs, bases et caches
├── README.md              # Documentation complète du projet
└── portail/               # Cœur applicatif du portail captif
    ├── serveur.py         # Serveur HTTP multi-threadé (Python stdlib)
    ├── admin.py           # Tableau de bord d'administration et sessions
    ├── bdd.py             # Gestionnaire de base SQLite et purge automatique
    ├── journal.py         # Moteur de fingerprinting (DHCP, User-Agent, OUI)
    ├── connexion.py       # Hook déclenché par dnsmasq à chaque bail DHCP
    ├── index.html         # Page 1 : Virus Hexaro (Alerte, sirène, décompte)
    ├── index-wifi.html    # Page 2 : Wifi (Portail CanalBox Gabon)
    ├── index-airtel.html  # Page 3 : Airtel Gabon
    ├── index-moov.html    # Page 4 : Moov Africa Gabon Telecom
    ├── alarme.wav         # Effet sonore d'alerte pour le thème Virus
    └── *.png              # Logos et icônes des différents portails
```

---

## 🔧 Dépannage & FAQ

#### 1. Le script indique « Outil manquant : hostapd » (ou autre)
Installez l'outil manquant avec votre gestionnaire de paquets :
```bash
sudo apt install hostapd dnsmasq
```

#### 2. Le script indique « wlan0 n'est pas une carte Wi-Fi » ou interface introuvable
Vérifiez le nom de votre interface sans-fil avec `iw dev` ou `ip link`. Si besoin, supprimez le fichier de configuration temporaire :
```bash
rm -f portail.conf
sudo ./lancer-portail.sh --configurer
```

#### 3. Le point d'accès n'émet pas ou échoue au démarrage
- Vérifiez si le Wi-Fi n'est pas bloqué matériellement ou logiciellement :
  ```bash
  sudo rfkill unblock wifi
  ```
- Vérifiez si un autre processus n'utilise pas la carte :
  ```bash
  sudo ./lancer-portail.sh --arreter
  sudo systemctl stop hostapd
  sudo systemctl stop dnsmasq
  ```

#### 4. Le smartphone est connecté mais n'affiche pas la page automatiquement
Certains smartphones requièrent un réseau **ouvert** (sans mot de passe) pour déclencher la détection immédiate de portail captif (CNA - *Captive Network Assistant*).
Si le navigateur ne s'ouvre pas automatiquement :
- Ouvrez le navigateur du smartphone et naviguez vers n'importe quelle adresse non chiffrée (ex: `http://neverssl.com` ou directement `http://10.42.0.1`).
- Le serveur interceptera la requête HTTP et affichera la page choisie.

#### 5. Les constructeurs MAC affichent « Inconnu »
Installez la base officielle IEEE OUI sous Linux :
```bash
sudo apt install ieee-data
```

---

## ⚖️ Licence

Projet distribué sous licence MIT. Libre d'utilisation dans le cadre de formations, cours, audits et ateliers de sensibilisation à la cybersécurité.