#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vignettes des livrables, prises avec Chrome sans interface.

    python3 shoot.py            # toutes
    python3 shoot.py pitch demo # certaines

Chaque prise sert le dossier de la page depuis un petit serveur local (les pages
chargent des ressources relatives), ouvre la page dans une fenêtre haute pour
avoir la page entière, puis découpe la zone demandée et l'enregistre en JPEG
dans shots/. Une page dont on ne veut que le haut se découpe à `haut` pixels.

Les captures de documents réservés (étude concurrentielle, ADR) ne montrent que
leur en-tête : ce sont des vignettes, pas des copies.
"""
from __future__ import annotations
import http.server, shutil, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path

ICI = Path(__file__).resolve().parent
CLAUDE = ICI.parent
SHOTS = ICI / "shots"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LARGEUR_SORTIE = 1200          # px — affichée à ~600 px, donc 2× logique

# nom → (dossier servi, page, largeur fenêtre, hauteur fenêtre, zone (y0, y1) à garder)
PRISES = {
    "pitch":        (ICI / "pitch", "index.html", 1400, 900, (0, 900)),
    "pitch-livrables": (ICI / "pitch", "index.html#livrables", 1400, 900, (0, 900)),
    "proposition":  (ICI / "proposition", "index.html", 1400, 900, (0, 900)),
    "demo":         (ICI / "demo", "verbatim-nord.html", 1400, 900, (0, 900)),
    "semantique":   (ICI / "demo", "champs-semantiques.html", 1400, 900, (0, 900)),
    "protocole":    (ICI / "protocole", "index.html", 1400, 900, (0, 900)),
    "site":         (CLAUDE / "acme-site" / "v5.2", "index.html", 1400, 900, (0, 900)),
    "decision":     (CLAUDE / "acme-site" / "v5.2", "decision-rapide.html", 1400, 900, (0, 900)),
    "contenus":     (CLAUDE / "acme-site" / "v5.2", "contenus.html", 1400, 900, (0, 900)),
    "etude":        (CLAUDE / "acme-etude-concurrentielle", "etude-concurrentielle.html", 1400, 900, (0, 900)),
    "adr":          (CLAUDE / "acme-ai-interviews", "etude-technique.html", 1400, 900, (0, 900)),
    "smallvan":     (CLAUDE, "Small-Van-Histoire-Digitale-PARTAGE.html", 1400, 900, (0, 900)),
    "reserve":      (ICI / "reserve", "index.html", 1400, 900, (0, 900)),
    # contrôle visuel du hub lui-même (pas des vignettes publiées)
    "hub":          (ICI, "index.html", 1400, 900, (0, 900)),
    "hub-cinq":     (ICI, "index.html#cinq-minutes", 1400, 1100, (0, 1100)),
    "hub-livrables": (ICI, "index.html#livrables", 1400, 1100, (0, 1100)),
    "hub-poc":      (ICI, "index.html#l-poc", 1400, 1000, (0, 1000)),
    "hub-reserve":  (ICI, "index.html#reserve", 1400, 1000, (0, 1000)),
    "hub-trancher": (ICI, "index.html#trancher", 1400, 1100, (0, 1100)),
    "hub-mobile":   (ICI, "index.html#livrables", 390, 1400, (0, 1400)),
}


def servir(dossier: Path):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(dossier), **k)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def capturer(nom: str) -> bool:
    dossier, page, w, h, (y0, y1) = PRISES[nom]
    fichier = dossier / page.split("#")[0]
    if not fichier.exists():
        print(f"   ✗ {nom:<16} source absente : {fichier}")
        return False
    # Les exports d'artefacts commencent par <title> sans déclaration d'encodage :
    # Chrome les lirait en latin-1 et casserait tous les accents. On sert alors
    # une copie qui déclare l'UTF-8 en tête.
    temporaire = None
    texte = fichier.read_bytes()[:4096].decode("utf-8", errors="ignore").lower()
    if "<meta charset" not in texte and "charset=" not in texte:
        temporaire = Path(tempfile.mkdtemp(prefix="shoot-copie-"))
        for f in dossier.iterdir():
            if f.is_file() and f.suffix.lower() in (".html", ".css", ".js", ".svg", ".png", ".jpg", ".webp", ".mp4"):
                shutil.copy2(f, temporaire / f.name)
        (temporaire / fichier.name).write_text('<meta charset="utf-8">\n' + fichier.read_text(encoding="utf-8"), encoding="utf-8")
        dossier = temporaire
    httpd, port = servir(dossier)
    profil = Path(tempfile.mkdtemp(prefix="shoot-chrome-"))
    brut = Path(tempfile.mkdtemp(prefix="shoot-")) / f"{nom}.png"
    url = f"http://127.0.0.1:{port}/{page}"
    try:
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
             "--autoplay-policy=no-user-gesture-required",
             f"--user-data-dir={profil}", f"--window-size={w},{h}",
             "--force-device-scale-factor=1", "--virtual-time-budget=12000",
             f"--screenshot={brut}", url],
            capture_output=True, timeout=150)
    except subprocess.TimeoutExpired:
        pass
    finally:
        httpd.shutdown()
        shutil.rmtree(profil, ignore_errors=True)
        if temporaire:
            shutil.rmtree(temporaire, ignore_errors=True)
    if not brut.exists():
        print(f"   ✗ {nom:<16} Chrome n'a rien rendu")
        return False
    # Découpe + redimensionnement + JPEG en une passe ffmpeg (pas de PIL ici).
    SHOTS.mkdir(exist_ok=True)
    cible = SHOTS / f"{nom}.jpg"
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(brut),
         "-vf", f"crop=iw:min(ih\\,{y1 - y0}):0:{y0},scale={LARGEUR_SORTIE}:-2:flags=lanczos",
         "-q:v", "4", str(cible)], capture_output=True, text=True)
    shutil.rmtree(brut.parent, ignore_errors=True)
    if r.returncode or not cible.exists():
        print(f"   ✗ {nom:<16} ffmpeg : {r.stderr.strip()[:120]}")
        return False
    print(f"   ✓ {nom:<16} {cible.stat().st_size // 1024:>4} Ko")
    return True


def main() -> int:
    voulues = sys.argv[1:] or list(PRISES)
    inconnues = [v for v in voulues if v not in PRISES]
    if inconnues:
        print(f"✗ prises inconnues : {inconnues}", file=sys.stderr)
        return 1
    faites = sum(capturer(v) for v in voulues)
    print(f"\n→ {faites}/{len(voulues)} vignettes dans {SHOTS}")
    return 0 if faites == len(voulues) else 1


if __name__ == "__main__":
    raise SystemExit(main())
