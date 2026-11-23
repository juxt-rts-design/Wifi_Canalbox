# Portail captif

Je m'appelle Hexaro, et je vous présente ce logiciel que j'ai créé.

Il ouvre un réseau sans fil à part. Le téléphone arrive sur une page, et l'ordinateur montre qui est branché. Les pages reprennent les couleurs de maisons connues au Gabon : CanalBox, Airtel, Moov Africa.

On l'utilise sur ses propres appareils, ou avec des gens qui ont dit oui. Le réseau d'un voisin, d'un client ou d'une école, sans cet accord, ce n'est pas l'usage de ce logiciel.

---

## Les noms utilisés

Quelques noms reviennent dans les fichiers et à l'écran.

- L'espace fermé où vit le réseau s'appelle **hexaro**.
- Le lien entre l'ordinateur et cet espace s'appelle **hxhost0** d'un côté et **hxns0** de l'autre.
- L'adresse de la page, c'est **10.42.0.1**.
- Le tableau de suivi s'ouvre avec une clé. Pour les essais, c'est **1492**.
- Les trois pages s'appellent **CanalBox**, **Airtel** et **Moov Africa**. Ce sont des habillages, pas les vrais services de ces maisons.

---

## À quoi ça sert, pour de vrai

L’utilisateur — toi, ou la personne à qui tu montres l’outil — récupère trois choses, pas plus.

1. **Un réseau à lui.** Un nom de réseau, un canal, avec ou sans mot de passe. Ce réseau ne se mélange pas à la connexion habituelle de l’ordinateur.
2. **Une page d’entreprise, au choix.** Trois habillages :
   - **CanalBox** — la page d’accueil façon box, pour ceux qui ont l’habitude de ce portail à la maison.
   - **Airtel** — rouge et blanc, le visage qu’on voit sur le mobile.
   - **Moov Africa** — bleu et orange, la maison Moov Africa Gabon Télécom.
3. **Un tableau.** Dès qu’un téléphone se branche, tu vois son adresse, la marque de la carte, le modèle quand on peut le deviner, et l’heure. Tu suis ça sans recharger la page.

Tu ne « récupères » pas le compte d’un client. Tu récupères **tes** outils : le réseau, la page choisie, le tableau. L’entreprise affichée, c’est un habit. CanalBox, Airtel ou Moov : tu en prends une, tu laisses les autres.

---

## Un utilisateur concret

Un utilisateur est à la maison, avec son ordinateur et son téléphone. Il veut voir si la page CanalBox s’ouvre, et si le tableau reconnaît son appareil.

1. Il ouvre un terminal dans le dossier du projet.
2. Il lance le logiciel avec les droits d’administration.
3. Il donne au réseau un nom simple, par exemple `Essai`. Il ne prend pas le nom d’une vraie box du quartier.
4. Il laisse le mot de passe vide, pour que le téléphone ouvre la page tout seul. Il peut aussi en mettre un, entre 8 et 63 signes.
5. Le canal, il laisse **6**, ou il en choisit un autre entre 1 et 13.
6. Pour la page, il prend **CanalBox**. Dans le menu, c’est le choix **2**. Airtel, c’est **3**. Moov Africa, c’est **4**.
7. Il connecte son téléphone au réseau `Essai`. La page CanalBox s’affiche.
8. Sur l’ordinateur, il ouvre `http://10.42.0.1/admin` et il tape la clé **1492**. Son téléphone apparaît : la marque, l’heure.
9. Il a fini. Il appuie sur `Ctrl + C`. Son réseau habituel revient tout seul.

Le même chemin marche si une autre personne est à côté et qu’elle a dit oui. Elle branche son téléphone, on le voit sur le tableau, on arrête. Personne d’autre.

Pour Airtel ou Moov à la place de CanalBox, seul le choix de la page change.

---

## Comment c’est bâti

Tout le réseau vit dans une pièce à part, pour ne pas toucher ta connexion du quotidien. Le téléphone parle au point d’accès. Le point d’accès parle au programme qui distribue les adresses. Ce programme prévient un petit script à chaque nouveau téléphone. Le filtre ramène les pages vers le serveur. Le serveur montre la page choisie et écrit le suivi. Ton ordinateur, lui, passe par un fil interne pour ouvrir le tableau.

```
                         Pièce fermée « hexaro »
                         (le réseau ne sort pas d'ici)

  Ton téléphone
       |
       |  il se branche au réseau
       v
  +----------------+     +------------------+     +------------------+
  | Point d'accès  | --> | Adresses et noms | --> | Filtre des pages |
  | (hostapd)      |     | (dnsmasq)        |     | (iptables)       |
  +----------------+     +--------+---------+     +--------+---------+
                                  |                        |
                                  | nouveau téléphone      | la page demandée
                                  v                        v
                         +----------------+       +------------------+
                         | connexion.py   |       | serveur.py       |
                         | note le bail   |       | montre la page   |
                         +-------+--------+       +--------+---------+
                                 |                         |
                                 v                         v
                         +------------------------------------------+
                         | journal.py et bdd.py                     |
                         | reconnaît l'appareil, garde la trace     |
                         +--------------------+---------------------+
                                              |
                                              | fil interne
                                              | hxhost0  <--->  hxns0
                                              v
                         Ton ordinateur
                         tableau : http://10.42.0.1/admin
```

Les noms entre parenthèses sont les programmes à installer. Dans le texte, on dit plutôt : point d’accès, distribution des adresses, filtre, serveur, journal, base.

### Ce que chaque pièce fait

- **Point d’accès.** Il ouvre le réseau sans fil. Sans une carte qui sait jouer ce rôle, rien ne part.
- **Adresses et noms.** Chaque téléphone reçoit une adresse. Quand il demande un site, on lui répond l’adresse du portail, pour que la page d’accueil s’ouvre.
- **Filtre.** Il ramène le trafic des pages vers le serveur.
- **connexion.py.** À chaque nouveau téléphone, il note le bail.
- **serveur.py.** Il montre la page CanalBox, Airtel ou Moov, et il sert le tableau.
- **journal.py.** Il devine la marque et le modèle à partir de ce que le téléphone dit de lui-même : navigateur, taille de l’écran, demande d’adresse, adresse physique de la carte.
- **bdd.py.** Il range ça dans un fichier local, et il efface les vieilles lignes au bout d’un mois, sauf si tu changes ce délai.
- **Le fil interne.** Grâce à lui, ton ordinateur ouvre le tableau sans quitter sa connexion habituelle.

À l’arrêt, la pièce fermée est détruite, la carte sans fil revient à sa place, et ton réseau d’avant se reconnecte.

---

## Ce qu’il te faut

### Le matériel

Une carte sans fil qui sait **ouvrir un réseau**, pas seulement s’y connecter. Pour vérifier :

```bash
iw list | grep -A 10 "Supported interface modes"
```

Tu dois voir la mention `AP` dans la liste.

### Les programmes

- `bash` (version 4 ou plus)
- `python3` (3.8 ou plus, rien à ajouter en plus de Python)
- `hostapd` — ouvre le réseau
- `dnsmasq` — donne les adresses et répond aux noms
- `iptables` — filtre et ramène les pages
- `iproute2` — la commande `ip`
- `iw` — règle la carte
- `network-manager` — la commande `nmcli`
- `wpa_supplicant` — prépare un réseau avec mot de passe
- `rfkill` — débloque la carte si elle est coupée
- `ieee-data` — pour afficher la marque à partir de l’adresse de la carte

---

## Installation

Place-toi dans le dossier du projet, puis installe les programmes.

Sur Debian, Ubuntu ou Kali :

```bash
sudo apt update
sudo apt install -y hostapd dnsmasq python3 iptables iproute2 iw network-manager wpasupplicant rfkill ieee-data
```

Sur Arch ou Manjaro :

```bash
sudo pacman -S hostapd dnsmasq python iptables iproute2 iw networkmanager wpa_supplicant rfkill
```

Sur Fedora :

```bash
sudo dnf install -y hostapd dnsmasq python3 iptables iproute iw NetworkManager wpa_supplicant rfkill
```

Rends les scripts lançables :

```bash
chmod +x lancer-portail.sh portail/connexion.py portail/serveur.py
```

---

## S’en servir

### Lancer

```bash
sudo ./lancer-portail.sh
```

Le script te pose les questions une par une.

1. **Nom du réseau.** Un nom simple, comme `Essai`.
2. **Mot de passe.** Entrée directe : réseau ouvert, le téléphone montre la page plus vite. Sinon, 8 à 63 signes.
3. **Canal.** De 1 à 13. Entrée : canal 6.
4. **Page.**
   - `2` : CanalBox
   - `3` : Airtel
   - `4` : Moov Africa

Les téléphones qui se branchent s’affichent dans le terminal au fur et à mesure.

### Changer un réglage déjà gardé

Le nom de la carte et le mot de passe restent dans `portail.conf`. Pour les revoir :

```bash
sudo ./lancer-portail.sh --configurer
```

### Arrêter

Dans le terminal qui tourne : `Ctrl + C`.

Si le terminal a été fermé trop vite :

```bash
sudo ./lancer-portail.sh --arreter
```

Ça enlève la pièce `hexaro`, rend la carte, et ramène ton réseau habituel.

---

## Le tableau

Il est là pour les pages **CanalBox**, **Airtel** et **Moov Africa**.

- Adresse : `http://10.42.0.1/admin`
- Clé d’essai : `1492`
- Entrée déjà ouverte : `http://10.42.0.1/admin?cle=1492`

Tu y vois :

- les téléphones encore là : adresse, adresse de la carte, marque, adresse réelle ou changée par le téléphone, système, modèle, première et dernière fois
- les comptes : combien d’appareils, combien de pages vues, combien de formulaires essayés
- sur un essai de formulaire : la **longueur** de ce qui a été tapé, le temps de frappe, et si le format était bon — **pas le mot de passe lui-même**
- le fil des événements, sans recharger

La clé du tableau est vérifiée sans donner d’indice, la session reste dans un jeton que la page ne peut pas lire, et après cinq mauvaises clés l’accès se ferme pendant 90 secondes.

Le mot de passe saisi sur la page d’accueil **n’est pas lu, pas envoyé, pas gardé**. La base n’a aucune colonne pour ça.

---

## Essayer sans carte sans fil

Tu peux regarder les pages et le tableau sur l’ordinateur seul, sans droits d’administration et sans toucher au réseau de la maison.

CanalBox :

```bash
HEXARO_PAGE=wifi HEXARO_CLE=1492 PORTAIL_PORT=8080 python3 portail/serveur.py
```

Airtel : remplace `wifi` par `airtel`.  
Moov Africa : remplace `wifi` par `moov`.

Puis ouvre :

- la page : `http://localhost:8080/`
- le tableau : `http://localhost:8080/admin?cle=1492`

---

## Réglages, si tu veux aller plus loin

| Réglage | Rôle | Valeur si tu ne touches à rien |
| :--- | :--- | :--- |
| `PORTAIL_PORT` | Numéro où le serveur écoute | `80`, ou `8080` en essai local |
| `HEXARO_PAGE` | Page montrée : `wifi`, `airtel` ou `moov` | selon ton choix au lancement |
| `HEXARO_CLE` | Clé du tableau | `1492` |
| `HEXARO_SSID` | Nom du réseau | ce que tu as tapé |
| `HEXARO_CANAL` | Canal | `6` |
| `HEXARO_BDD` | Fichier de la base | `portail/portail.db` |
| `HEXARO_RETENTION` | Jours avant l’effacement | `30` |
| `HEXARO_LOG` | Journal en texte | `/run/hexaro-portail/connexions.log` |
| `HEXARO_ETAT` | Photo des appareils, en direct | `/run/hexaro-portail/appareils.json` |

---

## Les fichiers

```
.
├── lancer-portail.sh       # lance, arrête et range le réseau
├── README.md               # ce texte
└── portail/
    ├── serveur.py          # les pages et le tableau
    ├── admin.py            # l'écran du tableau et la clé
    ├── bdd.py              # la base, et l'effacement au bout d'un mois
    ├── journal.py          # la reconnaissance du téléphone
    ├── connexion.py        # noté à chaque nouveau bail
    ├── index-wifi.html     # page CanalBox
    ├── index-airtel.html   # page Airtel
    ├── index-moov.html     # page Moov Africa
    └── *.png               # logos et images des pages
```

---

## Quand ça coince

**Il manque un programme** (`hostapd` ou un autre). Installe-le, par exemple :

```bash
sudo apt install hostapd dnsmasq
```

**La carte n’est pas reconnue.** Regarde son nom avec `iw dev` ou `ip link`, puis :

```bash
rm -f portail.conf
sudo ./lancer-portail.sh --configurer
```

**Le réseau ne s’allume pas.** Débloque la carte, puis coupe les anciens programmes qui la tiennent :

```bash
sudo rfkill unblock wifi
sudo ./lancer-portail.sh --arreter
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
```

**Le téléphone est connecté, la page ne s’ouvre pas.** Un réseau **sans mot de passe** aide le téléphone à montrer la page tout seul. Sinon, ouvre le navigateur et va sur `http://10.42.0.1`.

**La marque reste « Inconnu ».**

```bash
sudo apt install ieee-data
```

---

## Licence

Licence MIT. Tu peux t’en servir, le modifier, le montrer en cours, tant que tu restes sur tes appareils ou avec l’accord des gens concernés.
