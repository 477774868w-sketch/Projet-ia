#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere data/league_priors.csv.

Les couples (total, suprematie) sont des ORDRES DE GRANDEUR pluriannuels,
saisis a la main. Les taux 1X2 ne sont PAS des comptages historiques : ils
sont DEDUITS du modele a partir de (total, suprematie), ce qui garantit la
coherence interne du fichier avec le moteur. A recalibrer sur vos donnees.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
import footyedge as fe  # noqa: E402

# (id, championnat, pays, niveau, genre, total, suprematie, palier_efficience)
L = [
    # ---- Palier 1 : grands championnats masculins -------------------------
    ("ENG1", "Premier League",        "Angleterre",  1, "H", 2.80, 0.28, 1),
    ("ESP1", "LaLiga",                "Espagne",     1, "H", 2.60, 0.30, 1),
    ("ITA1", "Serie A",               "Italie",      1, "H", 2.75, 0.26, 1),
    ("GER1", "Bundesliga",            "Allemagne",   1, "H", 3.10, 0.30, 1),
    ("FRA1", "Ligue 1",               "France",      1, "H", 2.75, 0.28, 1),
    ("UCL",  "Ligue des champions",   "UEFA",        0, "H", 3.10, 0.30, 1),
    ("UEL",  "Ligue Europa",          "UEFA",        0, "H", 2.90, 0.32, 2),
    ("UECL", "Ligue Conference",      "UEFA",        0, "H", 2.95, 0.35, 2),
    # ---- Palier 2 : championnats majeurs suivants -------------------------
    ("NED1", "Eredivisie",            "Pays-Bas",    1, "H", 3.15, 0.35, 2),
    ("POR1", "Liga Portugal",         "Portugal",    1, "H", 2.60, 0.32, 2),
    ("BEL1", "Pro League",            "Belgique",    1, "H", 2.90, 0.30, 2),
    ("TUR1", "Super Lig",             "Turquie",     1, "H", 2.90, 0.32, 2),
    ("ENG2", "Championship",          "Angleterre",  2, "H", 2.60, 0.28, 2),
    ("GER2", "2. Bundesliga",         "Allemagne",   2, "H", 3.00, 0.30, 2),
    ("ITA2", "Serie B",               "Italie",      2, "H", 2.55, 0.28, 2),
    ("USA1", "MLS",                   "Etats-Unis",  1, "H", 3.00, 0.30, 2),
    ("MEX1", "Liga MX",               "Mexique",     1, "H", 2.75, 0.35, 2),
    ("BRA1", "Brasileirao Serie A",   "Bresil",      1, "H", 2.40, 0.35, 2),
    ("SCO1", "Premiership",           "Ecosse",      1, "H", 2.70, 0.28, 2),
    ("SUI1", "Super League",          "Suisse",      1, "H", 3.00, 0.28, 2),
    ("AUT1", "Bundesliga",            "Autriche",    1, "H", 3.00, 0.28, 2),
    ("JPN1", "J1 League",             "Japon",       1, "H", 2.65, 0.25, 2),
    ("ARG1", "Liga Profesional",      "Argentine",   1, "H", 2.30, 0.30, 2),
    # ---- Palier 3 : deuxiemes divisions et championnats moyens -------------
    ("FRA2", "Ligue 2",               "France",      2, "H", 2.30, 0.28, 3),
    ("ESP2", "LaLiga Hypermotion",    "Espagne",     2, "H", 2.30, 0.30, 3),
    ("POR2", "Liga Portugal 2",       "Portugal",    2, "H", 2.45, 0.30, 3),
    ("NED2", "Eerste Divisie",        "Pays-Bas",    2, "H", 3.30, 0.35, 3),
    ("BEL2", "Challenger Pro League", "Belgique",    2, "H", 2.75, 0.30, 3),
    ("TUR2", "1. Lig",                "Turquie",     2, "H", 2.55, 0.32, 3),
    ("ENG3", "League One",            "Angleterre",  3, "H", 2.65, 0.30, 3),
    ("ENG4", "League Two",            "Angleterre",  4, "H", 2.60, 0.30, 3),
    ("SCO2", "Championship",          "Ecosse",      2, "H", 2.70, 0.28, 3),
    ("GRE1", "Super League",          "Grece",       1, "H", 2.45, 0.35, 3),
    ("POL1", "Ekstraklasa",           "Pologne",     1, "H", 2.70, 0.30, 3),
    ("CZE1", "Chance Liga",           "Tchequie",    1, "H", 2.75, 0.30, 3),
    ("CRO1", "HNL",                   "Croatie",     1, "H", 2.65, 0.30, 3),
    ("DEN1", "Superliga",             "Danemark",    1, "H", 2.85, 0.28, 3),
    ("NOR1", "Eliteserien",           "Norvege",     1, "H", 3.00, 0.30, 3),
    ("SWE1", "Allsvenskan",           "Suede",       1, "H", 2.90, 0.28, 3),
    ("KOR1", "K League 1",            "Coree du Sud",1, "H", 2.60, 0.25, 3),
    ("AUS1", "A-League Men",          "Australie",   1, "H", 3.00, 0.28, 3),
    ("SAU1", "Saudi Pro League",      "Arabie S.",   1, "H", 2.90, 0.30, 3),
    ("JPN2", "J2 League",             "Japon",       2, "H", 2.45, 0.25, 3),
    ("BRA2", "Brasileirao Serie B",   "Bresil",      2, "H", 2.25, 0.35, 3),
    ("LIB",  "Copa Libertadores",     "CONMEBOL",    0, "H", 2.45, 0.45, 3),
    # ---- Palier 4 : feminin elite et divisions inferieures -----------------
    ("WENG1", "Women's Super League", "Angleterre",  1, "F", 3.20, 0.25, 4),
    ("WUSA1", "NWSL",                 "Etats-Unis",  1, "F", 2.65, 0.22, 3),
    ("WFRA1", "Premiere Ligue",       "France",      1, "F", 3.40, 0.20, 4),
    ("WGER1", "Frauen-Bundesliga",    "Allemagne",   1, "F", 3.20, 0.22, 4),
    ("WESP1", "Liga F",               "Espagne",     1, "F", 3.40, 0.22, 4),
    ("WITA1", "Serie A Femminile",    "Italie",      1, "F", 3.10, 0.22, 4),
    ("WSWE1", "Damallsvenskan",       "Suede",       1, "F", 3.00, 0.22, 4),
    ("WAUS1", "A-League Women",       "Australie",   1, "F", 3.30, 0.25, 4),
    ("WUCL",  "Women's Champions Lg", "UEFA",        0, "F", 3.60, 0.15, 4),
    ("WENG2", "Women's Championship", "Angleterre",  2, "F", 3.10, 0.25, 4),
]

# Reglages par palier d'efficience du marche
TIER = {
    1: dict(w_market=0.72, min_edge=0.025, kelly=0.25, margin=2.5, shape=""),
    2: dict(w_market=0.60, min_edge=0.030, kelly=0.22, margin=3.5, shape=""),
    3: dict(w_market=0.48, min_edge=0.040, kelly=0.18, margin=5.0, shape=14),
    4: dict(w_market=0.35, min_edge=0.055, kelly=0.13, margin=7.5, shape=10),
}


def rho_for(total, gender):
    if gender == "F":
        return -0.03          # moins de nuls, dispersion des niveaux plus forte
    if total < 2.45:
        return -0.07          # championnats a faible total : effet DC plus marque
    if total > 3.05:
        return -0.03
    return -0.05


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "data", "league_priors.csv")
    rows = []
    for lid, name, country, tier, gender, T, S, eff in L:
        rho = rho_for(T, gender)
        g = fe.ScoreGrid.from_lambdas((T + S) / 2, (T - S) / 2, rho)
        h, d, a = g.result_probs()
        cfg = TIER[eff]
        rows.append({
            "league_id": lid, "league": name, "country": country,
            "tier": tier, "gender": gender,
            "goals_per_game": round(T, 2),
            "home_supremacy": round(S, 2),
            "home_adv_log": round(fe.math.log(((T + S) / 2) / ((T - S) / 2)) / 2, 3),
            "rho": rho,
            "p_home": round(h, 3), "p_draw": round(d, 3), "p_away": round(a, 3),
            "p_over25": round(g.over_under(2.5)["over"]["win"], 3),
            "p_btts": round(g.btts()["yes"], 3),
            "efficiency_tier": eff,
            "typical_margin_1x2_pct": cfg["margin"],
            "w_market_default": cfg["w_market"],
            "min_edge": cfg["min_edge"],
            "kelly_fraction": cfg["kelly"],
            "nb_shape": cfg["shape"],
        })
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("%d championnats -> %s" % (len(rows), os.path.normpath(out)))
    return rows


if __name__ == "__main__":
    main()
