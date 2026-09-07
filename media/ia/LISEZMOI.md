# Rendus vidéo IA

Déposer ici les rendus (mp4, 16:9, 1080p au plus, sans son utile) sous ces noms :

| Fichier            | Emplacement sur la page                                 |
|--------------------|---------------------------------------------------------|
| `hero.mp4`         | fond du titre « Ce que nous changeons »                 |
| `verbatim.mp4`     | bande pleine largeur, section VERBATIM                  |
| `preclinique.mp4`  | bande pleine largeur, section pré-clinique              |
| `livrables.mp4`    | bande pleine largeur, section livrables                 |
| `createurs.mp4`    | bande pleine largeur, section créateurs                 |
| `decision.mp4`     | bande pleine largeur, section Décision rapide           |
| `serveurs.mp4`     | bande pleine largeur, section « notre logiciel »        |

Puis `python3 build.py --sans-reserve`. Le script recompresse chaque rendu une fois
(960 px, sans piste audio, cache dans `_c/`), extrait l'affiche, et l'insère à la place
du rendu provisoire. Un emplacement sans fichier ni rendu provisoire n'affiche rien.
