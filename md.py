#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown → HTML, sans dépendance. Couvre ce que les documents du dossier
emploient : titres, paragraphes, listes (un niveau d'imbrication), tableaux,
citations, blocs de code, filets, gras, italique, code en ligne, liens.

    from md import rendre
    html = rendre(texte_markdown)
"""
from __future__ import annotations
import html as _html
import re


def _inline(s: str) -> str:
    # Les entités déjà écrites (&nbsp;) sont conservées ; le reste est échappé.
    s = _html.escape(s, quote=False).replace("&amp;nbsp;", "&nbsp;")
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def _tableau(lignes: list[str]) -> str:
    rangs = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lignes]
    if len(rangs) >= 2 and all(re.fullmatch(r":?-{2,}:?", c) for c in rangs[1]):
        tete, corps = rangs[0], rangs[2:]
    else:
        tete, corps = None, rangs
    out = ["<table>"]
    if tete:
        out.append("<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in tete) + "</tr></thead>")
    out.append("<tbody>")
    for r in corps:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def rendre(texte: str) -> str:
    lignes = texte.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    para: list[str] = []

    def vider_para():
        if para:
            out.append("<p>" + _inline(" ".join(x.strip() for x in para)) + "</p>")
            para.clear()

    while i < len(lignes):
        l = lignes[i]
        s = l.strip()

        if s.startswith("```"):
            vider_para()
            j = i + 1
            bloc = []
            while j < len(lignes) and not lignes[j].strip().startswith("```"):
                bloc.append(lignes[j])
                j += 1
            out.append("<pre>" + _html.escape("\n".join(bloc)) + "</pre>")
            i = j + 1
            continue

        if not s:
            vider_para()
            i += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}", s):
            vider_para()
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            vider_para()
            n = len(m.group(1))
            titre = m.group(2).strip()
            ancre = re.sub(r"[^a-z0-9]+", "-", titre.lower()).strip("-")
            out.append(f'<h{n} id="{ancre}">{_inline(titre)}</h{n}>')
            i += 1
            continue

        if s.startswith("|"):
            vider_para()
            j = i
            while j < len(lignes) and lignes[j].strip().startswith("|"):
                j += 1
            out.append(_tableau(lignes[i:j]))
            i = j
            continue

        if s.startswith(">"):
            vider_para()
            j = i
            cit = []
            while j < len(lignes) and lignes[j].strip().startswith(">"):
                cit.append(lignes[j].strip()[1:].strip())
                j += 1
            out.append("<blockquote>" + rendre("\n".join(cit)) + "</blockquote>")
            i = j
            continue

        m = re.match(r"^(\s*)([-*]|\d+[.)])\s+(.*)$", l)
        if m:
            vider_para()
            j = i
            items: list[tuple[int, bool, str]] = []   # (indentation, ordonné, texte)
            while j < len(lignes):
                mm = re.match(r"^(\s*)([-*]|\d+[.)])\s+(.*)$", lignes[j])
                if mm:
                    items.append((len(mm.group(1)), mm.group(2)[0].isdigit(), mm.group(3)))
                    j += 1
                elif lignes[j].strip() and lignes[j].startswith("  ") and items:
                    ind, o, t = items[-1]
                    items[-1] = (ind, o, t + " " + lignes[j].strip())
                    j += 1
                else:
                    break
            # Deux niveaux : la racine et ce qui est indenté.
            base = min(x[0] for x in items)
            balise = "ol" if items[0][1] else "ul"
            out.append(f"<{balise}>")
            ouvert = None
            for ind, o, t in items:
                if ind > base:
                    if ouvert is None:
                        ouvert = "ol" if o else "ul"
                        out[-1] = out[-1][:-5] if out[-1].endswith("</li>") else out[-1]
                        out.append(f"<{ouvert}>")
                    out.append(f"<li>{_inline(t)}</li>")
                else:
                    if ouvert:
                        out.append(f"</{ouvert}></li>")
                        ouvert = None
                    out.append(f"<li>{_inline(t)}</li>")
            if ouvert:
                out.append(f"</{ouvert}></li>")
            out.append(f"</{balise}>")
            i = j
            continue

        para.append(l)
        i += 1

    vider_para()
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    print(rendre(open(sys.argv[1], encoding="utf-8").read()))
