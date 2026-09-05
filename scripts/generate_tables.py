#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere les tables chiffrees inserees dans sources/.

Chaque table de la base de connaissances est PRODUITE PAR LE MOTEUR, jamais
saisie a la main. `scripts/audit.py` regenere ces tables et verifie qu'elles
figurent telles quelles dans les documents : une divergence entre le code et
la documentation devient donc une erreur detectable.

Usage :
    python3 scripts/generate_tables.py            # affiche toutes les tables
    python3 scripts/generate_tables.py --name A   # une seule table
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "engine"))
import footyedge as fe  # noqa: E402

RHO = -0.04
SUPS = [-1.50, -1.25, -1.00, -0.75, -0.50, -0.25, 0.00,
        0.25, 0.50, 0.75, 1.00, 1.25, 1.50]
TOTS = [2.00, 2.25, 2.50, 2.75, 3.00, 3.25, 3.50]


def table_A():
    out = ["### Table A — 1X2 en fonction du total et de la suprématie (ρ = −0,04)", "",
           "Lecture : ligne = total attendu de buts, colonne = suprématie (λ_dom − λ_ext).",
           "Chaque cellule : **P(1) / P(X) / P(2)** en %.", "",
           "| Total \\ Supr. | " + " | ".join("%+.2f" % s for s in SUPS) + " |",
           "|" + "---|" * (len(SUPS) + 1)]
    for T in TOTS:
        cells = []
        for s in SUPS:
            lh, la = (T + s) / 2, (T - s) / 2
            if la <= 0.05 or lh <= 0.05:
                cells.append("—")
                continue
            h, d, a = fe.ScoreGrid.from_lambdas(lh, la, RHO).result_probs()
            cells.append("%.0f/%.0f/%.0f" % (100 * h, 100 * d, 100 * a))
        out.append("| **%.2f** | " % T + " | ".join(cells) + " |")
    return "\n".join(out)


def table_B():
    out = ["### Table B — Totaux (exacts pour des marginales de Poisson indépendantes)", "",
           "| Total λ | P(+0,5) | P(+1,5) | P(+2,5) | P(+3,5) | P(+4,5) |",
           "|---|---|---|---|---|---|"]
    for T in [1.75, 2.00, 2.25, 2.50, 2.75, 3.00, 3.25, 3.50, 3.75, 4.00]:
        g = fe.ScoreGrid.from_lambdas(T / 2, T / 2, 0.0)
        row = [g.over_under(l)["over"]["win"] for l in (0.5, 1.5, 2.5, 3.5, 4.5)]
        out.append("| %.2f | " % T + " | ".join("%.1f%%" % (100 * x) for x in row) + " |")
    return "\n".join(out)


def table_C():
    cols = [0.0, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50]
    out = ["### Table C — BTTS « oui » selon total et suprématie", "",
           "| Total \\ Supr. | 0,00 | 0,25 | 0,50 | 0,75 | 1,00 | 1,25 | 1,50 |",
           "|---|---|---|---|---|---|---|---|"]
    for T in TOTS:
        cells = []
        for s in cols:
            lh, la = (T + s) / 2, (T - s) / 2
            if la <= 0.05:
                cells.append("—")
                continue
            cells.append("%.1f%%" % (100 * fe.ScoreGrid.from_lambdas(lh, la, RHO).btts()["yes"]))
        out.append("| **%.2f** | " % T + " | ".join(cells) + " |")
    return "\n".join(out)


def table_D():
    out = ["### Table D — Ligne de handicap asiatique équitable selon la suprématie", "",
           "Ligne pour laquelle les deux camps valent 2,00 (probabilité hors remboursement = 50 %).",
           "Total fixé à 2,60 ; la ligne équitable dépend peu du total.", "",
           "| Suprématie | Ligne AH équitable (dom.) | P(1) | P(X) | P(2) |",
           "|---|---|---|---|---|"]
    for s in [0.00, 0.15, 0.30, 0.45, 0.60, 0.80, 1.00, 1.25, 1.50]:
        T = 2.60
        g = fe.ScoreGrid.from_lambdas((T + s) / 2, (T - s) / 2, RHO)
        best, bd, x = None, 9, -2.0
        while x <= 2.0001:
            p = g.asian_handicap(round(x, 2))["home"]["prob_norm"]
            if abs(p - 0.5) < bd:
                bd, best = abs(p - 0.5), round(x, 2)
            x += 0.25
        h, d, a = g.result_probs()
        out.append("| %+.2f | %+.2f | %.1f%% | %.1f%% | %.1f%% |"
                   % (s, best, 100 * h, 100 * d, 100 * a))
    return "\n".join(out)


def table_devig():
    names = {"multiplicative": "Multiplicatif", "additive": "Additif",
             "power": "Puissance", "odds_ratio": "Odds-ratio", "shin": "**Shin**"}
    cases = [("Match équilibré, marge serrée", [2.60, 3.30, 2.80]),
             ("Gros favori (biais maximal)", [1.18, 7.50, 15.00]),
             ("Marché mou, marge 9 %", [2.30, 3.30, 3.05])]
    out = []
    for title, o in cases:
        dv = fe.devig(o)
        out.append("**%s** — cotes %s, marge **%.2f %%**\n"
                   % (title, " / ".join("%.2f" % x for x in o), dv["margin_pct"]))
        out.append("| Méthode | P(1) | P(X) | P(2) | Cote juste 1 | Cote juste 2 |")
        out.append("|---|---|---|---|---|---|")
        for m in fe.DEVIG_METHODS:
            p = dv["all_methods"][m]
            out.append("| %s | %.2f%% | %.2f%% | %.2f%% | %.3f | %.3f |"
                       % (names[m], 100 * p[0], 100 * p[1], 100 * p[2],
                          1 / p[0], 1 / p[2]))
        out.append("\nÉcart max entre méthodes : **%.2f point de %%** (z de Shin = %.4f)\n"
                   % (100 * max(dv["method_spread"]), dv["shin_z"]))
    return "\n".join(out).strip()


def table_dispersion():
    lh, la = 3.40, 0.55
    gp = fe.ScoreGrid.from_lambdas(lh, la, -0.03)
    gn = fe.ScoreGrid.from_lambdas(lh, la, -0.03, shape_home=10, shape_away=10)
    rows = [
        ("Plus de 3,5 buts", lambda g: g.over_under(3.5)["over"]["win"]),
        ("Plus de 5,5 buts", lambda g: g.over_under(5.5)["over"]["win"]),
        ("Domicile marque 5 buts ou plus",
         lambda g: sum(p for k, p in g.team_dist("home").items() if k >= 5)),
        ("Handicap -3,5 domicile", lambda g: g.asian_handicap(-3.5)["home"]["win"]),
        ("Nul", lambda g: g.result_probs()[1]),
        ("Extérieur gagne", lambda g: g.result_probs()[2]),
        ("Clean sheet domicile", lambda g: g.clean_sheet("home")),
    ]
    out = ["| Marché | Poisson | Bin. nég. `shape=10` | Écart |", "|---|---|---|---|"]
    for name, f in rows:
        a, b = f(gp), f(gn)
        out.append("| %s | %.1f%% | %.1f%% | %+.1f pt |"
                   % (name, 100 * a, 100 * b, 100 * (b - a)))
    return "\n".join(out)


def table_parlay():
    g = fe.ScoreGrid.from_lambdas(1.85, 0.95, -0.05)
    combos = [
        ("Domicile gagne + plus de 2,5 buts", lambda h, a: h > a, lambda h, a: h + a > 2.5),
        ("Domicile gagne + moins de 2,5 buts", lambda h, a: h > a, lambda h, a: h + a < 2.5),
        ("Domicile gagne + BTTS oui", lambda h, a: h > a, lambda h, a: h > 0 and a > 0),
        ("Domicile gagne + BTTS non", lambda h, a: h > a, lambda h, a: h == 0 or a == 0),
        ("Nul + moins de 2,5 buts", lambda h, a: h == a, lambda h, a: h + a < 2.5),
        ("Plus de 2,5 buts + BTTS oui", lambda h, a: h + a > 2.5, lambda h, a: h > 0 and a > 0),
    ]
    tot = lambda f: sum(g.m[i][j] for i in range(g.n + 1)
                        for j in range(g.n + 1) if f(i, j))
    out = ["Match de référence : λ = 1,85 − 0,95 (ρ = −0,05).", "",
           "| Combinaison sur le MÊME match | Naïf (produit) | Réel (grille) | "
           "Écart relatif | Cote juste naïve | Cote juste réelle |",
           "|---|---|---|---|---|---|"]
    for name, f1, f2 in combos:
        naive = tot(f1) * tot(f2)
        real = tot(lambda h, a, f1=f1, f2=f2: f1(h, a) and f2(h, a))
        out.append("| %s | %.1f%% | %.1f%% | %+.0f%% | %.2f | %.2f |"
                   % (name, 100 * naive, 100 * real,
                      100 * (real - naive) / naive, 1 / naive, 1 / real))
    return "\n".join(out)


def table_kelly():
    def sim(p_true, p_believed, odds, c, n_bets=1000, n_sims=4000, seed=1):
        rng = random.Random(seed)
        f = c * max((p_believed * odds - 1.0) / (odds - 1.0), 0.0)
        dds, finals = [], []
        for _ in range(n_sims):
            b, peak, mdd = 1.0, 1.0, 0.0
            for _ in range(n_bets):
                b *= (1 + f * (odds - 1)) if rng.random() < p_true else (1 - f)
                peak = max(peak, b)
                mdd = max(mdd, (peak - b) / peak)
                if b < 0.02:
                    break
            dds.append(mdd)
            finals.append(b)
        dds.sort()
        finals.sort()
        q = lambda v, x: v[int(x * len(v))]
        return dict(f=f, med=q(finals, 0.5), p10=q(finals, 0.10),
                    dd50=q(dds, 0.5), dd95=q(dds, 0.95),
                    p_dd30=sum(1 for d in dds if d > 0.30) / len(dds),
                    p_dd50=sum(1 for d in dds if d > 0.50) / len(dds))

    F = [(1.0, "Kelly plein"), (0.5, "1/2 Kelly"),
         (0.25, "**1/4 Kelly**"), (0.125, "1/8 Kelly")]
    hdr = ("| Fraction | Mise | Médiane finale | 1er décile | Drawdown médian | "
           "Drawdown 95e c. | P(perte > 30 %) | P(perte > 50 %) |")
    sep = "|---|---|---|---|---|---|---|---|"
    out = ["**Hypothèses** : 1 000 paris successifs à cote 2,00, mise = fraction "
           "de Kelly, banque réinvestie.", "",
           "### Cas A — l'estimation est juste (avantage réel 3,0 %, p = 0,515)", "",
           hdr, sep]
    for c, lab in F:
        r = sim(0.515, 0.515, 2.0, c)
        out.append("| %s | %.2f%% | ×%.2f | ×%.2f | %.0f%% | %.0f%% | %.0f%% | %.0f%% |"
                   % (lab, 100 * r['f'], r['med'], r['p10'], 100 * r['dd50'],
                      100 * r['dd95'], 100 * r['p_dd30'], 100 * r['p_dd50']))
    out += ["", "### Cas B — l'avantage a été surestimé de moitié "
            "(on croit 3,0 %, il vaut 1,5 %)", "", hdr, sep]
    for c, lab in F:
        r = sim(0.5075, 0.515, 2.0, c, seed=2)
        out.append("| %s | %.2f%% | ×%.2f | ×%.2f | %.0f%% | %.0f%% | %.0f%% | %.0f%% |"
                   % (lab, 100 * r['f'], r['med'], r['p10'], 100 * r['dd50'],
                      100 * r['dd95'], 100 * r['p_dd30'], 100 * r['p_dd50']))
    out += ["", "### Cas C — il n'y avait aucun avantage (p réel = 0,50, marge payée)", "",
            "| Fraction | Médiane finale | 1er décile | Drawdown médian | P(perte > 50 %) |",
            "|---|---|---|---|---|"]
    for c, lab in F:
        r = sim(0.50, 0.515, 2.0, c, seed=3)
        out.append("| %s | ×%.2f | ×%.2f | %.0f%% | %.0f%% |"
                   % (lab, r['med'], r['p10'], 100 * r['dd50'], 100 * r['p_dd50']))
    return "\n".join(out)


TABLES = {
    "A": (table_A, "sources/02_MOTEUR_QUANTITATIF.md"),
    "B": (table_B, "sources/02_MOTEUR_QUANTITATIF.md"),
    "C": (table_C, "sources/02_MOTEUR_QUANTITATIF.md"),
    "D": (table_D, "sources/02_MOTEUR_QUANTITATIF.md"),
    "devig": (table_devig, "sources/03_MARCHE_DEVIG_CLV.md"),
    "kelly": (table_kelly, "sources/07_STAKING_RISQUE.md"),
    "dispersion": (table_dispersion, "sources/05_D2_ET_FEMININ.md"),
    "parlay": (table_parlay, "sources/09_MARCHES_FORMULES.md"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", choices=sorted(TABLES))
    a = ap.parse_args()
    for name in ([a.name] if a.name else sorted(TABLES)):
        fn, dest = TABLES[name]
        print("<!-- table %s -> %s -->" % (name, dest))
        print(fn())
        print()


if __name__ == "__main__":
    main()
