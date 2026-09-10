# ACMÉ — Notre avenir

Page de présentation, pour le client, de ce que le cabinet change : la plateforme
VERBATIM (démonstration Concept NORD), la pré-clinique menée par un bot, des livrables
plus interactifs (le récit au défilement, les champs sémantiques), le terrain des
créateurs, le showroom confronté au marché, l'offre Décision rapide, et les garanties
« notre logiciel, nos serveurs ».

Partagé **par lien, non indexé** (`robots.txt` en `Disallow: /`, `noindex` sur toutes
les pages). Tout ce qui porte du texte est **chiffré** ; les images servies en clair sont
anonymisées (marques, modèles, véhicules concurrents floutés).

## Quatre versions, deux codes

| Adresse | Public | Langue | Code |
|---|---|---|---|
| `/` | le client principal | français | principal |
| `/en/` | le client principal | anglais | principal |
| `/partenaires/` | les autres partenaires | français | partenaires |
| `/partenaires/en/` | les autres partenaires | anglais | partenaires |

La version « partenaires » montre plus d'écrans (sliders plus fournis, le showroom en
écrans floutés) mais n'ouvre ni le corpus (démonstration, champs sémantiques : en
rendez-vous), ni la page du client, ni l'espace réservé. Son code n'ouvre que sa page, la
proposition et Décision rapide. `build.py` le vérifie à chaque chiffrement : un document
qu'un code ne doit pas ouvrir est refusé s'il l'ouvre.

## Regénérer

```bash
python3 build.py                 # tout, espace réservé compris
python3 build.py --sans-reserve  # sans rechiffrer l'espace réservé
python3 build.py --en-clair      # pages lisibles sans code (contrôle local)
node record.mjs verbatim demo preclinique precliniqueen createurs showroom site siteen   # écrans + vidéos
node record.mjs hubcheck hubcheck_en hubcheck_p hubcheck_pen gatecheck                   # contrôle (non publié)
```

- `contenu.html` (français) et `contenu.en.html` (anglais) portent le texte. Un bloc
  réservé à un public s'écrit `<!--[client]-->…<!--[/client]-->` ou
  `<!--[partenaires]-->…<!--[/partenaires]-->`.
- `build.py` y pose les sliders (table `MEDIAS` : chaque écran dit pour quel public il
  vaut et porte ses deux légendes), les vidéos, les chemins et les chiffres. **Tous les
  écrans d'un slider sont au format 3:2** : une image qui ne l'a pas est complétée avec la
  couleur de son propre bord (`shots/32/`), jamais recadrée.
- `record.mjs` + `scenarios.mjs` rejouent chaque outil dans Chrome sans interface
  (protocole CDP, aucune dépendance), fenêtre 1350 × 900 prise à 2×. Options : `mask`
  (remplacement de texte), `flou` (mots remplacés par des lettres quelconques puis
  floutés), `flouSel` (éléments floutés), `collect` (relevé des textes d'une interface).
- La pré-clinique anglaise est la même séance que la française, traduite à l'écran par
  un masque (`shots/_ctl/poc-en.json`, relevé puis traduit) : le prototype, lui, est en
  français.
- Le prototype de pré-clinique est enregistré depuis une **copie sans séances**, jamais
  depuis le dossier qui contient les vraies séances.
- Les champs sémantiques viennent de `../acme-semantique/` (`extract.py` puis
  `build_page.py`) ; `build.py` relit la page produite et la chiffre.

## Ce qui est chiffré

Format `ACM2` : le contenu est chiffré une fois (AES-256-GCM, clé tirée au hasard), puis
cette clé est enveloppée pour chaque code autorisé (PBKDF2-SHA256, 250 000 itérations).
Chaque `.html` du dossier qui n'est pas un document public n'est qu'une grille d'accès ;
le code saisi reste valable le temps de l'onglet (`sessionStorage`).

| Document | Code principal | Code partenaires |
|---|---|---|
| les pages client (FR, EN) | oui | non |
| les pages partenaires (FR, EN) | non | oui |
| démonstration Concept NORD, champs sémantiques | oui | non |
| proposition (FR, EN), Décision rapide (FR, EN) | oui | oui |
| espace réservé (5 documents) | oui | non |

Les codes vivent dans `CODE-ACCES-NE-PAS-PUBLIER.txt` et
`CODE-PARTENAIRES-NE-PAS-PUBLIER.txt` (ignorés par git). Supprimer un fichier puis
relancer `build.py` en génère un nouveau et rechiffre.

## Ne pas publier

- les deux fichiers de code
- `scenarios.mjs` (ses listes de masquage nomment ce qu'elles protègent) et
  `_mots-sensibles.txt` (la liste que `build.py` cherche dans tout ce qui part)
- `shots/_hub*`, `shots/_ctl/` (captures de contrôle, relevés de textes)
- tout fichier en clair venant de `acme-etude-concurrentielle/`, `acme-ai-interviews/`,
  `acme-semantique/` ou `Small-Van-Histoire-Digitale*.html`
