#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemble le dossier « ACMÉ 2026 » — le hub qui regroupe les livrables sur le
futur du cabinet, pour partage par lien (public, non indexé).

    python3 build.py                 # tout
    python3 build.py --sans-reserve  # sans rechiffrer l'espace réservé

Ce que le script fabrique :
  index.html              le hub : lecture en cinq minutes, sliders d'écrans et
                          de mini-vidéos par livrable, ce qui reste à trancher
  protocole/index.html    le protocole d'entretien (markdown → page document)
  reserve/*.html + *.bin  l'espace réservé : chaque document est chiffré
                          (AES-256-GCM, clé dérivée du code par PBKDF2) dans un
                          fichier .bin ; la page ne contient que la grille d'accès
  assets/fonts.css        les trois polices en @font-face data: (une fois)
  robots.txt, .nojekyll, .gitignore

Les sources sensibles (étude concurrentielle, ADR, Small Van) sont lues à leur
emplacement d'origine et n'entrent JAMAIS en clair dans ce dossier. Le code
d'accès vit dans CODE-ACCES-NE-PAS-PUBLIER.txt (ignoré par git) et n'est
jamais imprimé.
"""
from __future__ import annotations
import html as _html
import json, os, re, secrets, sys
from datetime import date
from pathlib import Path

ICI = Path(__file__).resolve().parent
CLAUDE = ICI.parent
sys.path.insert(0, str(ICI))
from md import rendre  # noqa: E402

SOURCES = {
    "protocole": CLAUDE / "acme-ai-interviews" / "PROTOCOLE-ENTRETIEN.md",
    "recommandations": CLAUDE / "acme-etude-concurrentielle" / "RECOMMANDATIONS.md",
    "etude": CLAUDE / "acme-etude-concurrentielle" / "etude-concurrentielle.html",
    "adr": CLAUDE / "acme-ai-interviews" / "etude-technique.html",
    "smallvan": CLAUDE / "Small-Van-Histoire-Digitale-PARTAGE.html",
    # les données : relues à leur source, jamais copiées en clair dans ce dossier
    "demo": CLAUDE / "plateforme-qual" / "app" / "exports" / "ACME_VERBATIM_demo_NORD_compresse.html",
    "proposition": CLAUDE / "acme-propale-verbatim" / "proposition.html",
    "bbr": CLAUDE / "bbr-intel" / "bbr-showroom-intelligence.html",
}
CODE = ICI / "CODE-ACCES-NE-PAS-PUBLIER.txt"
VENV_PY = CLAUDE / "pseudo-local" / ".venv" / "bin" / "python3"
ITERATIONS = 250_000
DATE = "7 septembre 2026"

# ---------------------------------------------------------------- médias
# Chaque livrable : une liste d'écrans (jpg) et de mini-vidéos (mp4) avec leur
# légende. Un fichier absent est ignoré avec un avertissement, jamais un trou.
MEDIAS = {
    "verbatim": [
        ("shots/demo.mp4", "Le tour de la plateforme : carte du véhicule, atelier, typologies, pays, entretien."),
        ("shots/vb-02-carte.jpg", "La carte du véhicule : chaque pastille est une zone commentée, la taille dit le volume, la couleur la polarité."),
        ("shots/vb-03-zone.jpg", "Un clic sur une zone ouvre les verbatims qui en parlent, avec leur profil et leur polarité."),
        ("shots/vb-04-atelier.jpg", "L'atelier : un mot-clé, croisé avec la question du guide et le point de monographie. Chaque bloc se copie tel quel."),
        ("shots/vb-05-entretien.jpg", "Le verbatim remis dans sa conversation : la question posée juste avant, la relance qui a suivi, l'entretien complet."),
        ("shots/vb-08-profils.jpg", "Les profils, anonymes ou pseudonymes, au choix, sans changer de fichier."),
        ("shots/vb-06-pays.jpg", "France et Allemagne, lus côte à côte."),
        ("shots/vb-07-typologies.jpg", "Les typologies calculées sur le corpus."),
        ("shots/vb-09-champs.jpg", "Les champs sémantiques : le vocabulaire regroupé par thème, chaque mot relié à sa source."),
        ("shots/vb-01-vue.jpg", "La vue d'ensemble : 53 entretiens, 2 027 verbatims ancrés, fidélité vérifiée mot à mot."),
    ],
    "preclinique": [
        ("shots/poc.mp4", "Un pré-entretien joué de bout en bout, par écrit, jusqu'au suivi de terrain."),
        ("shots/pc-01-accueil.jpg", "L'accueil : le participant sait qu'il parle à une IA, et consent explicitement."),
        ("shots/pc-04-question.jpg", "La question du guide, prononcée mot pour mot. L'onde suit la voix."),
        ("shots/pc-05-echange.jpg", "La réponse, puis la relance : elle vient du répertoire fermé du guide."),
        ("shots/pc-07-fiche.jpg", "La fiche de qualification se remplit sous les yeux du chercheur, avec la citation qui fonde chaque valeur."),
        ("shots/pc-09-revue.jpg", "La revue avant clôture : séquence par séquence, ce qui est couvert, partiel ou non abordé."),
        ("shots/pc-10-cloture.jpg", "Ce qui manque est nommé, jamais tu : le redemander maintenant, ou clore en le disant."),
        ("shots/pc-12-terrain.jpg", "Le suivi de terrain : une case par pré-entretien, la répartition des hypothèses de milieu."),
        ("shots/pc-14-profil.jpg", "Le profil d'une séance en une page : ce que la séance a ramené, valeur par valeur."),
    ],
    "voyage": [
        ("media/smallvan-hero.mp4", "L'ouverture : le véhicule se construit à mesure qu'on descend."),
        ("media/smallvan-ouverture.jpg", "La première scène du livrable."),
    ],
    "semantique": [
        ("shots/semantique-01.jpg", "Les mots employés pour chaque véhicule, regroupés par thème."),
        ("shots/semantique-02.jpg", "La balance adhésion / réserve, dimension par dimension."),
        ("shots/semantique-03.jpg", "Chaque mot reste relié au passage dont il vient."),
    ],
    "createurs": [
        ("media/alpine-film.jpg", "L'ouverture du livrable : le récit d'abord, la gamme comparée à droite, les chiffres du dispositif en bas."),
        ("media/alpine-vehicules.jpg", "Synthèse par véhicule, agrégée depuis 62 vidéos de créateurs sur 9 marchés."),
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
    faces.unlink()   # une seule copie des polices dans le dossier
    print(f"   ✓ assets/fonts.css ({cible.stat().st_size // 1024} Ko)")


# ---------------------------------------------------------------- gabarits
def tete(titre: str, prefixe: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
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


def page_doc(titre: str, meta: str, corps: str, retour: str = "../index.html", prefixe: str = "../") -> str:
    corps = re.sub(r"<table>(.*?)</table>", r'<div class="table-wrap"><table>\1</table></div>', corps, flags=re.S)
    # Le premier h1 du markdown devient le titre de page ; on l'enlève du corps.
    corps = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", corps, count=1, flags=re.S)
    return tete(titre, prefixe) + f"""<body>
<main class="doc">
<a class="retour" href="{retour}">← Retour au dossier</a>
<div class="eyebrow">— ACMÉ · 2026</div>
<h1>{esc(titre)}</h1>
<div class="meta">{esc(meta)}</div>
{corps}
</main>
</body>
</html>
"""


def slider(cle: str) -> str:
    items = []
    for fichier, legende in MEDIAS.get(cle, []):
        p = ICI / fichier
        if not p.exists():
            print(f"   ⚠ média absent ({cle}) : {fichier}", file=sys.stderr)
            continue
        if fichier.endswith(".mp4"):
            # L'affiche = la première image de la vidéo, extraite une fois par ffmpeg,
            # pour qu'une vue vidéo ne soit jamais un rectangle noir avant lecture.
            poster = ""
            jpg = p.with_name(p.stem + "-poster.jpg")
            if not jpg.exists():
                import subprocess
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.4", "-i", str(p), "-frames:v", "1",
                                "-vf", "scale=1200:-2", "-q:v", "4", str(jpg)], check=False)
            if jpg.exists():
                poster = f' poster="{esc(str(jpg.relative_to(ICI)))}"'
            media = f'<video src="{esc(fichier)}"{poster} muted loop playsinline preload="metadata"></video>'
        else:
            media = f'<img src="{esc(fichier)}" alt="" loading="lazy">'
        items.append(f'<figure class="slide">{media}<figcaption>{esc(legende)}</figcaption></figure>')
    if not items:
        return '<div class="cadre cadre--vide"><span class="mono">Écrans à venir</span></div>'
    if len(items) == 1:
        return f'<div class="slider slider--seul" data-slider tabindex="0"><div class="slider-track">{items[0]}</div><div class="slider-bar"><button class="slider-btn slider-prev" hidden aria-hidden="true">←</button><span class="slider-count mono"></span><button class="slider-btn slider-next" hidden aria-hidden="true">→</button></div></div>'
    return (f'<div class="slider" data-slider tabindex="0" aria-label="Écrans du livrable">'
            f'<div class="slider-track">{"".join(items)}</div>'
            f'<div class="slider-bar"><button type="button" class="slider-btn slider-prev" aria-label="Écran précédent">←</button>'
            f'<div class="slider-dots"></div><span class="slider-count mono">1 / {len(items)}</span>'
            f'<button type="button" class="slider-btn slider-next" aria-label="Écran suivant">→</button></div></div>')


def video_slot(nom: str) -> str:
    """Un emplacement vidéo de la page. Le rendu IA déposé dans media/ia/<nom>.mp4
    prime ; sinon le rendu provisoire de VIDEOS ; sinon rien."""
    import subprocess
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
        return (f'<video class="hero-film-fond" src="{rel}" poster="{aff}" autoplay muted loop playsinline '
                f'aria-hidden="true"></video>')
    return (f'<video class="bande" src="{rel}" poster="{aff}" autoplay muted loop playsinline preload="metadata" '
            f'aria-hidden="true"></video>')


def hub(retourner: bool = False) -> str:
    corps = (ICI / "contenu.html").read_text(encoding="utf-8")
    corps = re.sub(r"\{\{slider:([a-z-]+)\}\}", lambda m: slider(m.group(1)), corps)
    corps = re.sub(r"\{\{video:([a-z-]+)\}\}", lambda m: video_slot(m.group(1)), corps)
    corps = corps.replace("{{date}}", DATE)
    html = tete("ACMÉ — Notre avenir") + f"""<body>
{corps}
<script src="assets/hub.js"></script>
</body>
</html>
"""
    if retourner:
        return html
    (ICI / "index.html").write_text(html, encoding="utf-8")
    externes = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    externes = [u for u in externes if "vbouin.github.io" not in u]
    print(f"   ✓ index.html ({len(html) // 1024} Ko) — {len(externes)} ressource(s) externe(s)")
    return html


def protocole() -> None:
    src = SOURCES["protocole"]
    if not src.exists():
        print(f"   ✗ source absente : {src}", file=sys.stderr)
        return
    # Le document cite le terrain qui a servi de corpus de mesure (un code de
    # trois lettres) : on le désigne sans le nommer, comme partout ailleurs dans
    # le dossier — et sans l'écrire ici non plus, ce script étant publié.
    texte = re.sub(r"10 entretiens [A-Z]{2,4} menés", "10 entretiens d'un même terrain menés",
                   src.read_text(encoding="utf-8"))
    corps = rendre(texte)
    (ICI / "protocole").mkdir(exist_ok=True)
    (ICI / "protocole" / "index.html").write_text(
        page_doc("Protocole d'entretien conduit par une IA",
                 "Document générique · version 1.0 · 25 août 2026", corps), encoding="utf-8")
    print("   ✓ protocole/index.html")


# ---------------------------------------------------------------- réservé
GATE_JS = """
const FICHIER = %(fichier)s, ITER = %(iter)d, CLE = 'acme2026-code';
async function dechiffrer(code) {
  const buf = new Uint8Array(await (await fetch(FICHIER, { cache: 'no-store' })).arrayBuffer());
  const salt = buf.slice(0, 16), iv = buf.slice(16, 28), ct = buf.slice(28);
  const enc = new TextEncoder();
  const km = await crypto.subtle.importKey('raw', enc.encode(code), { name: 'PBKDF2' }, false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: ITER, hash: 'SHA-256' }, km, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  return new TextDecoder().decode(pt);
}
const form = document.getElementById('form'), pw = document.getElementById('pw'), btn = document.getElementById('btn'), err = document.getElementById('err');
async function ouvrir(code, silencieux) {
  btn.disabled = true; btn.textContent = 'Déchiffrement…'; err.textContent = '';
  try {
    const html = await dechiffrer(code);
    try { sessionStorage.setItem(CLE, code); } catch (e) {}
    document.open(); document.write(html); document.close();
  } catch (e) {
    if (!silencieux) err.textContent = 'Code incorrect.';
    btn.disabled = false; btn.textContent = 'Déverrouiller';
  }
}
form.addEventListener('submit', e => { e.preventDefault(); ouvrir(pw.value.trim(), false); });
try { const s = sessionStorage.getItem(CLE); if (s) ouvrir(s, true); } catch (e) {}
"""


def page_gate(titre: str, sous_titre: str, fichier_bin: str, prefixe: str = "../",
              eyebrow: str = "— Espace réservé", retour: str = "../index.html") -> str:
    """La grille d'accès : une page sans contenu, qui va chercher le .bin et le
    déchiffre avec le code. Un même code, mémorisé le temps de l'onglet, ouvre
    tout ce qui est chiffré dans le dossier."""
    lien = f' <a href="{esc(retour)}" style="color:inherit">Retour à la page</a>' if retour else ""
    return tete(titre, prefixe) + f"""<body class="gate">
<div class="gate-inner">
  <div class="gate-box">
    <img src="{prefixe}assets/acme-blanc-h.svg" alt="ACMÉ">
    <div class="eyebrow">{esc(eyebrow)}</div>
    <h1>{esc(titre)}</h1>
    <p>{esc(sous_titre)}</p>
    <form id="form" class="gate-form" autocomplete="off">
      <input id="pw" type="password" placeholder="Code d'accès" aria-label="Code d'accès" autocomplete="off" required>
      <button id="btn" type="submit" class="btn btn--light">Déverrouiller</button>
    </form>
    <div id="err" class="gate-err" aria-live="polite"></div>
  </div>
</div>
<div class="gate-pied"><span>Le contenu est chiffré dans le fichier servi ; il ne se lit qu'avec le code.{lien}</span></div>
<script>{GATE_JS % dict(fichier=json.dumps(fichier_bin), iter=ITERATIONS)}</script>
</body>
</html>
"""


def sous_hub_reserve() -> str:
    """Le contenu déchiffré de reserve/index.html : la liste des trois documents."""
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
<footer class="pied"><div class="container"><span class="mono">Dossier de travail interne · non indexé · {esc(DATE)}</span></div></footer>
</body>
</html>
"""


def charset(html: str) -> str:
    """Les exports d'artefacts commencent par <title> sans déclaration d'encodage."""
    if re.search(r"<meta\s+charset", html, flags=re.I):
        return html
    return '<meta charset="utf-8">\n<meta name="robots" content="noindex, nofollow">\n' + html


def lire_code() -> str:
    if CODE.exists():
        code = CODE.read_text(encoding="utf-8").strip()
        if code:
            return code
    mots = ["cassette", "verbatim", "terrain", "atelier", "hayon", "entretien", "clinique", "corpus",
            "signal", "phrase", "guide", "profil", "carte", "bande", "encre", "filet", "bobine", "plateau"]
    code = "-".join(secrets.choice(mots) for _ in range(3)) + "-" + str(secrets.randbelow(9000) + 1000)
    CODE.write_text(code + "\n", encoding="utf-8")
    print(f"   ✓ code d'accès généré dans {CODE.name} (non affiché)")
    return code


def chiffrer(clair: str, code: str) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITERATIONS).derive(code.encode("utf-8"))
    return salt + iv + AESGCM(key).encrypt(iv, clair.encode("utf-8"), None)


def verifier(blob: bytes, code: str, attendu: str) -> None:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    key = PBKDF2HMAC(hashes.SHA256(), 32, blob[:16], ITERATIONS).derive(code.encode("utf-8"))
    assert AESGCM(key).decrypt(blob[16:28], blob[28:], None).decode("utf-8") == attendu


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


def residus(clair: str, etiquette: str) -> None:
    """Contrôle en mémoire, avant chiffrement : un mot sensible qui resterait
    dans le clair serait chiffré avec lui — c'est protégé, mais ce n'est pas
    voulu, donc on le dit."""
    t = re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=]+", "", clair)
    trouves = [m for m in mots_sensibles() if re.search(r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", t)]
    if trouves:
        print(f"   ⚠ {etiquette} : résidu(s) avant chiffrement : {trouves}", file=sys.stderr)


def sceller(clair: str, code: str, dossier: Path, nom: str, titre: str, sous_titre: str,
            prefixe: str = "../", eyebrow: str = "— Espace réservé", retour: str = "../index.html") -> None:
    blob = chiffrer(clair, code)
    verifier(blob, code, clair)
    dossier.mkdir(exist_ok=True)
    (dossier / f"{nom}.bin").write_bytes(blob)
    (dossier / f"{nom}.html").write_text(page_gate(titre, sous_titre, f"{nom}.bin", prefixe, eyebrow, retour), encoding="utf-8")
    print(f"   ✓ {dossier.relative_to(ICI) if dossier != ICI else '.'}/{nom}.html + .bin ({len(blob) // 1024} Ko)")


def demo_neutralisee() -> str:
    """La démonstration Concept NORD, relue à sa source, avec ce que l'anonymisation
    avait laissé passer dans le code : le lexique de recherche gardait des noms de
    modèles et le nom de code du terrain (entrées codées D, S et R), et une fonction
    portait un nom de constructeur. On ne les écrit pas ici : ce script est publié."""
    t = SOURCES["demo"].read_text(encoding="utf-8")
    t, n = re.subn(r"\['[a-z0-9 ]+', '[DSR]'\], ", "", t)
    t = re.sub(r"(\[\['jeep', 'J'\].*?\['yaris', 'T'\])\]\]", r"\1, ['nord', 'R']]]", t, count=1)
    t = re.sub(r"\b\w+ltLogo\b", "marqueLogo", t)
    if '<meta name="robots"' not in t:
        t = t.replace("<head>", '<head><meta name="robots" content="noindex, nofollow, noarchive">', 1)
    return t


def proposition_autonome() -> str:
    """La proposition, avec ses captures et ses deux vidéos incorporées : un seul
    clair, un seul chiffré, aucun média de l'étude servi en clair à côté."""
    import base64, mimetypes
    src = SOURCES["proposition"]
    t = src.read_text(encoding="utf-8")
    dossier = src.parent / "assets"
    def data_uri(m):
        p = dossier / m.group(1)
        if not p.exists():
            return m.group(0)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return f'{m.group(0).split("=")[0]}="data:{mime};base64,{base64.b64encode(p.read_bytes()).decode("ascii")}"'
    return re.sub(r'(?:src|poster)="assets/([^"]+)"', data_uri, t)


def decision_scellee() -> str:
    """Le détail de Décision rapide : les captures du configurateur, embarquées en
    data: (jamais servies en clair à leur propre URL), plus le lien vers l'outil en
    ligne. Une page complète (document.write remplace tout le document déchiffré)."""
    import base64
    slides = []
    for nom, legende in [
        ("site-04-decision.jpg", "Décider en six semaines, pas en six mois."),
        ("site-05-configurateur.jpg", "Le configurateur : quatre questions, un dispositif."),
        ("site-06-dispositif.jpg", "Le dispositif recommandé, son calendrier, ses livrables ; chiffrage sous 48 h."),
    ]:
        p = ICI / "shots" / nom
        if not p.exists():
            print(f"   ⚠ capture absente : shots/{nom}", file=sys.stderr)
            continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        slides.append(f'<figure class="slide"><img src="data:image/jpeg;base64,{b64}" alt=""><figcaption>{esc(legende)}</figcaption></figure>')
    slider = ""
    if slides:
        slider = ('<div class="slider" data-slider tabindex="0" aria-label="Écrans du configurateur">'
                   f'<div class="slider-track">{"".join(slides)}</div>'
                   '<div class="slider-bar"><button type="button" class="slider-btn slider-prev" aria-label="Précédent">←</button>'
                   f'<div class="slider-dots"></div><span class="slider-count mono">1 / {len(slides)}</span>'
                   '<button type="button" class="slider-btn slider-next" aria-label="Suivant">→</button></div></div>')
    corps = f"""
<header class="nav"><div class="container nav-inner">
  <a class="nav-logo" href="../index.html#decision"><img src="../assets/acme-noir-h.svg" alt="ACMÉ"></a>
  <nav class="nav-links"><a href="../index.html">← Retour à la page</a></nav>
</div></header>
<section class="section">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">— Décision rapide · déverrouillé</div>
      <h2 class="display">Composer votre dispositif.</h2>
      <p class="lead">Le socle ne bouge pas : cadrage, recrutement, terrain conduit par un consultant senior,
        transcripts intégraux. Les livrables sont en options : plateforme VERBATIM, top lines, analyse complète,
        typologies, atelier de décision.</p>
    </div>
    <div class="split">
      <div class="split-media">{slider}</div>
      <div class="split-texte">
        <div class="lbl">Le configurateur</div>
        <p>Il qualifie votre besoin en quatre questions et renvoie le dispositif recommandé, son calendrier et
          la liste exacte des livrables. Aucun prix n'est affiché à un visiteur : il produit un schéma et un
          calendrier, puis renvoie vers un chiffrage sous 48 heures.</p>
        <div class="actions">
          <a class="btn btn--dark" href="https://vbouin.github.io/acme-site/v5.2/decision-rapide.html" target="_blank" rel="noopener">Composer votre dispositif <span class="ar">→</span></a>
        </div>
        <p class="cap">Outil en ligne, hébergé à part, non indexé.</p>
      </div>
    </div>
  </div>
</section>
<footer class="pied"><div class="container"><span class="mono">Accès protégé · {esc(DATE)}</span></div></footer>
<script src="../assets/hub.js"></script>
"""
    return tete("Décision rapide — le configurateur", "../") + f"<body>{corps}</body></html>"


def donnees(tout: bool) -> None:
    """Ce qui porte de la matière d'étude ou du commercial est chiffré : la
    démonstration (le corpus des 53 entretiens), la proposition (ses captures) et
    le détail de Décision rapide (le configurateur). Avec --tout-chiffre, la page
    elle-même l'est aussi."""
    if not assurer_crypto():
        return
    code = lire_code()
    if SOURCES["demo"].exists():
        clair = demo_neutralisee()
        residus(clair, "démonstration")
        sceller(clair, code, ICI / "demo", "verbatim-nord", "Concept NORD — la démonstration",
                "Le corpus de la démonstration, 53 entretiens anonymisés, est chiffré. Il s'ouvre avec le code transmis "
                "avec ce document, une seule fois par onglet.", eyebrow="— Démonstration", retour="../index.html#verbatim")
    else:
        print(f"   ⚠ source absente : {SOURCES['demo']}", file=sys.stderr)
    if SOURCES["proposition"].exists():
        clair = proposition_autonome()
        residus(clair, "proposition")
        sceller(clair, code, ICI / "proposition", "index", "La proposition détaillée",
                "La proposition et ses captures de la plateforme sont chiffrées. Même code que la démonstration.",
                eyebrow="— Proposition", retour="../index.html#verbatim")
    else:
        print(f"   ⚠ source absente : {SOURCES['proposition']}", file=sys.stderr)
    clair = decision_scellee()
    residus(clair, "décision rapide")
    sceller(clair, code, ICI / "decision", "index", "Décision rapide — le configurateur",
            "Les écrans et le lien du configurateur sont chiffrés. Même code que la démonstration.",
            eyebrow="— Décision rapide", retour="../index.html#decision")
    if tout:
        clair = hub(retourner=True)
        sceller(clair, code, ICI, "index", "ACMÉ — Notre avenir",
                "Ce document est réservé à ses destinataires. Il s'ouvre avec le code qui l'accompagne.",
                prefixe="", eyebrow="— ACMÉ · Notre avenir", retour="")


def reserve() -> None:
    if not assurer_crypto():
        return
    code = lire_code()
    dossier = ICI / "reserve"
    dossier.mkdir(exist_ok=True)
    docs = {
        "index": ("Espace réservé", "Cinq documents qui nomment des clients ou des terrains sous accord de confidentialité.",
                  sous_hub_reserve()),
    }
    if SOURCES["etude"].exists():
        docs["etude"] = ("Étude concurrentielle", "Dossier interne, 23 acteurs. Le document nomme des comptes clients.",
                         charset(SOURCES["etude"].read_text(encoding="utf-8")))
    if SOURCES["recommandations"].exists():
        docs["recommandations"] = ("Recommandations", "Contenus, SEO/GEO et suite à donner. Document interne du 25 août 2026.",
                                   page_doc("ACMÉ — contenus, SEO/GEO et suite à donner", "Document interne · 25 août 2026",
                                            rendre(SOURCES["recommandations"].read_text(encoding="utf-8")),
                                            retour="index.html", prefixe="../"))
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
    ANCRES = {"showroom": "../index.html#showroom"}   # documents avec une carte dédiée sur la page
    for nom, (titre, sous_titre, clair) in docs.items():
        sceller(clair, code, dossier, nom, titre, sous_titre, retour=ANCRES.get(nom, "../index.html"))
    manquants = [cle for cle in ("etude", "recommandations", "adr", "smallvan", "bbr") if not SOURCES[cle].exists()]
    if manquants:
        print(f"   ⚠ sources absentes, document(s) non régénéré(s) : {manquants}", file=sys.stderr)


# ---------------------------------------------------------------- annexes
def annexes() -> None:
    (ICI / "robots.txt").write_text("# Dossier de travail partagé par lien. Ne pas indexer.\nUser-agent: *\nDisallow: /\n", encoding="utf-8")
    (ICI / ".nojekyll").write_text("", encoding="utf-8")
    (ICI / ".gitignore").write_text("\n".join([
        "CODE-ACCES-NE-PAS-PUBLIER.txt", "assets/faces.json", "__pycache__/", ".DS_Store", "_tmp/", "*.log",
        "shots/_hub*",
        # la table de masquage et la liste de contrôle nomment ce qu'elles protègent
        "scenarios.mjs", "_mots-sensibles.txt",
        # les données ne vivent ici que chiffrées (.bin) : jamais de copie en clair
        "proposition/assets/", "demo/*.clair.html",
        # embarquées en data: dans decision/index.bin ; servies en clair à leur URL, elles annuleraient le chiffrement
        "shots/site-04-decision.jpg", "shots/site-05-configurateur.jpg", "shots/site-06-dispositif.jpg", ""
    ]), encoding="utf-8")


def controle_fuites() -> None:
    """Ce qui est publié en clair ne doit nommer aucun client ni terrain.
    La liste des mots vit dans _mots-sensibles.txt (ignoré par git) : la
    publier reviendrait à publier ce qu'elle protège."""
    liste = ICI / "_mots-sensibles.txt"
    if not liste.exists():
        print("   ⚠ _mots-sensibles.txt absent : contrôle de fuite non fait", file=sys.stderr)
        return
    mots = [m.strip() for m in liste.read_text(encoding="utf-8").splitlines() if m.strip() and not m.startswith("#")]
    publics = [p for p in ICI.rglob("*") if p.is_file() and p.suffix in (".html", ".js", ".mjs", ".py", ".md", ".css", ".txt")
               and ".git" not in p.parts and p.name not in ("_mots-sensibles.txt", "scenarios.mjs")]
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
    tout = "--tout-chiffre" in sys.argv or (ICI / "index.bin").exists() and "--en-clair" not in sys.argv
    print("Polices"); fonts_css()
    print("Pages"); protocole()
    if tout:
        print("   · page chiffrée (--en-clair pour revenir à une page lisible)")
    else:
        hub()
        (ICI / "index.bin").unlink(missing_ok=True)
    print("Données chiffrées"); donnees(tout)
    if not sans_reserve:
        print("Espace réservé"); reserve()
    annexes()
    print("Contrôle"); controle_fuites()
    total = sum(p.stat().st_size for p in ICI.rglob("*") if p.is_file() and ".git" not in p.parts)
    print(f"\n→ dossier : {total / 1048576:.1f} Mo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
