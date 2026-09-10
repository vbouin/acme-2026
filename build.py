#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemble le dossier « ACMÉ 2026 » — la page « Notre avenir » et tout ce
qu'elle ouvre, pour partage par lien (public, non indexé).

    python3 build.py                 # tout
    python3 build.py --sans-reserve  # sans rechiffrer l'espace réservé
    python3 build.py --en-clair      # pages lisibles sans code (défaut : chiffrées)

Quatre versions de la page, deux textes sources (un par langue) :

    /                  le client principal, en français     code principal
    /en/               le client principal, en anglais      code principal
    /partenaires/      les autres partenaires, en français  code partenaires
    /partenaires/en/   les autres partenaires, en anglais   code partenaires

`contenu.html` et `contenu.en.html` portent le texte ; un bloc réservé à un
public s'écrit <!--[client]-->…<!--[/client]--> ou
<!--[partenaires]-->…<!--[/partenaires]-->. Les sliders ({{slider:…}}) viennent
de la table MEDIAS : chaque écran dit pour quel public il vaut et porte ses deux
légendes. Tous les écrans d'un slider ont le même format (3:2) : une image qui
ne l'a pas est complétée avec la couleur de son propre bord, jamais recadrée.

Les codes : la version « partenaires » a son propre code. Il n'ouvre que ce qui
a été chiffré pour elle — sa page, et les documents de démonstration partagés.
Il n'ouvre ni la page du client principal ni l'espace réservé. Les deux codes
vivent dans des fichiers ignorés par git et ne sont jamais imprimés.
"""
from __future__ import annotations
import html as _html
import json, os, re, secrets, subprocess, sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
CLAUDE = ICI.parent
sys.path.insert(0, str(ICI))
from md import rendre  # noqa: E402

SOURCES = {
    "protocole": CLAUDE / "acme-ai-interviews" / "PROTOCOLE-ENTRETIEN.md",
    "protocole_en": CLAUDE / "acme-ai-interviews" / "PROTOCOL-INTERVIEW-EN.md",
    "recommandations": CLAUDE / "acme-etude-concurrentielle" / "RECOMMANDATIONS.md",
    "etude": CLAUDE / "acme-etude-concurrentielle" / "etude-concurrentielle.html",
    "adr": CLAUDE / "acme-ai-interviews" / "etude-technique.html",
    "smallvan": CLAUDE / "Small-Van-Histoire-Digitale-PARTAGE.html",
    # les données : relues à leur source, jamais copiées en clair dans ce dossier
    "demo": CLAUDE / "plateforme-qual" / "app" / "exports" / "ACME_VERBATIM_demo_NORD_compresse.html",
    "proposition": CLAUDE / "acme-propale-verbatim" / "proposition.html",
    "proposition_en": CLAUDE / "acme-propale-verbatim" / "proposition.en.html",
    "semantique": CLAUDE / "acme-semantique" / "champs-semantiques.html",
    "bbr": CLAUDE / "bbr-intel" / "bbr-showroom-intelligence.html",
}
CODES = {"principal": ICI / "CODE-ACCES-NE-PAS-PUBLIER.txt",
         "partenaires": ICI / "CODE-PARTENAIRES-NE-PAS-PUBLIER.txt"}
VENV_PY = CLAUDE / "pseudo-local" / ".venv" / "bin" / "python3"
ITERATIONS = 250_000
DATE = {"fr": "10 septembre 2026", "en": "10 September 2026"}

VERSIONS = [
    {"cle": "client-fr", "dossier": "", "lang": "fr", "public": "client", "code": "principal"},
    {"cle": "client-en", "dossier": "en", "lang": "en", "public": "client", "code": "principal"},
    {"cle": "partenaires-fr", "dossier": "partenaires", "lang": "fr", "public": "partenaires", "code": "partenaires"},
    {"cle": "partenaires-en", "dossier": "partenaires/en", "lang": "en", "public": "partenaires", "code": "partenaires"},
]
TITRES = {"fr": "ACMÉ — Notre avenir", "en": "ACMÉ — Our future"}


# ---------------------------------------------------------------- médias
def M(src: str, fr: str, en: str, pour: str | None = None, src_en: str | None = None) -> dict:
    """Un écran de slider. `pour` : None = toutes les versions, sinon 'client'
    ou 'partenaires'. `src_en` : l'écran à montrer dans les versions anglaises."""
    return {"src": src, "fr": fr, "en": en, "pour": pour, "src_en": src_en}


P = "partenaires"
MEDIAS = {
    "verbatim": [
        M("shots/demo.mp4", "Le tour de la plateforme : carte du véhicule, atelier, typologies, pays, entretien.",
          "A tour of the platform: vehicle map, quote workshop, typologies, countries, interview."),
        M("shots/vb-02-carte.jpg", "La carte du véhicule : chaque pastille est une zone commentée, la taille dit le volume, la couleur la polarité.",
          "The vehicle map: each dot is a zone people talked about; size shows volume, colour shows polarity."),
        M("shots/vb-03-zone.jpg", "Un clic sur une zone ouvre les verbatims qui en parlent, avec leur profil et leur polarité.",
          "Click a zone to open the quotes about it, with each speaker's profile and polarity."),
        M("shots/vb-04-atelier.jpg", "L'atelier : un mot-clé, croisé avec la question du guide et le point de monographie. Chaque bloc se copie tel quel.",
          "The workshop: a keyword crossed with the guide question and the monograph point. Every block copies as is."),
        M("shots/vb-05-entretien.jpg", "Le verbatim remis dans sa conversation : la question posée juste avant, la relance qui a suivi, l'entretien complet.",
          "The quote back in its conversation: the question asked just before, the probe that followed, the full interview."),
        M("shots/vb-08-profils.jpg", "Les profils, anonymes ou pseudonymes, au choix, sans changer de fichier.",
          "Profiles, anonymous or pseudonymised, switched in the same file."),
        M("shots/vb-06-pays.jpg", "France et Allemagne, lues côte à côte.", "France and Germany, read side by side."),
        M("shots/vb-07-typologies.jpg", "Les typologies calculées sur le corpus.", "Typologies computed on the corpus."),
        M("shots/vb-10-analyses.jpg", "Les analyses croisées : milieu × issue, trajectoire des classements, thème × polarité.",
          "Cross-analyses: milieu × outcome, ranking trajectories, theme × polarity.", pour=P),
        M("shots/vb-11-guide.jpg", "Le guide d'entretien, section par section, relié aux verbatims qu'il a produits.",
          "The interview guide, section by section, linked to the quotes it produced.", pour=P),
        M("shots/vb-09-champs.jpg", "Toutes les citations par sujet, rangées par polarité.",
          "Every quote by topic, sorted by polarity."),
        M("shots/vb-01-vue.jpg", "La vue d'ensemble : 53 entretiens, 2 027 verbatims ancrés, fidélité vérifiée mot à mot.",
          "The overview: 53 interviews, 2,027 anchored quotes, word-for-word fidelity checked."),
    ],
    "preclinique": [
        M("shots/poc.mp4", "Un pré-entretien joué de bout en bout, par écrit, jusqu'au suivi de terrain.",
          "A pre-interview played end to end, in writing, down to the fieldwork tracker.", src_en="shots/en/poc.mp4"),
        M("shots/pc-01-accueil.jpg", "L'accueil : le participant sait qu'il parle à une IA, et consent explicitement.",
          "The welcome: participants know they are talking to an AI, and consent explicitly.", src_en="shots/en/pc-01-accueil.jpg"),
        M("shots/pc-02-programme.jpg", "Le programme annoncé : les séquences, leur durée, ce qui sera demandé.",
          "The programme announced up front: sequences, timing, what will be asked.", pour=P, src_en="shots/en/pc-02-programme.jpg"),
        M("shots/pc-04-question.jpg", "La question du guide, prononcée mot pour mot. L'onde suit la voix.",
          "The guide's question, spoken word for word. The waveform follows the voice.", src_en="shots/en/pc-04-question.jpg"),
        M("shots/pc-05-echange.jpg", "La réponse, puis la relance : elle vient du répertoire fermé du guide.",
          "The answer, then the probe: it comes from the guide's closed repertoire.", src_en="shots/en/pc-05-echange.jpg"),
        M("shots/pc-07-fiche.jpg", "La fiche de qualification se remplit sous les yeux du chercheur, avec la citation qui fonde chaque valeur.",
          "The screening sheet fills in as the researcher watches, with the quote behind every value.", src_en="shots/en/pc-07-fiche.jpg"),
        M("shots/pc-08-sommaire.jpg", "Le sommaire : où en est l'entretien, séquence par séquence.",
          "The outline: where the interview stands, sequence by sequence.", pour=P, src_en="shots/en/pc-08-sommaire.jpg"),
        M("shots/pc-09-revue.jpg", "La revue avant clôture : séquence par séquence, ce qui est couvert, partiel ou non abordé.",
          "The review before closing: covered, partial or not addressed, sequence by sequence.", src_en="shots/en/pc-09-revue.jpg"),
        M("shots/pc-10-cloture.jpg", "Ce qui manque est nommé, jamais tu : le redemander maintenant, ou clore en le disant.",
          "What is missing is named, never hidden: ask again now, or close and say so.", src_en="shots/en/pc-10-cloture.jpg"),
        M("shots/pc-12-terrain.jpg", "Le suivi de terrain : une case par pré-entretien, la répartition des hypothèses de milieu.",
          "The fieldwork tracker: one box per pre-interview, the spread of milieu hypotheses.", src_en="shots/en/pc-12-terrain.jpg"),
        M("shots/pc-13-grille.jpg", "La grille de terrain, colonne par colonne, comme celle de l'institut.",
          "The fieldwork grid, column by column, like the agency's own.", pour=P, src_en="shots/en/pc-13-grille.jpg"),
        M("shots/pc-14-profil.jpg", "Le profil d'une séance en une page : ce que la séance a ramené, valeur par valeur.",
          "One session's profile on one page: what it brought back, value by value.", src_en="shots/en/pc-14-profil.jpg"),
    ],
    "voyage": [
        M("media/smallvan-hero.mp4", "L'ouverture : le véhicule se construit à mesure qu'on descend.",
          "The opening: the vehicle builds itself as you scroll."),
    ],
    "semantique": [
        M("shots/sem.mp4", "Le tour de l'outil : champs, parties du véhicule, véhicules comparés, deux terrains.",
          "A tour of the tool: fields, vehicle parts, vehicles compared, two fieldworks.", src_en="shots/en/sem.mp4"),
        M("shots/sem-01-champs.jpg", "Les champs sémantiques du corpus : chaque champ regroupe des qualificatifs de même sens, compté en entretiens.",
          "The corpus's semantic fields: each groups qualifiers of the same meaning, counted in interviews.", src_en="shots/en/sem-01-champs.jpg"),
        M("shots/sem-02-parties.jpg", "Parties du véhicule × champs : ce qui se dit de la face avant n'est pas ce qui se dit de l'intérieur.",
          "Vehicle parts × fields: what is said about the front is not what is said about the interior.", src_en="shots/en/sem-02-parties.jpg"),
        M("shots/sem-03-mot.jpg", "Un qualificatif ouvre ses phrases, avec l'entretien et la question qui l'ont produit.",
          "A qualifier opens its sentences, with the interview and the question that produced them.", src_en="shots/en/sem-03-mot.jpg"),
        M("shots/sem-04-vehicules.jpg", "Le concept face aux concurrents de la salle : le même vocabulaire, pas les mêmes champs.",
          "The concept against the competitors in the room: same vocabulary, different fields.", src_en="shots/en/sem-04-vehicules.jpg"),
        M("shots/sem-05-terrains.jpg", "Deux types d'entretien, deux véhicules : clinique grand public et exploratoire professionnel.",
          "Two interview types, two vehicles: consumer clinic and professional exploratory.", src_en="shots/en/sem-05-terrains.jpg"),
        M("shots/sem-06-promesse.jpg", "La promesse de l'extérieur, confrontée à l'intérieur : ce qui tient, ce qui se perd.",
          "The exterior's promise against the interior: what holds, what gets lost.", src_en="shots/en/sem-06-promesse.jpg"),
    ],
    "createurs": [
        M("shots/alp.mp4", "Le tour du livrable : le film, l'analyse dimension par dimension, les vidéos et leurs transcriptions.",
          "A tour of the deliverable: the film, the dimension-by-dimension analysis, the videos and their transcripts."),
        M("shots/alp-01-film.jpg", "L'ouverture : le récit d'abord, la gamme comparée, les chiffres du dispositif.",
          "The opening: the story first, the line-up compared, the numbers behind it."),
        M("shots/alp-02-comparaison.jpg", "La colonne vertébrale : l'étude consommateurs à gauche, les créateurs à droite, l'alignement mesuré dimension par dimension.",
          "The spine: consumer research on the left, creators on the right, alignment measured dimension by dimension."),
        M("shots/alp-03-videos.jpg", "Les vidéos, filtrées par marché, modèle, format ; vues et engagement, vérifiés ou estimés, toujours signalés.",
          "The videos, filtered by market, model and format; views and engagement, verified or estimated, always flagged."),
        M("shots/alp-04-transcription.jpg", "Chaque vidéo s'ouvre sur sa transcription, face à ce qu'en dit l'étude interne.",
          "Every video opens on its transcript, facing what the internal study says."),
        M("shots/alp-05-verbatims.jpg", "Les commentaires, captés sur la plateforme, traduits et classés par thème et par tonalité.",
          "Comments captured on the platform, translated and sorted by theme and sentiment."),
        M("shots/alp-06-marche.jpg", "Un nouveau marché, le même procédé : les challengers d'un marché lointain, et le verdict des créateurs.",
          "A new market, the same process: challengers from a distant market, and the creators' verdict.", pour=P),
        M("shots/alp-07-vehicules.jpg", "La synthèse par véhicule, agrégée depuis les vidéos de neuf marchés.",
          "The per-vehicle synthesis, aggregated from videos across nine markets."),
    ],
    "showroom": [
        M("shots/sh-01-synthese.jpg", "La synthèse : chaque concurrent de la salle, entre ce qu'en dit la salle et ce qu'en dit le marché.",
          "The synthesis: each competitor in the room, between what the room says and what the market says.", pour=P),
        M("shots/sh-02-test.jpg", "Le test : les classements lus dans les transcripts, étape par étape.",
          "The test: rankings read in the transcripts, step by step.", pour=P),
        M("shots/sh-03-face.jpg", "Face à face : six dimensions, regard interne et regard externe, alignés ou non.",
          "Face to face: six dimensions, inside and outside views, aligned or not.", pour=P),
        M("shots/sh-04-avis.jpg", "Les avis clients, une dizaine de sources, notes normalisées.",
          "Customer reviews from a dozen sources, ratings normalised.", pour=P),
        M("shots/sh-05-createurs.jpg", "Les vidéos de créateurs, vérifiées une à une sur leur page.",
          "Creator videos, each checked on its own page.", pour=P),
    ],
}

# Emplacements vidéo : un rendu déposé dans media/ia/<nom>.mp4 remplace le rendu
# provisoire. Recompressé une fois (960 px, sans son), affiche extraite.
VIDEOS = {
    "hero":        "media/hero-prov.mp4",      # plateau tournant en aller-retour, sans texte incrusté
    "verbatim":    "media/video-commentaires.mp4",
    "preclinique": None,
    "livrables":   None,
    "createurs":   None,
    "decision":    None,
    "serveurs":    "media/video-donnees.mp4",
}

T = {  # libellés d'interface, par langue
    "fr": {"prec": "Écran précédent", "suiv": "Écran suivant", "ecrans": "Écrans du livrable", "avenir": "Écrans à venir",
           "code": "Code d'accès", "ouvrir": "Déverrouiller", "encours": "Déchiffrement…", "faux": "Code incorrect.",
           "pied": "Le contenu est chiffré dans le fichier servi ; il ne se lit qu'avec le code.", "retour": "Retour à la page",
           "retour_doc": "← Retour"},
    "en": {"prec": "Previous screen", "suiv": "Next screen", "ecrans": "Screens of the deliverable", "avenir": "Screens to come",
           "code": "Access code", "ouvrir": "Unlock", "encours": "Decrypting…", "faux": "Wrong code.",
           "pied": "The content is encrypted in the file served; it can only be read with the code.", "retour": "Back to the page",
           "retour_doc": "← Back"},
}


def esc(s: str) -> str:
    return _html.escape(s, quote=True)


# ---------------------------------------------------------------- polices
def fonts_css() -> None:
    cible = ICI / "assets" / "fonts.css"
    faces = ICI / "assets" / "faces.json"
    if cible.exists() and not faces.exists():
        return
    if not faces.exists():
        print("⚠ ni fonts.css ni faces.json : la page retombera sur les piles système", file=sys.stderr)
        return
    data = json.loads(faces.read_text(encoding="utf-8"))
    css = "\n".join(
        "@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;"
        "src:url(data:font/woff2;base64,%s) format('woff2')}" % (f["famille"], f["graisse"], f["b64"])
        for f in data)
    cible.write_text(css, encoding="utf-8")
    faces.unlink()
    print(f"   ✓ assets/fonts.css ({cible.stat().st_size // 1024} Ko)")


# ---------------------------------------------------------------- gabarits
def tete(titre: str, prefixe: str = "", lang: str = "fr") -> str:
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<title>{esc(titre)}</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="{prefixe}assets/fonts.css">
<link rel="stylesheet" href="{prefixe}assets/hub.css">
</head>
"""


# Un document ouvert depuis une page revient à la page d'où l'on vient (client
# ou partenaires) ; ouvert directement, il revient à `repli`.
RETOUR_JS = "if(document.referrer&&document.referrer.indexOf(location.origin)===0){history.back();return false}"


def page_doc(titre: str, meta: str, corps: str, repli: str = "../index.html", prefixe: str = "../", lang: str = "fr") -> str:
    corps = re.sub(r"<table>(.*?)</table>", r'<div class="table-wrap"><table>\1</table></div>', corps, flags=re.S)
    corps = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", corps, count=1, flags=re.S)
    return tete(titre, prefixe, lang) + f"""<body>
<main class="doc">
<a class="retour" href="{repli}" onclick="{RETOUR_JS}">{esc(T[lang]['retour_doc'])}</a>
<div class="eyebrow">— ACMÉ · 2026</div>
<h1>{esc(titre)}</h1>
<div class="meta">{esc(meta)}</div>
{corps}
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- écrans au format 3:2
def _dims(p: Path) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def _couleur_bord(p: Path, cote: str) -> str:
    """Couleur moyenne d'une bande de 6 px sur un bord de l'image (hex)."""
    crop = {"haut": "iw:6:0:0", "bas": "iw:6:0:ih-6", "gauche": "6:ih:0:0", "droite": "6:ih:iw-6:0"}[cote]
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", f"crop={crop},scale=1:1", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True)
    b = r.stdout[:3] if len(r.stdout) >= 3 else b"\xfa\xfa\xfa"
    return "%02x%02x%02x" % (b[0], b[1], b[2])


def cadre32(rel: str) -> str:
    """Chemin d'une version 3:2 de l'image : l'original s'il a déjà le format,
    sinon une copie complétée sur les bords avec leur propre couleur."""
    p = ICI / rel
    w, h = _dims(p)
    if abs(w / h - 1.5) <= 0.02:
        return rel
    sortie = p.parent / "32" / p.name
    if sortie.exists() and sortie.stat().st_mtime >= p.stat().st_mtime:
        return str(sortie.relative_to(ICI))
    sortie.parent.mkdir(exist_ok=True)
    if w / h > 1.5:   # trop large : on complète en haut et en bas
        W, H = w, round(w / 1.5)
        a, b = _couleur_bord(p, "haut"), _couleur_bord(p, "bas")
    else:             # trop haute : on complète à gauche et à droite
        W, H = round(h * 1.5), h
        a, b = _couleur_bord(p, "gauche"), _couleur_bord(p, "droite")
    moy = "%02x%02x%02x" % tuple((int(a[i:i + 2], 16) + int(b[i:i + 2], 16)) // 2 for i in (0, 2, 4))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vf",
                    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{moy}", "-q:v", "3", str(sortie)], check=False)
    print(f"   · {rel} complété en 3:2 ({w}×{h} → {W}×{H})")
    return str(sortie.relative_to(ICI))


def _affiche(p: Path) -> Path | None:
    jpg = p.with_name(p.stem + "-poster.jpg")
    if not jpg.exists() or jpg.stat().st_mtime < p.stat().st_mtime:
        # à 3 s : le premier instant d'un enregistrement d'interface est souvent une page encore blanche ou noire
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3", "-i", str(p), "-frames:v", "1",
                        "-vf", "scale=1200:-2", "-q:v", "4", str(jpg)], check=False)
    return jpg if jpg.exists() else None


def slider(cle: str, public: str, lang: str, prefixe: str) -> str:
    items = []
    for m in MEDIAS.get(cle, []):
        if m["pour"] and m["pour"] != public:
            continue
        src = m["src_en"] if lang == "en" and m["src_en"] and (ICI / m["src_en"]).exists() else m["src"]
        p = ICI / src
        if not p.exists():
            print(f"   ⚠ média absent ({cle}) : {src}", file=sys.stderr)
            continue
        legende = m[lang]
        if src.endswith(".mp4"):
            aff = _affiche(p)
            poster = f' poster="{prefixe}{esc(str(aff.relative_to(ICI)))}"' if aff else ""
            media = f'<video src="{prefixe}{esc(src)}"{poster} muted loop playsinline preload="metadata"></video>'
        else:
            media = f'<img src="{prefixe}{esc(cadre32(src))}" alt="" loading="lazy">'
        items.append(f'<figure class="slide">{media}<figcaption>{esc(legende)}</figcaption></figure>')
    t = T[lang]
    if not items:
        return f'<div class="cadre cadre--vide"><span class="mono">{t["avenir"]}</span></div>'
    if len(items) == 1:
        return (f'<div class="slider slider--seul" data-slider tabindex="0"><div class="slider-track">{items[0]}</div>'
                '<div class="slider-bar"><button class="slider-btn slider-prev" hidden aria-hidden="true">←</button>'
                '<span class="slider-count mono"></span><button class="slider-btn slider-next" hidden aria-hidden="true">→</button></div></div>')
    return (f'<div class="slider" data-slider tabindex="0" aria-label="{t["ecrans"]}">'
            f'<div class="slider-track">{"".join(items)}</div>'
            f'<div class="slider-bar"><button type="button" class="slider-btn slider-prev" aria-label="{t["prec"]}">←</button>'
            f'<div class="slider-dots"></div><span class="slider-count mono">1 / {len(items)}</span>'
            f'<button type="button" class="slider-btn slider-next" aria-label="{t["suiv"]}">→</button></div></div>')


def video_slot(nom: str, prefixe: str) -> str:
    """Un emplacement vidéo de la page. Le rendu IA déposé dans media/ia/<nom>.mp4
    prime ; sinon le rendu provisoire de VIDEOS ; sinon rien."""
    ia = ICI / "media" / "ia" / f"{nom}.mp4"
    if ia.exists():
        cache = ICI / "media" / "ia" / "_c"
        cache.mkdir(exist_ok=True)
        petit = cache / f"{nom}.mp4"
        if not petit.exists() or petit.stat().st_mtime < ia.stat().st_mtime:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ia), "-vf", "scale=960:-2:flags=lanczos", "-an",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "30", "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", str(petit)], check=False)
            print(f"   ✓ rendu IA {nom} recompressé ({petit.stat().st_size // 1024} Ko)")
        src = petit
    else:
        prov = VIDEOS.get(nom)
        if not prov or not (ICI / prov).exists():
            return ""
        src = ICI / prov
    affiche = src.with_name(src.stem + "-poster.jpg")
    if not affiche.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=1200:-2", "-q:v", "4", str(affiche)], check=False)
    rel, aff = src.relative_to(ICI), affiche.relative_to(ICI)
    if nom == "hero":
        return (f'<video class="hero-film-fond" src="{prefixe}{rel}" poster="{prefixe}{aff}" autoplay muted loop playsinline '
                f'aria-hidden="true"></video>')
    return (f'<video class="bande" src="{prefixe}{rel}" poster="{prefixe}{aff}" autoplay muted loop playsinline preload="metadata" '
            f'aria-hidden="true"></video>')


# ---------------------------------------------------------------- la page, en quatre versions
def filtrer_public(corps: str, public: str) -> str:
    """Garde les blocs du public demandé, retire ceux de l'autre."""
    for p in ("client", "partenaires"):
        motif = re.compile(r"<!--\[" + p + r"\]-->(.*?)<!--\[/" + p + r"\]-->", re.S)
        corps = motif.sub((lambda m: m.group(1)) if p == public else "", corps)
    return corps


def prefixe_de(dossier: str) -> str:
    return "../" * (dossier.count("/") + 1) if dossier else ""


def autre_langue(v: dict) -> str:
    """Lien vers la même version dans l'autre langue (relatif à la page)."""
    return "en/index.html" if v["lang"] == "fr" else "../index.html"


def chiffres() -> dict:
    """Les chiffres cités dans le texte, relus à leur source quand elle existe."""
    c = {"alp-autres": 33,      # vidéos du marché lointain (onglet dédié du livrable créateurs)
         "sh-videos": 101}      # vidéos retenues après vérification sur leur page (showroom)
    stats = CLAUDE / "acme-semantique" / "data" / "stats.json"
    if stats.exists():
        s = json.loads(stats.read_text(encoding="utf-8"))
        c.update({"sem-occ": s.get("occ"), "sem-itw": s.get("itw"), "sem-champs": s.get("champs"), "sem-parties": s.get("parties")})
    return {k: v for k, v in c.items() if v is not None}


def nombre(n, lang: str) -> str:
    """12345 → « 12 345 » (espace fine insécable) en français, « 12,345 » en anglais."""
    if not isinstance(n, int):
        return str(n)
    s = f"{n:,}"
    return s.replace(",", " ") if lang == "fr" else s


def hub(v: dict) -> str:
    source = ICI / ("contenu.html" if v["lang"] == "fr" else "contenu.en.html")
    if not source.exists():
        print(f"   ✗ texte absent : {source.name}", file=sys.stderr)
        return ""
    pre = prefixe_de(v["dossier"])
    corps = filtrer_public(source.read_text(encoding="utf-8"), v["public"])
    corps = re.sub(r"\{\{slider:([a-z-]+)\}\}", lambda m: slider(m.group(1), v["public"], v["lang"], pre), corps)
    corps = re.sub(r"\{\{video:([a-z-]+)\}\}", lambda m: video_slot(m.group(1), pre), corps)
    corps = (corps.replace("{{date}}", DATE[v["lang"]]).replace("{{p}}", pre).replace("{{autre-langue}}", autre_langue(v)))
    for cle, n in chiffres().items():
        corps = corps.replace("{{" + cle + "}}", nombre(n, v["lang"]))
    reste = sorted(set(re.findall(r"\{\{[a-z0-9:-]+\}\}", corps)))
    if reste:
        print(f"   ⚠ {v['cle']} : repère(s) non remplacé(s) {reste}", file=sys.stderr)
    return tete(TITRES[v["lang"]], pre, v["lang"]) + f"""<body>
{corps}
<script src="{pre}assets/hub.js"></script>
</body>
</html>
"""


def protocole() -> None:
    for lang, cle, dossier, titre, meta in (
            ("fr", "protocole", ICI / "protocole", "Protocole d'entretien conduit par une IA", "Document générique · version 1.0 · 25 août 2026"),
            ("en", "protocole_en", ICI / "protocole" / "en", "AI-led interview protocol", "Generic document · version 1.0 · 25 August 2026")):
        src = SOURCES[cle]
        if not src.exists():
            print(f"   ⚠ source absente : {src.name}", file=sys.stderr)
            continue
        # Le document cite le terrain qui a servi de corpus de mesure (un code de
        # trois lettres) : on le désigne sans le nommer, comme partout ailleurs.
        texte = re.sub(r"10 entretiens [A-Z]{2,4} menés", "10 entretiens d'un même terrain menés", src.read_text(encoding="utf-8"))
        # l'exemple d'ouverture reprenait le prénom d'un participant réel : prénom d'emprunt
        texte = re.sub(r"\bPhilippe\b", "Julien", texte)
        # l'article sur la relance a un seul auteur (O. C. Robinson, Qualitative Research in
        # Psychology, 20(3), 2023) : la source lui adjoignait un co-auteur qui n'existe pas
        texte = texte.replace("Robinson, S. & Rosenberg, D. (2023)", "Robinson, O. C. (2023)")
        texte = texte.replace("Robinson & Rosenberg", "Robinson")
        dossier.mkdir(parents=True, exist_ok=True)
        pre = "../" if lang == "fr" else "../../"
        repli = "../index.html" if lang == "fr" else "../../en/index.html"
        (dossier / "index.html").write_text(page_doc(titre, meta, rendre(texte), repli, pre, lang), encoding="utf-8")
        print(f"   ✓ {dossier.relative_to(ICI)}/index.html")


# ---------------------------------------------------------------- chiffrement
# Format « ACM2 » : le contenu est chiffré une seule fois (AES-256-GCM) avec une
# clé de contenu tirée au hasard ; cette clé est ensuite enveloppée pour chaque
# code autorisé (clé dérivée du code par PBKDF2-SHA256). Un document partagé par
# deux codes ne pèse donc qu'une fois.
#   "ACM2" | n | n × (sel 16 | iv 12 | clé enveloppée 48) | iv 12 | contenu chiffré
GATE_JS = """
const FICHIER = %(fichier)s, ITER = %(iter)d, CLE = 'acme2026-code', TXT = %(txt)s;
let BUF = null;
async function charger() {
  if (!BUF) { const r = await fetch(FICHIER, { cache: 'no-store' }); if (!r.ok) throw new Error('absent'); BUF = new Uint8Array(await r.arrayBuffer()); }
  return BUF;
}
async function derive(code, sel) {
  const km = await crypto.subtle.importKey('raw', new TextEncoder().encode(code), { name: 'PBKDF2' }, false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: sel, iterations: ITER, hash: 'SHA-256' }, km, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
}
async function dechiffrer(code) {
  const b = await charger(), dec = new TextDecoder();
  if (b[0] === 65 && b[1] === 67 && b[2] === 77 && b[3] === 50) {
    const n = b[4]; let pos = 5, cek = null;
    for (let k = 0; k < n && !cek; k++, pos += 76) {
      try {
        const kek = await derive(code, b.slice(pos, pos + 16));
        const brute = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b.slice(pos + 16, pos + 28) }, kek, b.slice(pos + 28, pos + 76));
        cek = await crypto.subtle.importKey('raw', brute, { name: 'AES-GCM' }, false, ['decrypt']);
      } catch (e) {}
    }
    if (!cek) throw new Error('code');
    const d = 5 + 76 * n;
    return dec.decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b.slice(d, d + 12) }, cek, b.slice(d + 12)));
  }
  const kek = await derive(code, b.slice(0, 16));          // ancien format : un seul code
  return dec.decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b.slice(16, 28) }, kek, b.slice(28)));
}
const form = document.getElementById('form'), pw = document.getElementById('pw'), btn = document.getElementById('btn'), err = document.getElementById('err');
async function ouvrir(code, silencieux) {
  btn.disabled = true; btn.textContent = TXT.encours; err.textContent = '';
  try {
    const html = await dechiffrer(code);
    try { sessionStorage.setItem(CLE, code); } catch (e) {}
    document.open(); document.write(html); document.close();
  } catch (e) {
    if (!silencieux) err.textContent = TXT.faux;
    btn.disabled = false; btn.textContent = TXT.ouvrir;
  }
}
form.addEventListener('submit', e => { e.preventDefault(); ouvrir(pw.value.trim(), false); });
try { const s = sessionStorage.getItem(CLE); if (s) ouvrir(s, true); } catch (e) {}
"""


def page_gate(titre: str, sous_titre: str, fichier: str, prefixe: str = "../", eyebrow: str = "— Espace réservé",
              retour: str | None = "../index.html", lang: str = "fr") -> str:
    """La grille d'accès : une page sans contenu, qui va chercher un .bin et le
    déchiffre avec le code. Un code, mémorisé le temps de l'onglet, ouvre tout
    ce qui a été chiffré pour lui."""
    t = T[lang]
    lien = (f' <a href="{esc(retour)}" onclick="{RETOUR_JS}" style="color:inherit">{esc(t["retour"])}</a>' if retour else "")
    txt = json.dumps({"encours": t["encours"], "faux": t["faux"], "ouvrir": t["ouvrir"]}, ensure_ascii=False)
    return tete(titre, prefixe, lang) + f"""<body class="gate">
<div class="gate-inner">
  <div class="gate-box">
    <img src="{prefixe}assets/acme-blanc-h.svg" alt="ACMÉ">
    <div class="eyebrow">{esc(eyebrow)}</div>
    <h1>{esc(titre)}</h1>
    <p>{esc(sous_titre)}</p>
    <form id="form" class="gate-form" autocomplete="off">
      <input id="pw" type="password" placeholder="{esc(t['code'])}" aria-label="{esc(t['code'])}" autocomplete="off" required>
      <button id="btn" type="submit" class="btn btn--light">{esc(t['ouvrir'])}</button>
    </form>
    <div id="err" class="gate-err" aria-live="polite"></div>
  </div>
</div>
<div class="gate-pied"><span>{esc(t['pied'])}{lien}</span></div>
<script>{GATE_JS % dict(fichier=json.dumps(fichier), iter=ITERATIONS, txt=txt)}</script>
</body>
</html>
"""


def lire_code(qui: str = "principal") -> str:
    f = CODES[qui]
    if f.exists():
        code = f.read_text(encoding="utf-8").strip()
        if code:
            return code
    mots = ["cassette", "verbatim", "terrain", "atelier", "hayon", "entretien", "clinique", "corpus",
            "signal", "phrase", "guide", "profil", "carte", "bande", "encre", "filet", "bobine", "plateau",
            "relance", "calandre", "monographie", "salle", "stimulus", "curseur"]
    code = "-".join(secrets.choice(mots) for _ in range(3)) + "-" + str(secrets.randbelow(9000) + 1000)
    f.write_text(code + "\n", encoding="utf-8")
    print(f"   ✓ code « {qui} » généré dans {f.name} (non affiché)")
    return code


def _kdf(code: str, sel: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return PBKDF2HMAC(hashes.SHA256(), 32, sel, ITERATIONS).derive(code.encode("utf-8"))


def chiffrer(clair: str, codes: list[str]) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    cek = AESGCM.generate_key(bit_length=256)
    out = bytearray(b"ACM2" + bytes([len(codes)]))
    for code in codes:
        sel, iv = os.urandom(16), os.urandom(12)
        out += sel + iv + AESGCM(_kdf(code, sel)).encrypt(iv, cek, None)
    iv = os.urandom(12)
    out += iv + AESGCM(cek).encrypt(iv, clair.encode("utf-8"), None)
    return bytes(out)


def dechiffrer(blob: bytes, code: str) -> str | None:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    assert blob[:4] == b"ACM2"
    n, pos = blob[4], 5
    for _ in range(n):
        sel, iv, env = blob[pos:pos + 16], blob[pos + 16:pos + 28], blob[pos + 28:pos + 76]
        pos += 76
        try:
            cek = AESGCM(_kdf(code, sel)).decrypt(iv, env, None)
        except InvalidTag:
            continue
        d = 5 + 76 * n
        return AESGCM(cek).decrypt(blob[d:d + 12], blob[d + 12:], None).decode("utf-8")
    return None


def assurer_crypto() -> bool:
    try:
        import cryptography  # noqa: F401
        return True
    except ImportError:
        if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
            print(f"   ↻ cryptography absente : relance avec {VENV_PY}")
            os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])
        print("   ✗ le module cryptography manque — rien n'est chiffré", file=sys.stderr)
        return False


def mots_sensibles() -> list[str]:
    liste = ICI / "_mots-sensibles.txt"
    if not liste.exists():
        return []
    return [m.strip() for m in liste.read_text(encoding="utf-8").splitlines() if m.strip() and not m.startswith("#")]


def residus(clair: str, etiquette: str, strict: bool = False) -> int:
    """Contrôle en mémoire, avant chiffrement. Un mot sensible chiffré reste
    protégé, mais pas voulu ; pour ce que le code partenaires ouvre, c'est une
    fuite : `strict` le signale comme tel."""
    t = re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=]+", "", clair)
    trouves = [m for m in mots_sensibles() if re.search(r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", t)]
    if trouves:
        print(f"   {'✗ FUITE' if strict else '⚠'} {etiquette} : résidu(s) avant chiffrement : {trouves}", file=sys.stderr)
    return len(trouves)


def sceller(clair: str, dossier: Path, nom: str, codes: tuple[str, ...], titre: str, sous_titre: str,
            prefixe: str = "../", eyebrow: str = "— Espace réservé", retour: str | None = "../index.html",
            lang: str = "fr") -> None:
    """Chiffre `clair` dans <nom>.bin, ouvrable par chacun des `codes` ; écrit la
    grille <nom>.html. Vérifie que chaque code ouvre, et que l'autre non."""
    dossier.mkdir(parents=True, exist_ok=True)
    valeurs = [lire_code(q) for q in codes]
    blob = chiffrer(clair, valeurs)
    for v in valeurs:
        assert dechiffrer(blob, v) == clair
    for q in CODES:
        if q not in codes and CODES[q].exists():
            assert dechiffrer(blob, lire_code(q)) is None, f"le code {q} ouvre {nom} : refus"
    (dossier / f"{nom}.bin").write_bytes(blob)
    (dossier / f"{nom}.p.bin").unlink(missing_ok=True)          # ancien double chiffré
    (dossier / f"{nom}.html").write_text(page_gate(titre, sous_titre, f"{nom}.bin", prefixe, eyebrow, retour, lang), encoding="utf-8")
    print(f"   ✓ {dossier.relative_to(ICI) if dossier != ICI else '.'}/{nom} · {'+'.join(codes)} ({len(blob) // 1024} Ko)")


def gate_seule(dossier: Path, nom: str, fichier: str, titre: str, sous_titre: str, prefixe: str, eyebrow: str,
               retour: str | None, lang: str) -> None:
    """Une grille dans une autre langue pour un .bin écrit ailleurs."""
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{nom}.html").write_text(page_gate(titre, sous_titre, fichier, prefixe, eyebrow, retour, lang), encoding="utf-8")


# ---------------------------------------------------------------- espace réservé (code principal seul)
def sous_hub_reserve() -> str:
    cartes = [
        ("etude.html", "Étude concurrentielle", "23 acteurs, 25 août 2026",
         "Le terrain : six concurrents historiques et seize nouveaux entrants, dont les plateformes d'entretien par IA. "
         "Le positionnement retenu, « la parole client structurée jusqu'à la décision », les requêtes à viser et celles à fuir, "
         "les battle cards. Le document nomme des comptes clients : il reste ici."),
        ("recommandations.html", "Recommandations", "contenus, SEO et suite à donner",
         "Ce qui est livré, les quatre décisions qui bloquent la mise en ligne, le plan des douze prochaines semaines, "
         "et l'offre Décision rapide confrontée à la concurrence : là où elle gagne, là où elle perd."),
        ("adr.html", "AI Interviews — l'étude technique", "ADR-001, 25 août 2026",
         "Sept décisions d'architecture pour l'entretien mené par un bot : serveur plutôt qu'iPhone, pipeline cascadé plutôt "
         "que speech-to-speech, guide transformé en donnée, coût par entretien. Le terrain de référence y est nommé."),
        ("small-van.html", "Small Van — l'histoire digitale", "étude exploratoire, mai 2026",
         "Le livrable complet : vingt-huit scènes, le véhicule qui se construit au défilement, cinq univers métier, trois "
         "concepts. Fichier lourd (12 Mo), à ouvrir sur ordinateur. Le commanditaire y est nommé."),
        ("showroom.html", "Showroom Intelligence — cinq concurrents face au concept", "clinique de juin 2026",
         "Deux regards confrontés voiture par voiture : ce que la salle a dit en clinique, ce que le marché en dit "
         "(avis, presse, créateurs, ventes). Fichier lourd, à ouvrir sur ordinateur. Comptes et véhicules concurrents "
         "nommés."),
    ]
    blocs = "".join(f"""
      <article class="livrable">
        <div class="eyebrow">{esc(meta)}</div>
        <h3>{esc(titre)}</h3>
        <p>{esc(texte)}</p>
        <div class="livrable-pied"><a class="btn" href="{fichier}">Ouvrir <span class="ar">→</span></a></div>
      </article>""" for fichier, titre, meta, texte in cartes)
    return tete("ACMÉ 2026 — espace réservé", "../") + f"""<body>
<header class="nav"><div class="container nav-inner">
  <a class="nav-logo" href="../index.html"><img src="../assets/acme-noir-h.svg" alt="ACMÉ"></a>
  <nav class="nav-links"><a href="../index.html">← Retour au dossier</a></nav>
</div></header>
<section class="section">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">— Espace réservé · déverrouillé</div>
      <h2 class="display">Cinq documents,<br>sous code.</h2>
      <p class="lead">Ils nomment des clients ou des terrains sous accord de confidentialité. Ils ne quittent pas cet espace. Le code reste valable pour les cinq tant que l'onglet est ouvert.</p>
    </div>
    <div class="livrables">{blocs}
    </div>
  </div>
</section>
<footer class="pied"><div class="container"><span class="mono">Dossier de travail interne · non indexé · {esc(DATE['fr'])}</span></div></footer>
</body>
</html>
"""


def charset(html: str) -> str:
    """Les exports d'artefacts commencent par <title> sans déclaration d'encodage."""
    if re.search(r"<meta\s+charset", html, flags=re.I):
        return html
    return '<meta charset="utf-8">\n<meta name="robots" content="noindex, nofollow">\n' + html


def reserve() -> None:
    if not assurer_crypto():
        return
    dossier = ICI / "reserve"
    docs = {"index": ("Espace réservé", "Cinq documents qui nomment des clients ou des terrains sous accord de confidentialité.",
                      sous_hub_reserve())}
    if SOURCES["etude"].exists():
        docs["etude"] = ("Étude concurrentielle", "Dossier interne, 23 acteurs. Le document nomme des comptes clients.",
                         charset(SOURCES["etude"].read_text(encoding="utf-8")))
    if SOURCES["recommandations"].exists():
        docs["recommandations"] = ("Recommandations", "Contenus, SEO/GEO et suite à donner. Document interne du 25 août 2026.",
                                   page_doc("ACMÉ — contenus, SEO/GEO et suite à donner", "Document interne · 25 août 2026",
                                            rendre(SOURCES["recommandations"].read_text(encoding="utf-8")),
                                            repli="index.html", prefixe="../"))
    if SOURCES["adr"].exists():
        docs["adr"] = ("AI Interviews — l'étude technique", "ADR-001 : sept décisions d'architecture. Le terrain de référence y est nommé.",
                       charset(SOURCES["adr"].read_text(encoding="utf-8")))
    if SOURCES["smallvan"].exists():
        docs["small-van"] = ("Small Van — l'histoire digitale", "Livrable client complet, 12 Mo. Le déchiffrement prend quelques secondes.",
                             SOURCES["smallvan"].read_text(encoding="utf-8"))
    if SOURCES["bbr"].exists():
        docs["showroom"] = ("Showroom Intelligence — cinq concurrents face au concept",
                            "Clinique de juin 2026 : ce que la salle a dit des concurrents, confronté au marché. "
                            "Document confidentiel, comptes et véhicules nommés. Fichier lourd, le déchiffrement prend "
                            "quelques secondes.",
                            charset(SOURCES["bbr"].read_text(encoding="utf-8")))
    ANCRES = {"showroom": "../index.html#showroom"}
    for nom, (titre, sous_titre, clair) in docs.items():
        sceller(clair, dossier, nom, ("principal",), titre, sous_titre, retour=ANCRES.get(nom, "../index.html"))
    manquants = [cle for cle in ("etude", "recommandations", "adr", "smallvan", "bbr") if not SOURCES[cle].exists()]
    if manquants:
        print(f"   ⚠ sources absentes, document(s) non régénéré(s) : {manquants}", file=sys.stderr)


# ---------------------------------------------------------------- documents partagés (les deux codes)
def demo_neutralisee() -> str:
    """La démonstration Concept NORD, relue à sa source, avec ce que l'anonymisation
    avait laissé passer dans le code : le lexique de recherche gardait des noms de
    modèles et le nom de code du terrain (entrées codées D, S et R), et une fonction
    portait un nom de constructeur. On ne les écrit pas ici : ce script est publié."""
    t = SOURCES["demo"].read_text(encoding="utf-8")
    t = re.sub(r"\['[a-z0-9 ]+', '[DSR]'\], ", "", t)
    t = re.sub(r"(\[\['jeep', 'J'\].*?\['yaris', 'T'\])\]\]", r"\1, ['nord', 'R']]]", t, count=1)
    t = re.sub(r"\b\w+ltLogo\b", "marqueLogo", t)
    t = masquer_noms_dans_donnees(t)
    if '<meta name="robots"' not in t:
        t = t.replace("<head>", '<head><meta name="robots" content="noindex, nofollow, noarchive">', 1)
    return t


def noms_a_masquer() -> list[str]:
    """Noms de famille de répondants restés dans les données anonymisées (liste
    locale, ignorée par git : l'écrire ici reviendrait à la publier)."""
    f = ICI / "_noms-a-masquer.txt"
    if not f.exists():
        return []
    return [l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def masquer_noms_dans_donnees(t: str) -> str:
    """Le corpus de la démonstration voyage compressé (gzip + base64) dans une
    balise <script id="verbatim-donnees"> : on le décompresse, on remplace les
    noms de famille par « … », on le recompresse."""
    import base64, gzip
    noms = noms_a_masquer()
    m = re.search(r'(<script id="verbatim-donnees" type="application/gzip\+base64">)([A-Za-z0-9+/=\s]+)(</script>)', t)
    if not noms or not m:
        if noms:
            print("   ⚠ démonstration : bloc de données compressé introuvable, noms non masqués", file=sys.stderr)
        return t
    clair = gzip.decompress(base64.b64decode(re.sub(r"\s", "", m.group(2)))).decode("utf-8")
    rx = re.compile(r"(?<![\wÀ-ÿ])(" + "|".join(re.escape(n) for n in noms) + r")(?![\wÀ-ÿ])")
    clair, n = rx.subn("…", clair)
    reste = [x for x in noms if x in clair]
    assert not reste, "noms encore présents"
    blob = base64.b64encode(gzip.compress(clair.encode("utf-8"), 9)).decode("ascii")
    print(f"   · démonstration : {n} nom(s) de famille masqué(s) dans le corpus")
    return t[:m.start(2)] + blob + t[m.end(2):]


def proposition_autonome(src: Path) -> str:
    """La proposition, avec ses captures et ses deux vidéos incorporées : un seul
    clair, un seul chiffré, aucun média de l'étude servi en clair à côté."""
    import base64, mimetypes
    t = src.read_text(encoding="utf-8")
    dossier = src.parent / "assets"

    def data_uri(m):
        p = dossier / m.group(1)
        if not p.exists():
            return m.group(0)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return f'{m.group(0).split("=")[0]}="data:{mime};base64,{base64.b64encode(p.read_bytes()).decode("ascii")}"'
    return re.sub(r'(?:src|poster)="assets/([^"]+)"', data_uri, t)


DECISION = {
    "fr": {"shots": [("site-04-decision.jpg", "Décider en six semaines, pas en six mois."),
                     ("site-05-configurateur.jpg", "Le configurateur : quatre questions, un dispositif."),
                     ("site-06-dispositif.jpg", "Le dispositif recommandé, son calendrier, ses livrables ; chiffrage sous 48 h.")],
           "titre": "Décision rapide — le configurateur", "eyebrow": "— Décision rapide · déverrouillé",
           "h2": "Composer votre dispositif.", "retour": "← Retour à la page",
           "lead": "Le socle ne bouge pas : cadrage, recrutement, terrain conduit par un consultant senior, transcripts intégraux. "
                   "Les livrables sont en options : plateforme VERBATIM, top lines, analyse complète, typologies, atelier de décision.",
           "lbl": "Le configurateur",
           "p": "Il qualifie votre besoin en quatre questions et renvoie le dispositif recommandé, son calendrier et la liste exacte "
                "des livrables. Aucun prix n'est affiché à un visiteur : il produit un schéma et un calendrier, puis renvoie vers "
                "un chiffrage sous 48 heures.",
           "btn": "Composer votre dispositif", "cap": "Outil en ligne, hébergé à part, non indexé.", "pied": "Accès protégé"},
    "en": {"shots": [("site-04-decision-en.jpg", "Decide in six weeks, not six months."),
                     ("site-05-configurateur-en.jpg", "The configurator: four questions, one set-up."),
                     ("site-06-dispositif-en.jpg", "The recommended set-up, its timeline, its deliverables; costed within 48 hours.")],
           "titre": "Quick Decision — the configurator", "eyebrow": "— Quick Decision · unlocked",
           "h2": "Build your study set-up.", "retour": "← Back to the page",
           "lead": "The core never changes: scoping, recruitment, fieldwork led by a senior consultant, full transcripts. "
                   "Deliverables are options: VERBATIM platform, top lines, full analysis, typologies, decision workshop.",
           "lbl": "The configurator",
           "p": "It qualifies your need in four questions and returns the recommended set-up, its timeline and the exact list of "
                "deliverables. No price is shown to a visitor: it produces a plan and a timeline, then leads to a quote within 48 hours.",
           "btn": "Build your set-up", "cap": "Online tool, hosted separately, not indexed.", "pied": "Protected access"},
}


def decision_scellee(lang: str) -> str:
    """Le détail de Décision rapide : les captures du configurateur embarquées en
    data: (jamais servies en clair à leur propre URL), plus le lien vers l'outil."""
    import base64
    d = DECISION[lang]
    pre = "../" if lang == "fr" else "../../"
    slides = []
    for nom, legende in d["shots"]:
        p = ICI / "shots" / nom
        if not p.exists() and lang == "en":
            p = ICI / "shots" / nom.replace("-en.jpg", ".jpg")
        if not p.exists():
            print(f"   ⚠ capture absente : shots/{nom}", file=sys.stderr)
            continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        slides.append(f'<figure class="slide"><img src="data:image/jpeg;base64,{b64}" alt=""><figcaption>{esc(legende)}</figcaption></figure>')
    t = T[lang]
    bloc = ""
    if slides:
        bloc = (f'<div class="slider" data-slider tabindex="0" aria-label="{t["ecrans"]}">'
                f'<div class="slider-track">{"".join(slides)}</div>'
                f'<div class="slider-bar"><button type="button" class="slider-btn slider-prev" aria-label="{t["prec"]}">←</button>'
                f'<div class="slider-dots"></div><span class="slider-count mono">1 / {len(slides)}</span>'
                f'<button type="button" class="slider-btn slider-next" aria-label="{t["suiv"]}">→</button></div></div>')
    site = "https://vbouin.github.io/acme-site/v5.2/decision-rapide.html"
    corps = f"""
<header class="nav"><div class="container nav-inner">
  <a class="nav-logo" href="{pre}index.html" onclick="{RETOUR_JS}"><img src="{pre}assets/acme-noir-h.svg" alt="ACMÉ"></a>
  <nav class="nav-links"><a href="{pre}index.html" onclick="{RETOUR_JS}">{esc(d['retour'])}</a></nav>
</div></header>
<section class="section">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">{esc(d['eyebrow'])}</div>
      <h2 class="display">{esc(d['h2'])}</h2>
      <p class="lead">{esc(d['lead'])}</p>
    </div>
    <div class="vitrine">{bloc}</div>
    <div class="colonnes">
      <div>
        <div class="lbl">{esc(d['lbl'])}</div>
        <p class="texte">{esc(d['p'])}</p>
      </div>
      <div>
        <div class="actions" style="margin-top:0">
          <a class="btn btn--dark" href="{site}" target="_blank" rel="noopener">{esc(d['btn'])} <span class="ar">→</span></a>
        </div>
        <p class="cap">{esc(d['cap'])}</p>
      </div>
    </div>
  </div>
</section>
<footer class="pied"><div class="container"><span class="mono">{esc(d['pied'])} · {esc(DATE[lang])}</span></div></footer>
<script src="{pre}assets/hub.js"></script>
"""
    return tete(d["titre"], pre, lang) + f"<body>{corps}</body></html>"


PARTAGES = ("principal", "partenaires")
# Le corpus lui-même (la démonstration, les champs sémantiques) reste réservé au
# code principal : c'est le terrain d'un client, même anonymisé. Les partenaires
# en voient les écrans, floutés, sur leur page ; l'outil se montre en rendez-vous.
# Pour le leur ouvrir aussi : CORPUS = PARTAGES.
CORPUS = ("principal",)


def donnees() -> None:
    """Ce qui porte de la matière d'étude ou du commercial est chiffré :
    démonstration et champs sémantiques au code principal, proposition et
    Décision rapide aux deux codes. Tout ce que le code partenaires ouvre passe
    le contrôle des mots sensibles en mode strict."""
    if not assurer_crypto():
        return
    # la démonstration Concept NORD (interface en français ; grille dans les deux langues)
    if SOURCES["demo"].exists():
        clair = demo_neutralisee()
        residus(clair, "démonstration")
        sceller(clair, ICI / "demo", "verbatim-nord", CORPUS, "Concept NORD — la démonstration",
                "Le corpus de la démonstration, 53 entretiens anonymisés, est chiffré. Il s'ouvre avec le code transmis "
                "avec ce document, une seule fois par onglet.", eyebrow="— Démonstration", retour="../index.html#verbatim")
        gate_seule(ICI / "demo" / "en", "verbatim-nord", "../verbatim-nord.bin",
                   "Concept NORD — the demo", "The demo corpus, 53 anonymised interviews, is encrypted. It opens with the code "
                   "sent with this document, once per tab. The interface is in French, the language of the fieldwork.",
                   "../../", "— Demo", "../../en/index.html#verbatim", "en")
    else:
        print(f"   ⚠ source absente : {SOURCES['demo']}", file=sys.stderr)
    # les champs sémantiques (une page, deux langues : la langue suit l'adresse)
    if SOURCES["semantique"].exists():
        clair = SOURCES["semantique"].read_text(encoding="utf-8")
        residus(clair, "champs sémantiques")
        sceller(clair, ICI / "demo", "champs-semantiques", CORPUS, "Champs sémantiques — l'outil",
                "Les qualificatifs relevés dans les entretiens, rattachés aux parties du véhicule, sont chiffrés. "
                "Même code que la démonstration.", eyebrow="— Champs sémantiques", retour="../index.html#livrables")
        gate_seule(ICI / "demo" / "en", "champs-semantiques", "../champs-semantiques.bin",
                   "Semantic fields — the tool", "The qualifiers found in the interviews, tied to vehicle parts, are encrypted. "
                   "Same code as the demo.", "../../", "— Semantic fields", "../../en/index.html#livrables", "en")
    else:
        print(f"   ⚠ source absente : {SOURCES['semantique']}", file=sys.stderr)
    # la proposition, en français et en anglais
    for lang, cle, dossier, titre, sous in (
            ("fr", "proposition", ICI / "proposition", "La proposition détaillée",
             "La proposition et ses captures de la plateforme sont chiffrées. Même code que la démonstration."),
            ("en", "proposition_en", ICI / "proposition" / "en", "The detailed proposal",
             "The proposal and its platform screenshots are encrypted. Same code as the demo.")):
        if not SOURCES[cle].exists():
            print(f"   ⚠ source absente : {SOURCES[cle].name}", file=sys.stderr)
            continue
        clair = proposition_autonome(SOURCES[cle])
        residus(clair, f"proposition ({lang})", strict=True)
        sceller(clair, dossier, "index", PARTAGES, titre, sous, prefixe="../" if lang == "fr" else "../../",
                eyebrow="— Proposition" if lang == "fr" else "— Proposal",
                retour="../index.html#verbatim" if lang == "fr" else "../../en/index.html#verbatim", lang=lang)
    # Décision rapide
    for lang, dossier in (("fr", ICI / "decision"), ("en", ICI / "decision" / "en")):
        clair = decision_scellee(lang)
        residus(clair, f"décision rapide ({lang})", strict=True)
        d = DECISION[lang]
        sceller(clair, dossier, "index", PARTAGES, d["titre"],
                "Les écrans et le lien du configurateur sont chiffrés. Même code que la démonstration." if lang == "fr" else
                "The configurator screens and link are encrypted. Same code as the demo.",
                prefixe="../" if lang == "fr" else "../../", eyebrow="— Décision rapide" if lang == "fr" else "— Quick Decision",
                retour="../index.html#decision" if lang == "fr" else "../../en/index.html#decision", lang=lang)


def pages(chiffre: bool) -> None:
    """Les quatre versions de la page. Chiffrées : une grille par version, un .bin
    au code de la version (le code partenaires n'ouvre pas la page client)."""
    if chiffre and not assurer_crypto():
        return
    for v in VERSIONS:
        html = hub(v)
        if not html:
            continue
        dossier = ICI / v["dossier"] if v["dossier"] else ICI
        dossier.mkdir(parents=True, exist_ok=True)
        pre = prefixe_de(v["dossier"])
        if v["public"] == "partenaires":
            residus(html, f"page {v['cle']}", strict=True)
        if chiffre:
            en = v["lang"] == "en"
            sceller(html, dossier, "index", (v["code"],), TITRES[v["lang"]],
                    ("This document is reserved for its recipients. It opens with the code that comes with it." if en else
                     "Ce document est réservé à ses destinataires. Il s'ouvre avec le code qui l'accompagne."),
                    prefixe=pre, eyebrow="— ACMÉ · Our future" if en else "— ACMÉ · Notre avenir", retour=None, lang=v["lang"])
        else:
            (dossier / "index.html").write_text(html, encoding="utf-8")
            for f in ("index.bin", "index.p.bin"):
                (dossier / f).unlink(missing_ok=True)
            print(f"   ✓ {v['dossier'] or '.'}/index.html ({len(html) // 1024} Ko, en clair)")


# ---------------------------------------------------------------- annexes
def annexes() -> None:
    (ICI / "robots.txt").write_text("# Dossier de travail partagé par lien. Ne pas indexer.\nUser-agent: *\nDisallow: /\n", encoding="utf-8")
    (ICI / ".nojekyll").write_text("", encoding="utf-8")
    (ICI / ".gitignore").write_text("\n".join([
        "CODE-ACCES-NE-PAS-PUBLIER.txt", "CODE-PARTENAIRES-NE-PAS-PUBLIER.txt", "_noms-a-masquer.txt", "assets/faces.json", "__pycache__/",
        ".DS_Store", "_tmp/", "*.log", "shots/_hub*", "shots/_ctl/",
        # la table de masquage et la liste de contrôle nomment ce qu'elles protègent
        "scenarios.mjs", "_mots-sensibles.txt",
        # les données ne vivent ici que chiffrées (.bin) : jamais de copie en clair
        "proposition/assets/", "demo/*.clair.html",
        # embarquées en data: dans decision/*.bin ; servies en clair à leur URL, elles annuleraient le chiffrement
        "shots/site-0*.jpg", ""
    ]), encoding="utf-8")


def controle_fuites() -> None:
    """Ce qui est publié en clair ne doit nommer aucun client ni terrain."""
    mots = mots_sensibles()
    if not mots:
        print("   ⚠ _mots-sensibles.txt absent : contrôle de fuite non fait", file=sys.stderr)
        return
    publics = [p for p in ICI.rglob("*") if p.is_file() and p.suffix in (".html", ".js", ".mjs", ".py", ".md", ".css", ".txt")
               and ".git" not in p.parts and p.name not in ("_mots-sensibles.txt", "scenarios.mjs")
               and not p.name.startswith("CODE-") and p.name != "_noms-a-masquer.txt"]
    total = 0
    for f in publics:
        t = f.read_text(encoding="utf-8", errors="ignore")
        t = re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=]+", "", t)
        trouves = [m for m in mots if re.search(r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", t)]
        if trouves:
            total += 1
            print(f"   ⚠ {f.relative_to(ICI)} nomme : {trouves}", file=sys.stderr)
    print(f"   ✓ {len(publics)} fichiers contrôlés, {total} en alerte")


def main() -> int:
    sans_reserve = "--sans-reserve" in sys.argv
    chiffre = "--en-clair" not in sys.argv
    print("Polices"); fonts_css()
    print("Documents"); protocole()
    print("Pages" + (" (chiffrées)" if chiffre else " (en clair)")); pages(chiffre)
    print("Données chiffrées"); donnees()
    if not sans_reserve:
        print("Espace réservé"); reserve()
    annexes()
    print("Contrôle"); controle_fuites()
    total = sum(p.stat().st_size for p in ICI.rglob("*") if p.is_file() and ".git" not in p.parts)
    print(f"\n→ dossier : {total / 1048576:.1f} Mo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
