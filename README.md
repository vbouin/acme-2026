# ACMÉ — Notre avenir

Page de présentation, pour le client, de ce que le cabinet change : la plateforme
VERBATIM (démonstration Concept NORD), la pré-clinique menée par un bot, les livrables
qui se parcourent, le terrain des créateurs, l'offre Décision rapide, et les garanties
« notre logiciel, nos serveurs ». Chaque nouveauté porte un slider d'écrans zoomés et une
mini-vidéo de l'outil, plus un emplacement pour un rendu vidéo IA (`media/ia/`).

Partagé **par lien, non indexé** (`robots.txt` en `Disallow: /`, `noindex` sur toutes
les pages). Les corpus montrés sont anonymisés ; les documents qui nomment un client
sont **chiffrés** dans `reserve/` et ne se lisent qu'avec le code d'accès.

## Regénérer

```bash
python3 build.py                # hub + protocole + espace réservé (rechiffré)
python3 build.py --sans-reserve # sans toucher à l'espace réservé
node record.mjs demo verbatim poc preclinique precliniqueprofil semantique site   # écrans + vidéos
python3 shoot.py etude          # vignette fixe d'un document
```

- `contenu.html` porte le texte du hub ; `build.py` y insère les sliders à partir de
  la table `MEDIAS` (un média absent est ignoré avec un avertissement).
- `record.mjs` + `scenarios.mjs` rejouent chaque outil dans Chrome sans interface
  (protocole CDP, aucune dépendance) et produisent `shots/<nom>.mp4` et `shots/<nom>-NN.jpg`.
  Un curseur dessiné est injecté dans la page ; sur le prototype d'entretien, les noms
  de marque sont masqués au moment de la capture (nœuds de texte uniquement).
- Le prototype de pré-clinique est enregistré depuis une **copie sans séances**
  (`scratchpad/poc-demo`), jamais depuis le dossier qui contient les vraies séances.
- `build.py` relit les sources sensibles à leur emplacement d'origine (étude
  concurrentielle, ADR, Small Van) : elles n'entrent jamais en clair dans ce dossier.
  Sans le module `cryptography`, le script se relance avec le Python de `pseudo-local/.venv`.

## Ce qui est chiffré

Les **données** ne sont jamais servies en clair : la démonstration Concept NORD (le corpus
des 53 entretiens), la proposition détaillée (ses captures et vidéos incorporées) et le détail
de Décision rapide (les écrans du configurateur + le lien vers l'outil) sont relus à leur
source par `build.py`, neutralisés, puis chiffrés en `demo/verbatim-nord.bin`,
`proposition/index.bin` et `decision/index.bin`. Les pages `.html` du même nom ne contiennent
que la grille d'accès. Même code que l'espace réservé, saisi une seule fois par onglet.

La page « Notre avenir » reste lisible. Pour la chiffrer aussi :

```bash
python3 build.py --tout-chiffre    # index.html devient une grille, le contenu part en index.bin
python3 build.py --en-clair        # retour à une page lisible
```

## Espace réservé

Cinq documents désormais (étude concurrentielle, recommandations, ADR, Small Van, Showroom Intelligence). Un fichier `.bin` par document : `salt (16) | iv (12) | AES-256-GCM`. Clé dérivée du
code par PBKDF2-SHA256, 250 000 itérations. La page `reserve/<doc>.html` ne contient
que la grille d'accès ; une fois le code saisi, il reste valable pour les quatre
documents le temps de l'onglet (`sessionStorage`).

Le code vit dans `CODE-ACCES-NE-PAS-PUBLIER.txt` (ignoré par git). Le supprimer puis
relancer `build.py` en génère un nouveau et rechiffre tout.

## Ne pas publier

- `CODE-ACCES-NE-PAS-PUBLIER.txt`
- `scenarios.mjs` (sa table de masquage nomme ce qu'elle masque) et `_mots-sensibles.txt`
  (la liste que `build.py` cherche dans tout ce qui part : un fichier en alerte ne se publie pas)
- `shots/_hub*` (captures de contrôle du hub)
- tout fichier en clair venant de `acme-etude-concurrentielle/`, `acme-ai-interviews/`
  ou `Small-Van-Histoire-Digitale*.html`
