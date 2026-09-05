#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FootyEdge — moteur quantitatif de pronostic football.

Zero dependance externe (stdlib uniquement) : concu pour tourner dans
n'importe quel interpreteur Python 3.8+, y compris l'outil d'execution de
code d'un assistant IA.

Contenu
-------
1.  Utilitaires numeriques (log-sum-exp, Poisson / binomiale negative,
    recherche de racine, optimiseur Adam).
2.  Grille de scores : Poisson bivarie avec correction Dixon-Coles,
    marginales optionnellement sur-dispersees (binomiale negative).
3.  Tarification de TOUS les marches derives de la grille
    (1X2, DC, AH, O/U, BTTS, totaux equipe, scores exacts, MT/FT, marge...).
4.  Retrait de marge bookmaker ("devig") : multiplicatif, additif,
    puissance, odds-ratio, Shin.
5.  Inversion de marche : cotes asiatiques / 1X2 -> (lambda_dom, lambda_ext).
6.  Fusion modele <-> marche par pooling log-lineaire.
7.  Estimation des forces d'equipes : Dixon-Coles pondere dans le temps
    (max de vraisemblance, gradient analytique) + Elo a buts.
8.  Mise : Kelly simple, Kelly multi-issues exclusives, Kelly portefeuille,
    decote d'incertitude.
9.  Metriques de calibration : Brier, log-loss, RPS, ECE, CLV.
10. Simulation Monte-Carlo : fin de saison, combines correles.
11. Backtest walk-forward.
12. CLI + auto-test (`python3 footyedge.py selftest`).

Licence : usage prive. Aucune garantie. Le pari sportif comporte un risque
de perte en capital ; ce logiciel produit des probabilites, pas des certitudes.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

__version__ = "1.0.0"

# --------------------------------------------------------------------------
# 0. Constantes globales
# --------------------------------------------------------------------------

MAX_GOALS = 12          # taille de la grille de scores (0..MAX_GOALS)
EPS = 1e-12
DEFAULT_H1_SHARE = 0.455  # part des buts inscrits en 1re mi-temps (prior)


# --------------------------------------------------------------------------
# 1. Utilitaires numeriques
# --------------------------------------------------------------------------

def _clip(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def safe_log(x):
    return math.log(x) if x > EPS else math.log(EPS)


def logsumexp(values):
    if not values:
        return float("-inf")
    m = max(values)
    if m == float("-inf"):
        return float("-inf")
    return m + math.log(sum(math.exp(v - m) for v in values))


def poisson_pmf(k, lam):
    """P(X=k) pour X ~ Poisson(lam), calcul en log pour la stabilite."""
    if k < 0:
        return 0.0
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(k * math.log(lam) - lam - math.lgamma(k + 1.0))


def nbinom_pmf(k, mean, shape):
    """
    Binomiale negative parametree par (moyenne, forme).

    Variance = mean + mean^2 / shape. shape -> +inf redonne Poisson.
    Utile pour les championnats a forte sur-dispersion (D2, feminin).
    """
    if k < 0:
        return 0.0
    if shape is None or shape > 1e6:
        return poisson_pmf(k, mean)
    if mean <= 0:
        return 1.0 if k == 0 else 0.0
    r = float(shape)
    p = r / (r + mean)                       # P(succes)
    log_p = (math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1.0)
             + r * math.log(p) + k * math.log(1.0 - p))
    return math.exp(log_p)


def goal_pmf_vector(mean, shape=None, max_goals=MAX_GOALS):
    """Vecteur [P(0), ..., P(max_goals)] renormalise a 1."""
    if shape is None or shape > 1e6:
        vec = [poisson_pmf(k, mean) for k in range(max_goals + 1)]
    else:
        vec = [nbinom_pmf(k, mean, shape) for k in range(max_goals + 1)]
    s = sum(vec)
    if s <= 0:
        vec = [1.0] + [0.0] * max_goals
        s = 1.0
    return [v / s for v in vec]


def bisect(f, lo, hi, tol=1e-10, max_iter=200):
    """Recherche de racine par dichotomie ; renvoie None si pas d'encadrement."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if fhi == 0:
        return hi
    if flo * fhi > 0:
        return None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if abs(fmid) < tol or (hi - lo) < tol:
            return mid
        if flo * fmid < 0:
            hi, fhi = mid, fmid
        else:
            lo, flo = mid, fmid
    return 0.5 * (lo + hi)


def golden_section_max(f, lo, hi, tol=1e-7, max_iter=200):
    """Maximisation unidimensionnelle d'une fonction unimodale."""
    invphi = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c = b - invphi * (b - a)
    d = a + invphi * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(max_iter):
        if (b - a) < tol:
            break
        if fc > fd:
            b, d, fd = d, c, fc
            c = b - invphi * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + invphi * (b - a)
            fd = f(d)
    return 0.5 * (a + b)


class Adam:
    """Optimiseur Adam minimal, sur listes de flottants."""

    def __init__(self, n, lr=0.05, b1=0.9, b2=0.999, eps=1e-8):
        self.lr, self.b1, self.b2, self.eps = lr, b1, b2, eps
        self.m = [0.0] * n
        self.v = [0.0] * n
        self.t = 0

    def step(self, params, grads):
        """Ascension de gradient (on maximise) : params += lr * m_hat / ..."""
        self.t += 1
        b1t = 1.0 - self.b1 ** self.t
        b2t = 1.0 - self.b2 ** self.t
        for i, g in enumerate(grads):
            self.m[i] = self.b1 * self.m[i] + (1 - self.b1) * g
            self.v[i] = self.b2 * self.v[i] + (1 - self.b2) * g * g
            mh = self.m[i] / b1t
            vh = self.v[i] / b2t
            params[i] += self.lr * mh / (math.sqrt(vh) + self.eps)
        return params


# --------------------------------------------------------------------------
# 2. Grille de scores (Poisson bivarie + correction Dixon-Coles)
# --------------------------------------------------------------------------

def dixon_coles_tau(i, j, lam_h, lam_a, rho):
    """
    Correction Dixon-Coles (1997) sur les quatre scores bas.

    Corrige la sous-estimation des 0-0 / 1-1 et la sur-estimation des 1-0 / 0-1
    produite par l'hypothese d'independance des marginales de Poisson.
    """
    if rho == 0.0:
        return 1.0
    if i == 0 and j == 0:
        return 1.0 - lam_h * lam_a * rho
    if i == 0 and j == 1:
        return 1.0 + lam_h * rho
    if i == 1 and j == 0:
        return 1.0 + lam_a * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def rho_bounds(lam_h, lam_a):
    """Intervalle de rho garantissant tau > 0 pour les quatre cellules."""
    hi = min(1.0 / max(lam_h, EPS), 1.0 / max(lam_a, EPS), 1.0)
    lo = -1.0 / max(lam_h * lam_a, EPS)
    lo = max(lo, -1.0)
    return lo * 0.98, hi * 0.98


class ScoreGrid:
    """
    Distribution jointe des scores (buts domicile x buts exterieur).

    Toute la tarification decoule de cet objet : un seul modele probabiliste
    coherent alimente 1X2, handicaps, totaux, BTTS, scores exacts, etc.
    Impossible d'avoir des prix contradictoires entre marches.
    """

    __slots__ = ("m", "n", "lam_h", "lam_a", "rho", "meta")

    def __init__(self, matrix, lam_h=None, lam_a=None, rho=0.0, meta=None):
        self.m = matrix
        self.n = len(matrix) - 1
        self.lam_h = lam_h
        self.lam_a = lam_a
        self.rho = rho
        self.meta = meta or {}

    # ---------------------------------------------------------------- build
    @staticmethod
    def from_lambdas(lam_h, lam_a, rho=0.0, max_goals=MAX_GOALS,
                     shape_home=None, shape_away=None):
        lam_h = max(float(lam_h), 1e-6)
        lam_a = max(float(lam_a), 1e-6)
        lo, hi = rho_bounds(lam_h, lam_a)
        rho = _clip(float(rho), lo, hi)
        ph = goal_pmf_vector(lam_h, shape_home, max_goals)
        pa = goal_pmf_vector(lam_a, shape_away, max_goals)
        matrix = [[0.0] * (max_goals + 1) for _ in range(max_goals + 1)]
        total = 0.0
        for i in range(max_goals + 1):
            phi = ph[i]
            if phi <= 0.0:
                continue
            for j in range(max_goals + 1):
                v = phi * pa[j] * dixon_coles_tau(i, j, lam_h, lam_a, rho)
                if v < 0.0:
                    v = 0.0
                matrix[i][j] = v
                total += v
        if total <= 0:
            raise ValueError("grille degeneree")
        for i in range(max_goals + 1):
            row = matrix[i]
            for j in range(max_goals + 1):
                row[j] /= total
        return ScoreGrid(matrix, lam_h, lam_a, rho)

    # ------------------------------------------------------------ marginales
    def margin_dist(self):
        """Distribution de (buts domicile - buts exterieur)."""
        d = defaultdict(float)
        for i, row in enumerate(self.m):
            for j, p in enumerate(row):
                if p:
                    d[i - j] += p
        return dict(d)

    def total_dist(self):
        """Distribution du nombre total de buts."""
        d = defaultdict(float)
        for i, row in enumerate(self.m):
            for j, p in enumerate(row):
                if p:
                    d[i + j] += p
        return dict(d)

    def team_dist(self, side):
        d = defaultdict(float)
        for i, row in enumerate(self.m):
            for j, p in enumerate(row):
                if p:
                    d[i if side == "home" else j] += p
        return dict(d)

    def expected_goals(self):
        """Esperance de buts effective de la grille (post-correction DC)."""
        eh = sum(g * p for g, p in self.team_dist("home").items())
        ea = sum(g * p for g, p in self.team_dist("away").items())
        return eh, ea

    # --------------------------------------------------------------- marches
    def result_probs(self):
        """(P(1), P(X), P(2))."""
        h = d = a = 0.0
        for i, row in enumerate(self.m):
            for j, p in enumerate(row):
                if not p:
                    continue
                if i > j:
                    h += p
                elif i == j:
                    d += p
                else:
                    a += p
        return h, d, a

    def double_chance(self):
        h, d, a = self.result_probs()
        return {"1X": h + d, "12": h + a, "X2": d + a}

    def draw_no_bet(self):
        h, d, a = self.result_probs()
        den = h + a
        if den <= 0:
            return {"home": 0.5, "away": 0.5}
        return {"home": h / den, "away": a / den}

    def over_under(self, line):
        over = line_probs(self.total_dist(), line, +1)
        under = line_probs(self.total_dist(), line, -1)
        return {"over": _wpl(over), "under": _wpl(under)}

    def asian_handicap(self, line):
        """
        `line` s'applique a l'equipe a domicile (ex : -0.75).
        L'exterieur recoit donc -line. Les deux cotes partagent le meme seuil
        (-line) sur la marge, seul le sens de comparaison change :
          domicile gagne si marge > -line ; exterieur gagne si marge < -line.
        """
        md = self.margin_dist()
        home = line_probs(md, -line, +1)
        away = line_probs(md, -line, -1)
        return {"home": _wpl(home), "away": _wpl(away)}

    def btts(self):
        yes = 0.0
        for i, row in enumerate(self.m):
            if i == 0:
                continue
            yes += sum(row[1:])
        return {"yes": yes, "no": 1.0 - yes}

    def team_total(self, side, line):
        d = self.team_dist(side)
        return {"over": _wpl(line_probs(d, line, +1)),
                "under": _wpl(line_probs(d, line, -1))}

    def clean_sheet(self, side):
        """Probabilite que `side` ne encaisse aucun but."""
        if side == "home":
            return sum(self.m[i][0] for i in range(self.n + 1))
        return sum(self.m[0][j] for j in range(self.n + 1))

    def win_to_nil(self, side):
        if side == "home":
            return sum(self.m[i][0] for i in range(1, self.n + 1))
        return sum(self.m[0][j] for j in range(1, self.n + 1))

    def odd_even(self):
        td = self.total_dist()
        odd = sum(p for t, p in td.items() if t % 2 == 1)
        return {"odd": odd, "even": 1.0 - odd}

    def multigoals(self, lo, hi):
        td = self.total_dist()
        return sum(p for t, p in td.items() if lo <= t <= hi)

    def winning_margin(self):
        md = self.margin_dist()
        out = {}
        for k, p in sorted(md.items()):
            if k > 0:
                out["home_by_%d" % k] = p
            elif k < 0:
                out["away_by_%d" % (-k)] = p
            else:
                out["draw"] = p
        return out

    def correct_score(self, i, j):
        if 0 <= i <= self.n and 0 <= j <= self.n:
            return self.m[i][j]
        return 0.0

    def top_scores(self, k=10):
        flat = [((i, j), p) for i, row in enumerate(self.m)
                for j, p in enumerate(row) if p > 0]
        flat.sort(key=lambda x: -x[1])
        return [{"score": "%d-%d" % ij, "prob": p} for ij, p in flat[:k]]

    # --------------------------------------------------------------- divers
    def entropy_bits(self):
        h, d, a = self.result_probs()
        return -sum(p * math.log2(p) for p in (h, d, a) if p > 0)

    def as_dict(self, top_scores=8):
        h, d, a = self.result_probs()
        return {
            "lambda_home": self.lam_h,
            "lambda_away": self.lam_a,
            "rho": self.rho,
            "supremacy": (self.lam_h - self.lam_a) if self.lam_h else None,
            "total_xg": (self.lam_h + self.lam_a) if self.lam_h else None,
            "1x2": {"home": h, "draw": d, "away": a},
            "top_scores": self.top_scores(top_scores),
        }


def _wpl(triplet):
    """(win, push, lose) -> dict enrichi de la cote equitable."""
    w, p, l = triplet
    fair = (1.0 + l / w) if w > EPS else float("inf")
    return {"win": w, "push": p, "lose": l, "fair_odds": fair,
            "prob_norm": (w / (w + l)) if (w + l) > EPS else 0.0}


def _asian_components(line):
    """Decompose une ligne quart (x.25 / x.75) en deux demi-lignes."""
    q = int(round(line * 4))
    if q % 2 == 0:
        return [(q / 4.0, 1.0)]
    return [((q - 1) / 4.0, 0.5), ((q + 1) / 4.0, 0.5)]


def line_probs(dist, line, direction=1):
    """
    Probabilites (gain, remboursement, perte) d'un pari a ligne asiatique.

    `dist`      : distribution discrete {valeur_entiere: proba}
    `line`      : ligne (multiple de 0.25)
    `direction` : +1 si le pari gagne quand valeur > ligne, -1 sinon.
    """
    win = push = lose = 0.0
    for c, weight in _asian_components(line):
        for v, p in dist.items():
            if not p:
                continue
            if abs(v - c) < 1e-9:
                push += weight * p
            elif (v > c) == (direction > 0):
                win += weight * p
            else:
                lose += weight * p
    return win, push, lose


def fair_odds(prob):
    return (1.0 / prob) if prob > EPS else float("inf")


def edge(prob, odds):
    """Esperance par unite misee : p*o - 1."""
    return prob * odds - 1.0


def edge_asian(wpl, odds):
    """Esperance d'un pari asiatique tenant compte du remboursement."""
    return wpl["win"] * (odds - 1.0) - wpl["lose"]


# --------------------------------------------------------------------------
# 3. Retrait de la marge bookmaker ("devig")
# --------------------------------------------------------------------------

def _implied(odds):
    return [1.0 / o for o in odds]


def devig_multiplicative(odds):
    q = _implied(odds)
    s = sum(q)
    return [x / s for x in q]


def devig_additive(odds):
    """
    Marge repartie uniformement (equivalent a la methode dite
    "margin proportional to odds" de Buchdahl). Peut produire des valeurs
    negatives sur des books tres desequilibres -> on borne puis renormalise.
    """
    q = _implied(odds)
    m = sum(q) - 1.0
    n = len(q)
    p = [max(x - m / n, 1e-6) for x in q]
    s = sum(p)
    return [x / s for x in p]


def devig_power(odds):
    """Trouve k tel que sum(q_i^k) = 1. Corrige partiellement le biais
    favori/outsider (la marge est proportionnellement plus lourde sur les
    grosses cotes)."""
    q = _implied(odds)

    def f(k):
        return sum(x ** k for x in q) - 1.0

    k = bisect(f, 0.2, 20.0)
    if k is None:
        return devig_multiplicative(odds)
    p = [x ** k for x in q]
    s = sum(p)
    return [x / s for x in p]


def devig_odds_ratio(odds):
    """Methode "odds ratio" (Cheung) : p = q / (c + q - c*q)."""
    q = _implied(odds)

    def f(c):
        return sum(x / (c + x - c * x) for x in q) - 1.0

    c = bisect(f, 1e-6, 1000.0)
    if c is None:
        return devig_multiplicative(odds)
    p = [x / (c + x - c * x) for x in q]
    s = sum(p)
    return [x / s for x in p]


def devig_shin(odds):
    """
    Modele de Shin (1993) : la marge remuneree provient de parieurs informes.
    Reference du secteur pour les marches 2 et 3 issues ; attenue le biais
    favori/outsider mieux que la normalisation naive.
    Renvoie aussi z, la proportion estimee de flux "informe".
    """
    q = _implied(odds)
    B = sum(q)

    def probs(z):
        if z >= 1.0 - 1e-9:
            return [1.0 / len(q)] * len(q)
        out = []
        for x in q:
            val = math.sqrt(max(z * z + 4.0 * (1.0 - z) * x * x / B, 0.0))
            out.append((val - z) / (2.0 * (1.0 - z)))
        return out

    def f(z):
        return sum(probs(z)) - 1.0

    z = bisect(f, 0.0, 0.9999)
    if z is None:
        return devig_multiplicative(odds), 0.0
    p = probs(z)
    s = sum(p)
    return [x / s for x in p], z


DEVIG_METHODS = ("multiplicative", "additive", "power", "odds_ratio", "shin")


def devig(odds, method="auto"):
    """
    Retire la marge d'un ensemble de cotes decimales d'un meme marche.

    method="auto" -> Shin (2-3 issues), puissance au-dela.
    Renvoie un dict complet : probabilites, marge, et TOUTES les methodes
    pour mesurer la sensibilite du prix a l'hypothese de devig.
    """
    odds = [float(o) for o in odds]
    if any(o <= 1.0 for o in odds):
        raise ValueError("cotes decimales invalides (doivent etre > 1.0)")
    q = _implied(odds)
    overround = sum(q) - 1.0
    shin_p, shin_z = devig_shin(odds)
    allm = {
        "multiplicative": devig_multiplicative(odds),
        "additive": devig_additive(odds),
        "power": devig_power(odds),
        "odds_ratio": devig_odds_ratio(odds),
        "shin": shin_p,
    }
    if method == "auto":
        chosen = "shin" if len(odds) <= 3 else "power"
    else:
        chosen = method
    if chosen not in allm:
        raise ValueError("methode de devig inconnue: %s" % chosen)
    p = allm[chosen]
    spread = [max(allm[k][i] for k in allm) - min(allm[k][i] for k in allm)
              for i in range(len(odds))]
    return {
        "odds": odds,
        "implied_raw": q,
        "overround": overround,
        "margin_pct": 100.0 * overround / (1.0 + overround),
        "method": chosen,
        "probs": p,
        "fair_odds": [fair_odds(x) for x in p],
        "shin_z": shin_z,
        "all_methods": allm,
        "method_spread": spread,     # incertitude de modele sur le devig
    }


# --------------------------------------------------------------------------
# 4. Inversion du marche : cotes -> (lambda_dom, lambda_ext)
# --------------------------------------------------------------------------

def _grid(T, s, rho, max_goals=MAX_GOALS):
    lam_h = max((T + s) / 2.0, 1e-4)
    lam_a = max((T - s) / 2.0, 1e-4)
    return ScoreGrid.from_lambdas(lam_h, lam_a, rho, max_goals)


# Tolerance des inversions de marche. Elle porte sur une PROBABILITE :
# 1e-7 represente 0,00001 point de pourcentage, trois ordres de grandeur
# sous la precision de la moindre cote affichee. La resserrer davantage ne
# fait que multiplier les constructions de grille (l'inversion est le poste
# le plus couteux du backtest).
INVERT_TOL = 1e-7


def _solve_s(T, target, fn, rho, max_goals, tol=INVERT_TOL):
    """Trouve la suprematie s telle que fn(grille) = target (fn croissante)."""
    lo, hi = -T + 1e-3, T - 1e-3

    def f(s):
        return fn(_grid(T, s, rho, max_goals)) - target

    r = bisect(f, lo, hi, tol=tol)
    return lo if r is None else r


def lambdas_from_1x2(p_home, p_draw, p_away, rho=0.0, max_goals=MAX_GOALS):
    """
    Inverse un 1X2 DEBARRASSE DE LA MARGE en un couple (lambda_dom, lambda_ext).

    Principe : bissection imbriquee.
      - interne : a total T fixe, la difference P(1)-P(2) croit avec la
        suprematie s ;
      - externe : P(nul) decroit avec le total T.
    Le couple obtenu reproduit exactement le 1X2 du marche et permet donc de
    tarifer TOUS les marches derives de facon coherente avec le marche.
    """
    tot = p_home + p_draw + p_away
    p_home, p_draw, p_away = p_home / tot, p_draw / tot, p_away / tot
    diff = p_home - p_away

    def f_diff(g):
        h, _, a = g.result_probs()
        return h - a

    def f_draw(T):
        s = _solve_s(T, diff, f_diff, rho, max_goals)
        _, d, _ = _grid(T, s, rho, max_goals).result_probs()
        return d - p_draw

    T = bisect(f_draw, 0.35, 9.0, tol=INVERT_TOL)
    if T is None:
        T = 2.6
    s = _solve_s(T, diff, f_diff, rho, max_goals)
    lam_h = max((T + s) / 2.0, 1e-4)
    lam_a = max((T - s) / 2.0, 1e-4)
    return lam_h, lam_a


def lambdas_from_asian(ah_line, p_ah_home, ou_line, p_over,
                       rho=0.0, max_goals=MAX_GOALS):
    """
    Inverse un couple (handicap asiatique, total) DEBARRASSE DE LA MARGE.

    C'est la methode des syndicats : les lignes asiatiques de Pinnacle /
    Betfair sont les prix les plus efficients du marche. On les convertit en
    (lambda_dom, lambda_ext), puis on tarifie les marches secondaires, souvent
    plus mous, pour en extraire la valeur.

    `p_ah_home` et `p_over` sont les probabilites hors remboursement
    (win / (win + lose)).
    """
    def f_ah(g):
        return g.asian_handicap(ah_line)["home"]["prob_norm"]

    def f_over(T):
        s = _solve_s(T, p_ah_home, f_ah, rho, max_goals)
        return _grid(T, s, rho, max_goals).over_under(ou_line)["over"]["prob_norm"] - p_over

    T = bisect(f_over, 0.35, 9.0, tol=INVERT_TOL)
    if T is None:
        T = 2.6
    s = _solve_s(T, p_ah_home, f_ah, rho, max_goals)
    return max((T + s) / 2.0, 1e-4), max((T - s) / 2.0, 1e-4)


# --------------------------------------------------------------------------
# 5. Fusion modele <-> marche
# --------------------------------------------------------------------------

def log_pool(prob_sets, weights):
    """
    Pooling log-lineaire (moyenne geometrique ponderee) de distributions
    categorielles. Superieur a la moyenne arithmetique : preserve les rapports
    de cotes, ne cree pas de fausse incertitude, reste dans le simplexe.
    """
    if not prob_sets:
        raise ValueError("aucune distribution")
    n = len(prob_sets[0])
    ws = sum(weights)
    weights = [w / ws for w in weights]
    out = []
    for i in range(n):
        acc = 0.0
        for ps, w in zip(prob_sets, weights):
            acc += w * safe_log(max(ps[i], EPS))
        out.append(math.exp(acc))
    s = sum(out)
    return [x / s for x in out]


def blend_lambdas(model, market, w_market):
    """Fusion geometrique des intensites (lambda_dom, lambda_ext)."""
    w = _clip(float(w_market), 0.0, 1.0)
    return (math.exp((1 - w) * safe_log(model[0]) + w * safe_log(market[0])),
            math.exp((1 - w) * safe_log(model[1]) + w * safe_log(market[1])))


# --------------------------------------------------------------------------
# 6. Mi-temps / fin de match
# --------------------------------------------------------------------------

def halves_analysis(lam_h, lam_a, rho=0.0, h1_share=DEFAULT_H1_SHARE,
                    max_goals=8):
    """
    Decompose le match en deux mi-temps independantes.

    La somme de deux Poisson etant Poisson, la grille temps plein reconstruite
    est coherente avec la grille directe (a la correction DC pres).
    """
    g1 = ScoreGrid.from_lambdas(lam_h * h1_share, lam_a * h1_share,
                                rho * 0.5, max_goals)
    g2 = ScoreGrid.from_lambdas(lam_h * (1 - h1_share), lam_a * (1 - h1_share),
                                rho * 0.5, max_goals)
    htft = defaultdict(float)
    ht = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for i1 in range(max_goals + 1):
        for j1 in range(max_goals + 1):
            p1 = g1.m[i1][j1]
            if p1 < 1e-12:
                continue
            r1 = "home" if i1 > j1 else ("draw" if i1 == j1 else "away")
            ht[r1] += p1
            for i2 in range(max_goals + 1):
                for j2 in range(max_goals + 1):
                    p2 = g2.m[i2][j2]
                    if p2 < 1e-12:
                        continue
                    ih, ia = i1 + i2, j1 + j2
                    r2 = "home" if ih > ia else ("draw" if ih == ia else "away")
                    htft[(r1, r2)] += p1 * p2
    lab = {"home": "1", "draw": "X", "away": "2"}
    return {
        "ht_1x2": ht,
        "ht_over_05": 1.0 - g1.m[0][0],
        "htft": {"%s/%s" % (lab[a], lab[b]): p for (a, b), p in
                 sorted(htft.items(), key=lambda kv: -kv[1])},
        "h1_share": h1_share,
    }


# --------------------------------------------------------------------------
# 7. Estimation des forces d'equipe (Dixon-Coles pondere dans le temps)
# --------------------------------------------------------------------------

def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError("date illisible: %r" % value)


class DixonColesModel:
    """Forces offensives / defensives par equipe + avantage du terrain."""

    def __init__(self, teams, att, dfn, home_adv, mu, rho,
                 counts=None, weights=None, meta=None):
        self.teams = list(teams)
        self.att = dict(att)
        self.dfn = dict(dfn)
        self.home_adv = home_adv
        self.mu = mu
        self.rho = rho
        self.counts = counts or {}
        self.weights = weights or {}
        self.meta = meta or {}

    # ------------------------------------------------------------------ API
    def known(self, team):
        return team in self.att

    def lambdas(self, home, away, neutral=False, adj_home=1.0, adj_away=1.0):
        ah = self.att.get(home, 0.0)
        dh = self.dfn.get(home, 0.0)
        aa = self.att.get(away, 0.0)
        da = self.dfn.get(away, 0.0)
        hfa = 0.0 if neutral else self.home_adv
        lam_h = math.exp(self.mu + hfa + ah + da) * adj_home
        lam_a = math.exp(self.mu + aa + dh) * adj_away
        return lam_h, lam_a

    def grid(self, home, away, neutral=False, adj_home=1.0, adj_away=1.0,
             max_goals=MAX_GOALS, shape=None):
        lh, la = self.lambdas(home, away, neutral, adj_home, adj_away)
        return ScoreGrid.from_lambdas(lh, la, self.rho, max_goals, shape, shape)

    def reliability(self, team):
        """Poids effectif accumule : proxy de la confiance dans la note."""
        return self.weights.get(team, 0.0)

    def table(self):
        rows = []
        for t in self.teams:
            lh, la = self.lambdas(t, t)     # match fictif contre soi-meme
            rows.append({
                "team": t,
                "attack": self.att.get(t, 0.0),
                "defense": self.dfn.get(t, 0.0),
                "rating": self.att.get(t, 0.0) - self.dfn.get(t, 0.0),
                "matches": self.counts.get(t, 0),
                "eff_weight": round(self.weights.get(t, 0.0), 2),
                "xg_for_neutral": round(math.exp(self.mu + self.att.get(t, 0.0)), 3),
                "xg_against_neutral": round(math.exp(self.mu + self.dfn.get(t, 0.0)), 3),
            })
        rows.sort(key=lambda r: -r["rating"])
        for i, r in enumerate(rows, 1):
            r["rank"] = i
        return rows

    def to_dict(self):
        return {
            "type": "dixon_coles", "version": __version__,
            "teams": self.teams, "att": self.att, "def": self.dfn,
            "home_adv": self.home_adv, "mu": self.mu, "rho": self.rho,
            "counts": self.counts, "weights": self.weights, "meta": self.meta,
        }

    @staticmethod
    def from_dict(d):
        return DixonColesModel(d["teams"], d["att"], d["def"], d["home_adv"],
                               d["mu"], d["rho"], d.get("counts"),
                               d.get("weights"), d.get("meta"))


def fit_dixon_coles(matches, half_life_days=180.0, reg=1.0, ref_date=None,
                    max_iter=600, lr=0.06, fit_rho=True, target="goals",
                    xg_weight=0.6, init_model=None, verbose=False):
    """
    Ajuste le modele par maximum de vraisemblance pondere.

    matches   : liste de dicts {date, home, away, hg, ag [, hxg, axg]}
    half_life : demi-vie de la ponderation temporelle, en jours.
                Court (90 j) = reactif mais bruite ; long (365 j) = stable
                mais lent a integrer les changements d'effectif.
    reg       : force de retrecissement vers la moyenne du championnat.
                Indispensable pour les promus et les petits echantillons.
    target    : "goals" | "xg" | "blend"  (si colonnes hxg/axg fournies)

    init_model : modele precedent servant de point de depart (demarrage a
                 chaud). Divise par ~4 le nombre d'iterations necessaires
                 lors d'un backtest walk-forward.

    Gradient analytique : d/d att_i = sum_m w_m (y_m - lambda_m).
    Rho (correction Dixon-Coles) est ajuste dans un second temps par
    section doree sur la vraisemblance des scores bas.
    """
    data = []
    for m in matches:
        d = _parse_date(m.get("date"))
        try:
            hg, ag = float(m["hg"]), float(m["ag"])
        except (KeyError, TypeError, ValueError):
            continue
        hxg = m.get("hxg")
        axg = m.get("axg")
        yh, ya = hg, ag
        if target in ("xg", "blend") and hxg not in (None, "") and axg not in (None, ""):
            hxg, axg = float(hxg), float(axg)
            if target == "xg":
                yh, ya = hxg, axg
            else:
                yh = xg_weight * hxg + (1 - xg_weight) * hg
                ya = xg_weight * axg + (1 - xg_weight) * ag
        data.append({"date": d, "home": str(m["home"]).strip(),
                     "away": str(m["away"]).strip(), "yh": yh, "ya": ya,
                     "hg": hg, "ag": ag,
                     "neutral": bool(m.get("neutral", False))})
    if not data:
        raise ValueError("aucun match exploitable")

    if ref_date is None:
        ref_date = max(d["date"] for d in data if d["date"]) if any(
            d["date"] for d in data) else date.today()
    ref_date = _parse_date(ref_date)

    xi = math.log(2.0) / max(float(half_life_days), 1.0)
    for d in data:
        age = (ref_date - d["date"]).days if d["date"] else 0
        d["w"] = math.exp(-xi * max(age, 0))

    teams = sorted({d["home"] for d in data} | {d["away"] for d in data})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    counts = defaultdict(int)
    wsum = defaultdict(float)
    for d in data:
        counts[d["home"]] += 1
        counts[d["away"]] += 1
        wsum[d["home"]] += d["w"]
        wsum[d["away"]] += d["w"]

    total_w = sum(d["w"] for d in data)
    mean_goals = sum(d["w"] * (d["yh"] + d["ya"]) for d in data) / (2 * total_w)
    params = [safe_log(max(mean_goals, 0.05)), 0.15] + [0.0] * (2 * n)
    if init_model is not None:
        params[0] = init_model.mu
        params[1] = init_model.home_adv
        for t, i in idx.items():
            params[2 + i] = init_model.att.get(t, 0.0)
            params[2 + n + i] = init_model.dfn.get(t, 0.0)
    opt = Adam(len(params), lr=lr)

    for it in range(max_iter):
        g = [0.0] * len(params)
        for d in data:
            w = d["w"]
            i, j = idx[d["home"]], idx[d["away"]]
            hfa = 0.0 if d["neutral"] else params[1]
            lh = math.exp(params[0] + hfa + params[2 + i] + params[2 + n + j])
            la = math.exp(params[0] + params[2 + j] + params[2 + n + i])
            lh = min(lh, 25.0)
            la = min(la, 25.0)
            rh = w * (d["yh"] - lh)
            ra = w * (d["ya"] - la)
            g[0] += rh + ra
            if not d["neutral"]:
                g[1] += rh
            g[2 + i] += rh                 # attaque domicile
            g[2 + n + j] += rh             # faiblesse defensive exterieur
            g[2 + j] += ra                 # attaque exterieur
            g[2 + n + i] += ra             # faiblesse defensive domicile
        for k in range(n):                 # retrecissement L2 vers 0
            g[2 + k] -= reg * params[2 + k]
            g[2 + n + k] -= reg * params[2 + n + k]
        params = opt.step(params, g)
        # identifiabilite : attaque et defense de moyenne nulle
        ma = sum(params[2:2 + n]) / n
        md = sum(params[2 + n:2 + 2 * n]) / n
        for k in range(n):
            params[2 + k] -= ma
            params[2 + n + k] -= md
        params[0] += ma + md
        if verbose and it % 100 == 0:
            print("iter %4d  mu=%.4f hfa=%.4f" % (it, params[0], params[1]),
                  file=sys.stderr)

    att = {t: params[2 + idx[t]] for t in teams}
    dfn = {t: params[2 + n + idx[t]] for t in teams}
    mu, hfa = params[0], params[1]

    rho = 0.0
    if fit_rho:
        lam_cache = []
        lo_b, hi_b = -0.9, 0.9
        for d in data:
            if d["hg"] > 1 and d["ag"] > 1:
                continue                    # tau = 1, aucune information
            h = 0.0 if d["neutral"] else hfa
            lh = math.exp(mu + h + att[d["home"]] + dfn[d["away"]])
            la = math.exp(mu + att[d["away"]] + dfn[d["home"]])
            lam_cache.append((int(d["hg"]), int(d["ag"]), lh, la, d["w"]))
            b_lo, b_hi = rho_bounds(lh, la)
            lo_b, hi_b = max(lo_b, b_lo), min(hi_b, b_hi)
        if lam_cache and lo_b < hi_b:
            def ll(r):
                s = 0.0
                for hg, ag, lh, la, w in lam_cache:
                    t = dixon_coles_tau(hg, ag, lh, la, r)
                    s += w * safe_log(max(t, 1e-9))
                return s
            rho = golden_section_max(ll, lo_b, hi_b)

    return DixonColesModel(
        teams, att, dfn, hfa, mu, rho, dict(counts), dict(wsum),
        meta={"n_matches": len(data), "half_life_days": half_life_days,
              "reg": reg, "ref_date": str(ref_date), "target": target,
              "total_weight": total_w,
              "mean_goals_per_team": mean_goals})


# --------------------------------------------------------------------------
# 8. Elo a buts (modele secondaire / controle de coherence)
# --------------------------------------------------------------------------

class EloRatings:
    """
    Elo avec marge de buts (variante "World Football Elo").

    Sert de garde-fou : si Elo et Dixon-Coles divergent fortement sur une
    affiche, c'est le signal qu'une equipe a un profil buts atypique
    (finition, chance, changement d'effectif) -> reduire la mise.
    """

    def __init__(self, k=20.0, home_adv=60.0, start=1500.0, regress=0.20):
        self.k, self.home_adv, self.start, self.regress = k, home_adv, start, regress
        self.r = {}

    def rating(self, team):
        return self.r.get(team, self.start)

    def expected(self, home, away, neutral=False):
        hfa = 0.0 if neutral else self.home_adv
        diff = self.rating(home) + hfa - self.rating(away)
        return 1.0 / (1.0 + 10 ** (-diff / 400.0))

    def update(self, home, away, hg, ag, neutral=False):
        exp_h = self.expected(home, away, neutral)
        gd = abs(hg - ag)
        mult = 1.0 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8.0)
        score = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
        delta = self.k * mult * (score - exp_h)
        self.r[home] = self.rating(home) + delta
        self.r[away] = self.rating(away) - delta

    def new_season(self):
        """Regression vers la moyenne entre deux saisons."""
        if not self.r:
            return
        mean = sum(self.r.values()) / len(self.r)
        for t in self.r:
            self.r[t] = mean + (1 - self.regress) * (self.r[t] - mean)

    def fit(self, matches):
        rows = sorted(matches, key=lambda m: _parse_date(m.get("date")) or date.min)
        prev_season = None
        for m in rows:
            season = m.get("season")
            if prev_season is not None and season is not None and season != prev_season:
                self.new_season()
            prev_season = season
            try:
                self.update(str(m["home"]).strip(), str(m["away"]).strip(),
                            float(m["hg"]), float(m["ag"]),
                            bool(m.get("neutral", False)))
            except (KeyError, TypeError, ValueError):
                continue
        return self

    def table(self):
        return sorted(({"team": t, "elo": round(v, 1)} for t, v in self.r.items()),
                      key=lambda x: -x["elo"])


# --------------------------------------------------------------------------
# 9. Mise : Kelly et gestion de portefeuille
# --------------------------------------------------------------------------

def kelly_single(p, odds, fraction=1.0, cap=1.0):
    """Fraction de Kelly pour un pari binaire : f* = (p*o - 1) / (o - 1)."""
    if odds <= 1.0:
        return 0.0
    f = (p * odds - 1.0) / (odds - 1.0)
    return _clip(max(f, 0.0) * fraction, 0.0, cap)


def kelly_asian(win, lose, odds, fraction=1.0, cap=1.0):
    """
    Kelly pour un pari a remboursement possible (handicap / total asiatique).

    Maximise w*log(1+f(o-1)) + push*log(1) + l*log(1-f) :
        f* = (w(o-1) - l) / ((o-1)(w + l))
    """
    if odds <= 1.0 or (win + lose) <= 0:
        return 0.0
    f = (win * (odds - 1.0) - lose) / ((odds - 1.0) * (win + lose))
    return _clip(max(f, 0.0) * fraction, 0.0, cap)


def kelly_with_uncertainty(p, sigma, odds, fraction=1.0, z=1.0, cap=1.0):
    """
    Kelly decote par l'incertitude d'estimation.

    On mise sur p - z*sigma plutot que sur p. Justification : le sur-pari est
    asymetriquement plus destructeur que le sous-pari (la courbe de croissance
    logarithmique est concave et devient negative au-dela de 2x Kelly).
    `sigma` = ecart-type de l'estimation de p (dispersion des methodes de
    devig, desaccord modele/marche, taille d'echantillon).
    """
    return kelly_single(max(p - z * sigma, 0.0), odds, fraction, cap)


def kelly_exclusive(probs, odds):
    """
    Kelly exact pour des issues MUTUELLEMENT EXCLUSIVES d'un meme evenement
    (ex : 1, X, 2). Algorithme de Smoczynski-Tomkins.

    Renvoie la liste des fractions optimales (0 pour les issues exclues).
    Necessaire des qu'on veut jouer deux issues du meme match : les traiter
    independamment sur-mise systematiquement.
    """
    n = len(probs)
    exhaustive = abs(sum(probs) - 1.0) < 1e-9
    # Cas d'arbitrage : couvrir toutes les issues rapporte a coup sur.
    # La reserve optimale est nulle et l'allocation vaut f_i = p_i
    # (maximise sum p_i log(f_i o_i) sous sum f_i = 1).
    if exhaustive and sum(1.0 / o for o in odds) < 1.0 - 1e-12:
        return list(probs)
    order = sorted(range(n), key=lambda i: -(probs[i] * odds[i]))
    chosen = []
    b = 1.0
    for i in order:
        if probs[i] * odds[i] <= b + 1e-12:
            break
        trial = chosen + [i]
        sp = sum(probs[k] for k in trial)
        sq = sum(1.0 / odds[k] for k in trial)
        if sq >= 1.0 - 1e-12 or sp >= 1.0 - 1e-12:
            break
        nb = (1.0 - sp) / (1.0 - sq)
        if nb <= 0:
            break
        chosen, b = trial, nb
    f = [0.0] * n
    for i in chosen:
        f[i] = max(probs[i] - b / odds[i], 0.0)
    return f


def stake_plan(bets, bankroll=1000.0, kelly_fraction=0.25, max_per_bet=0.02,
               max_total=0.10, correlation_haircut=0.0, min_stake=0.0):
    """
    Transforme une liste de paris en plan de mise executable.

    bets : [{"label", "prob", "odds", ["sigma"], ["win","lose"], ["group"]}]

    Garde-fous cumules (l'ordre compte) :
      1. Kelly fractionnaire (defaut 1/4 : le pari plein est intolerable
         quand les probabilites sont estimees et non connues) ;
      2. decote d'incertitude par pari (sigma) ;
      3. plafond par pari ;
      4. decote de correlation intra-groupe (meme match, meme championnat,
         meme journee : les issues ne sont pas independantes) ;
      5. plafond d'exposition totale, applique par mise a l'echelle.
    """
    out = []
    for b in bets:
        odds = float(b["odds"])
        sigma = float(b.get("sigma", 0.0))
        if b.get("win") is not None and b.get("lose") is not None:
            w, l = float(b["win"]), float(b["lose"])
            p_eff = w / (w + l) if (w + l) > 0 else 0.0
            f = kelly_asian(max(w - sigma * (w + l), 0.0), l + sigma * (w + l),
                            odds, kelly_fraction)
            ev = w * (odds - 1.0) - l
        else:
            p_eff = float(b["prob"])
            f = kelly_with_uncertainty(p_eff, sigma, odds, kelly_fraction)
            ev = p_eff * odds - 1.0
        f = min(f, max_per_bet)
        out.append({**b, "kelly_raw": f, "ev": ev, "p_used": p_eff})

    groups = defaultdict(list)
    for i, b in enumerate(out):
        groups[b.get("group", "_")].append(i)
    if correlation_haircut > 0:
        for _, ids in groups.items():
            if len(ids) > 1:
                factor = 1.0 / (1.0 + correlation_haircut * (len(ids) - 1))
                for i in ids:
                    out[i]["kelly_raw"] *= factor

    total = sum(b["kelly_raw"] for b in out)
    scale = 1.0 if total <= max_total or total == 0 else max_total / total
    for b in out:
        b["fraction"] = b["kelly_raw"] * scale
        b["stake"] = round(b["fraction"] * bankroll, 2)
        if b["stake"] < min_stake:
            b["stake"] = 0.0
            b["fraction"] = 0.0
    return {
        "bankroll": bankroll, "kelly_fraction": kelly_fraction,
        "scale_applied": scale,
        "total_exposure": sum(b["fraction"] for b in out),
        "expected_growth": sum(b["fraction"] * b["ev"] for b in out),
        "bets": sorted(out, key=lambda x: -x["stake"]),
    }


# --------------------------------------------------------------------------
# 10. Metriques de calibration et de performance
# --------------------------------------------------------------------------

def brier_multiclass(probs, outcome_index):
    """Somme des ecarts quadratiques (0 = parfait, 2 = pire cas a 3 issues)."""
    return sum((p - (1.0 if i == outcome_index else 0.0)) ** 2
               for i, p in enumerate(probs))


def log_loss(probs, outcome_index):
    return -safe_log(max(probs[outcome_index], EPS))


def rps(probs, outcome_index):
    """
    Ranked Probability Score : metrique de reference pour le 1X2 car elle
    tient compte de l'ordre naturel (1, X, 2). Penalise moins une erreur
    "1 au lieu de X" qu'une erreur "1 au lieu de 2".
    """
    r = len(probs)
    cum_p = 0.0
    cum_o = 0.0
    s = 0.0
    for i in range(r - 1):
        cum_p += probs[i]
        cum_o += 1.0 if i == outcome_index else 0.0
        s += (cum_p - cum_o) ** 2
    return s / (r - 1)


def reliability_bins(pairs, n_bins=10):
    """
    pairs : [(proba_predite, resultat_binaire)]
    Renvoie les bacs de calibration + ECE (Expected Calibration Error).
    Un systeme bien calibre : sur les paris annonces a 60 %, ~60 % passent.
    """
    bins = [{"lo": i / n_bins, "hi": (i + 1) / n_bins, "n": 0,
             "sum_p": 0.0, "hits": 0} for i in range(n_bins)]
    for p, y in pairs:
        k = min(int(p * n_bins), n_bins - 1)
        bins[k]["n"] += 1
        bins[k]["sum_p"] += p
        bins[k]["hits"] += 1 if y else 0
    n_tot = sum(b["n"] for b in bins) or 1
    ece = 0.0
    for b in bins:
        if b["n"]:
            b["mean_pred"] = b["sum_p"] / b["n"]
            b["observed"] = b["hits"] / b["n"]
            b["gap"] = b["observed"] - b["mean_pred"]
            ece += (b["n"] / n_tot) * abs(b["gap"])
        else:
            b["mean_pred"] = b["observed"] = b["gap"] = None
    return {"bins": bins, "ece": ece, "n": n_tot}


def clv(taken_odds, closing_odds, closing_fair_odds=None):
    """
    Closing Line Value : le seul indicateur d'edge fiable a court terme.

    - clv_gross : cote prise / cote de cloture - 1 (marge incluse)
    - clv_fair  : cote prise / cote de cloture DEVIGUEE - 1  <- le bon chiffre
      C'est l'esperance implicite du pari si la cloture est efficiente.
    """
    out = {"clv_gross": taken_odds / closing_odds - 1.0,
           "beat_close": taken_odds > closing_odds}
    if closing_fair_odds:
        out["clv_fair"] = taken_odds / closing_fair_odds - 1.0
    return out


def bootstrap_ci(values, stat=None, n_boot=2000, alpha=0.05, seed=12345):
    """Intervalle de confiance par bootstrap (percentile)."""
    if not values:
        return {"point": None, "lo": None, "hi": None, "n": 0}
    stat = stat or (lambda v: sum(v) / len(v))
    rng = random.Random(seed)
    n = len(values)
    reps = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        reps.append(stat(sample))
    reps.sort()
    lo = reps[int(alpha / 2 * n_boot)]
    hi = reps[min(int((1 - alpha / 2) * n_boot), n_boot - 1)]
    return {"point": stat(values), "lo": lo, "hi": hi, "n": n}


def roi_significance(returns):
    """
    t-statistique du ROI et taille d'echantillon requise.

    A retenir : avec un edge de 3 % et une volatilite typique du 1X2, il faut
    de l'ordre de 1 000 a 2 000 paris pour distinguer le talent du hasard a
    95 %. D'ou la primaute du CLV, qui converge ~10x plus vite.
    """
    n = len(returns)
    if n < 2:
        return {"n": n, "roi": None, "t": None, "n_required_95": None}
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    sd = math.sqrt(max(var, EPS))
    t = mean / (sd / math.sqrt(n))
    n_req = None
    if mean > 0:
        n_req = int(math.ceil((1.96 * sd / mean) ** 2))
    return {"n": n, "roi": mean, "sd": sd, "t": t, "n_required_95": n_req}


# --------------------------------------------------------------------------
# 11. Chaine de tarification complete d'un match
# --------------------------------------------------------------------------

DEFAULT_OU_LINES = (0.5, 1.5, 2.5, 3.5, 4.5)
DEFAULT_AH_LINES = (-2.5, -2.0, -1.5, -1.0, -0.75, -0.5, -0.25, 0.0,
                    0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5)


def market_to_lambdas(market, rho=0.0, max_goals=MAX_GOALS):
    """
    Convertit un bloc de cotes de marche en (lambda_dom, lambda_ext).

    Priorite : lignes asiatiques (AH + total) > 1X2. Les lignes asiatiques
    portent une information plus propre : marge plus faible, limites plus
    hautes, donc flux plus informe.
    """
    info = {}
    if market.get("ah") and market.get("ou"):
        ah, ou = market["ah"], market["ou"]
        dv_ah = devig([ah["home"], ah["away"]])
        dv_ou = devig([ou["over"], ou["under"]])
        lh, la = lambdas_from_asian(float(ah["line"]), dv_ah["probs"][0],
                                    float(ou["line"]), dv_ou["probs"][0],
                                    rho, max_goals)
        info = {"source": "asian", "devig_ah": dv_ah, "devig_ou": dv_ou,
                "spread": max(max(dv_ah["method_spread"]),
                              max(dv_ou["method_spread"]))}
    elif market.get("1x2"):
        dv = devig(market["1x2"])
        lh, la = lambdas_from_1x2(*dv["probs"], rho=rho, max_goals=max_goals)
        info = {"source": "1x2", "devig_1x2": dv,
                "spread": max(dv["method_spread"])}
    else:
        return None, None, {}
    return lh, la, info


def build_book(grid, ou_lines=DEFAULT_OU_LINES, ah_lines=DEFAULT_AH_LINES,
               team_total_lines=(0.5, 1.5, 2.5), with_halves=True,
               h1_share=DEFAULT_H1_SHARE):
    """Tarif complet et coherent de tous les marches usuels."""
    h, d, a = grid.result_probs()
    book = {
        "inputs": {"lambda_home": grid.lam_h, "lambda_away": grid.lam_a,
                   "rho": grid.rho,
                   "supremacy": (grid.lam_h - grid.lam_a) if grid.lam_h else None,
                   "total": (grid.lam_h + grid.lam_a) if grid.lam_h else None},
        "1x2": {"home": {"prob": h, "fair": fair_odds(h)},
                "draw": {"prob": d, "fair": fair_odds(d)},
                "away": {"prob": a, "fair": fair_odds(a)}},
        "double_chance": {k: {"prob": v, "fair": fair_odds(v)}
                          for k, v in grid.double_chance().items()},
        "dnb": {k: {"prob": v, "fair": fair_odds(v)}
                for k, v in grid.draw_no_bet().items()},
        "btts": {k: {"prob": v, "fair": fair_odds(v)}
                 for k, v in grid.btts().items()},
        "odd_even": {k: {"prob": v, "fair": fair_odds(v)}
                     for k, v in grid.odd_even().items()},
        "over_under": {}, "asian_handicap": {}, "team_totals": {},
        "clean_sheet": {"home": grid.clean_sheet("home"),
                        "away": grid.clean_sheet("away")},
        "win_to_nil": {"home": grid.win_to_nil("home"),
                       "away": grid.win_to_nil("away")},
        "multigoals": {"0-1": grid.multigoals(0, 1), "1-2": grid.multigoals(1, 2),
                       "2-3": grid.multigoals(2, 3), "2-4": grid.multigoals(2, 4),
                       "3-5": grid.multigoals(3, 5), "4+": grid.multigoals(4, 99)},
        "winning_margin": grid.winning_margin(),
        "top_scores": grid.top_scores(12),
        "entropy_bits": grid.entropy_bits(),
    }
    for ln in ou_lines:
        book["over_under"]["%.2f" % ln] = grid.over_under(ln)
    for ln in ah_lines:
        book["asian_handicap"]["%+.2f" % ln] = grid.asian_handicap(ln)
    for side in ("home", "away"):
        book["team_totals"][side] = {"%.2f" % ln: grid.team_total(side, ln)
                                     for ln in team_total_lines}
    if with_halves and grid.lam_h:
        book["halves"] = halves_analysis(grid.lam_h, grid.lam_a, grid.rho, h1_share)
    return book


def estimate_sigma(p_model, p_market, devig_spread=0.0, reliability=1.0,
                   base=0.010):
    """
    Ecart-type approximatif de la probabilite estimee.

    Trois sources d'incertitude combinees en quadrature :
      1. desaccord modele / marche (le plus informatif) ;
      2. sensibilite a la methode de devig ;
      3. bruit d'estimation du modele (decroit avec le poids effectif de
         donnees sur l'equipe).
    Cette sigma alimente la decote de Kelly : plus on est incertain,
    moins on mise. C'est la difference entre un systeme robuste et un
    systeme qui explose au premier regime de marche inhabituel.
    """
    disagree = abs(p_model - p_market) if p_market is not None else 0.03
    noise = base / math.sqrt(max(reliability, 0.05))
    return math.sqrt((0.45 * disagree) ** 2 + (0.7 * devig_spread) ** 2
                     + noise ** 2)


def price_match(lam_home=None, lam_away=None, rho=0.0, model=None,
                home=None, away=None, market=None, w_market=0.5,
                adj_home=1.0, adj_away=1.0, shape=None, neutral=False,
                offered=None, bankroll=1000.0, kelly_fraction=0.25,
                min_edge=0.02, max_goals=MAX_GOALS, reliability=1.0,
                ou_lines=DEFAULT_OU_LINES, ah_lines=DEFAULT_AH_LINES):
    """
    Point d'entree principal : produit le tarif complet, la comparaison au
    marche, les paris de valeur et le plan de mise.

    `w_market` : poids accorde au marche dans la fusion (0 = modele pur,
    1 = marche pur). Voir 03_MARCHE_DEVIG_CLV.md pour le bareme par
    championnat ; en pratique 0.55-0.75 sur les grands championnats,
    0.35-0.55 en D2, 0.25-0.45 en feminin.
    """
    result = {"engine": __version__}
    lm = None
    if model is not None and home and away:
        lm = model.lambdas(home, away, neutral=neutral)
        reliability = min(model.reliability(home), model.reliability(away))
        result["model_known"] = model.known(home) and model.known(away)
    elif lam_home is not None and lam_away is not None:
        lm = (float(lam_home), float(lam_away))
    if lm is None:
        raise ValueError("fournir (lam_home, lam_away) ou (model, home, away)")
    lm = (lm[0] * adj_home, lm[1] * adj_away)
    result["lambdas_model"] = lm
    result["adjustments"] = {"home": adj_home, "away": adj_away}

    devig_spread = 0.0
    lk = None
    if market:
        mh, ma, info = market_to_lambdas(market, rho, max_goals)
        if mh is not None:
            lk = (mh, ma)
            devig_spread = info.get("spread", 0.0)
            result["lambdas_market"] = lk
            result["market_info"] = {k: v for k, v in info.items()
                                     if k == "source" or k == "spread"}
    if lk is not None:
        lam = blend_lambdas(lm, lk, w_market)
        result["w_market"] = w_market
    else:
        lam = lm
        result["w_market"] = 0.0
    result["lambdas_used"] = lam

    grid = ScoreGrid.from_lambdas(lam[0], lam[1], rho, max_goals, shape, shape)
    result["book"] = build_book(grid, ou_lines, ah_lines)

    if lk is not None:
        gm = ScoreGrid.from_lambdas(lm[0], lm[1], rho, max_goals)
        gk = ScoreGrid.from_lambdas(lk[0], lk[1], rho, max_goals)
        result["diagnostics"] = {
            "model_1x2": dict(zip(("home", "draw", "away"), gm.result_probs())),
            "market_1x2": dict(zip(("home", "draw", "away"), gk.result_probs())),
            "supremacy_gap": (lm[0] - lm[1]) - (lk[0] - lk[1]),
            "total_gap": (lm[0] + lm[1]) - (lk[0] + lk[1]),
            "devig_spread": devig_spread,
        }

    # Penalite de desaccord : un modele qui s'ecarte fortement du marche a
    # plus souvent tort que raison (donnee manquante, effectif, information
    # non publique deja integree par le marche). On mise moins, sans renoncer.
    penalty = 1.0
    if lk is not None:
        gap = max(abs((lm[0] - lm[1]) - (lk[0] - lk[1])) / 0.60,
                  abs((lm[0] + lm[1]) - (lk[0] + lk[1])) / 0.90)
        penalty = 1.0 / (1.0 + 2.0 * max(gap - 0.5, 0.0))
    result["disagreement_penalty"] = penalty

    if offered:
        value = scan_value(grid, offered, min_edge=min_edge,
                           devig_spread=devig_spread, reliability=reliability,
                           market_probs=_market_prob_lookup(lk, rho, max_goals))
        result["value_bets"] = value
        result["stake_plan"] = stake_plan(
            [{k: v[k] for k in ("label", "prob", "odds", "sigma", "group",
                                "win", "lose") if k in v}
             for v in value if v["edge"] >= min_edge],
            bankroll=bankroll, kelly_fraction=kelly_fraction * penalty,
            correlation_haircut=0.35)
        result["stake_plan"]["disagreement_penalty"] = penalty
    return result


def _market_prob_lookup(lk, rho, max_goals):
    if lk is None:
        return None
    return ScoreGrid.from_lambdas(lk[0], lk[1], rho, max_goals)


def scan_value(grid, offered, min_edge=0.02, devig_spread=0.0,
               reliability=1.0, market_probs=None):
    """
    Compare les cotes disponibles au tarif du modele.

    `offered` : dict de cotes proposees, ex.
        {"1x2": {"home": 2.10, "draw": 3.5, "away": 3.6},
         "ou": {"2.5": {"over": 1.95, "under": 1.95}},
         "ah": {"-0.5": {"home": 2.05, "away": 1.90}},
         "btts": {"yes": 1.80, "no": 2.05}}
    """
    out = []
    h, d, a = grid.result_probs()
    probs_1x2 = {"home": h, "draw": d, "away": a}

    def add(label, prob, odds, win=None, lose=None, group="match", mkt=None):
        if not odds or odds <= 1.0:
            return
        e = (win * (odds - 1.0) - lose) if win is not None else (prob * odds - 1.0)
        sigma = estimate_sigma(prob, mkt, devig_spread, reliability)
        row = {"label": label, "prob": prob, "odds": odds,
               "fair": fair_odds(prob), "edge": e, "sigma": sigma,
               "edge_z": (e / max(sigma * odds, 1e-9)), "group": group}
        if win is not None:
            row["win"], row["lose"] = win, lose
        out.append(row)

    o = offered or {}
    for k, odds in (o.get("1x2") or {}).items():
        if k in probs_1x2:
            mkt = None
            if market_probs is not None:
                mp = dict(zip(("home", "draw", "away"), market_probs.result_probs()))
                mkt = mp.get(k)
            add("1X2 " + k, probs_1x2[k], odds, mkt=mkt)
    for k, odds in (o.get("dc") or {}).items():
        dc = grid.double_chance()
        if k in dc:
            add("DC " + k, dc[k], odds)
    for k, odds in (o.get("btts") or {}).items():
        b = grid.btts()
        if k in b:
            add("BTTS " + k, b[k], odds)
    for line, sides in (o.get("ou") or {}).items():
        ou = grid.over_under(float(line))
        for side, odds in sides.items():
            if side in ou:
                w = ou[side]
                add("O/U %s %s" % (line, side), w["prob_norm"], odds,
                    w["win"], w["lose"], group="total")
    for line, sides in (o.get("ah") or {}).items():
        ah = grid.asian_handicap(float(line))
        for side, odds in sides.items():
            if side in ah:
                w = ah[side]
                add("AH %s %s" % (line, side), w["prob_norm"], odds,
                    w["win"], w["lose"], group="handicap")
    for side, lines in (o.get("team_totals") or {}).items():
        for line, sides in lines.items():
            tt = grid.team_total(side, float(line))
            for s, odds in sides.items():
                if s in tt:
                    w = tt[s]
                    add("TT %s %s %s" % (side, line, s), w["prob_norm"], odds,
                        w["win"], w["lose"], group="total")
    for score, odds in (o.get("cs") or {}).items():
        try:
            i, j = (int(x) for x in str(score).replace(":", "-").split("-"))
        except ValueError:
            continue
        add("CS " + str(score), grid.correct_score(i, j), odds, group="cs")

    out.sort(key=lambda r: -r["edge"])
    for r in out:
        r["value"] = r["edge"] >= min_edge
    return out


# --------------------------------------------------------------------------
# 11 bis. Rendu compact (fiche de match lisible)
# --------------------------------------------------------------------------

def _pc(x):
    return "%.1f%%" % (100.0 * x)


def render_match(res, home="Domicile", away="Exterieur", competition="",
                 max_bets=8):
    """
    Fiche de match condensee, prete a coller dans une conversation.

    Le JSON complet reste disponible pour l'analyse ; cette fiche est ce que
    l'on lit avant de miser.
    """
    L = []
    bk = res["book"]
    lam = res["lambdas_used"]
    title = "%s  -  %s" % (home, away)
    if competition:
        title += "   [%s]" % competition
    L.append("=" * 66)
    L.append(title)
    L.append("=" * 66)
    lm = res.get("lambdas_model")
    lk = res.get("lambdas_market")
    L.append("Intensites (buts attendus)")
    if lm:
        L.append("   modele  : %.2f - %.2f   (total %.2f, suprematie %+.2f)"
                 % (lm[0], lm[1], lm[0] + lm[1], lm[0] - lm[1]))
    if lk:
        L.append("   marche  : %.2f - %.2f   (total %.2f, suprematie %+.2f)"
                 % (lk[0], lk[1], lk[0] + lk[1], lk[0] - lk[1]))
    L.append("   RETENU  : %.2f - %.2f   (total %.2f, suprematie %+.2f)  [w_marche=%.2f]"
             % (lam[0], lam[1], lam[0] + lam[1], lam[0] - lam[1],
                res.get("w_market", 0.0)))
    d = res.get("diagnostics")
    if d:
        L.append("   ecarts modele-marche : suprematie %+.2f | total %+.2f"
                 % (d["supremacy_gap"], d["total_gap"]))
        flag = ("DESACCORD FORT - reduire la mise"
                if abs(d["supremacy_gap"]) > 0.45 or abs(d["total_gap"]) > 0.60
                else "accord raisonnable")
        L.append("   -> %s" % flag)
    L.append("")
    x = bk["1x2"]
    L.append("Probabilites justes")
    L.append("   1X2      1 %s (%.2f)   X %s (%.2f)   2 %s (%.2f)"
             % (_pc(x["home"]["prob"]), x["home"]["fair"],
                _pc(x["draw"]["prob"]), x["draw"]["fair"],
                _pc(x["away"]["prob"]), x["away"]["fair"]))
    ou = bk["over_under"].get("2.50")
    if ou:
        L.append("   O/U 2.5  over %s (%.2f)   under %s (%.2f)"
                 % (_pc(ou["over"]["win"]), ou["over"]["fair_odds"],
                    _pc(ou["under"]["win"]), ou["under"]["fair_odds"]))
    bt = bk["btts"]
    L.append("   BTTS     oui %s (%.2f)   non %s (%.2f)"
             % (_pc(bt["yes"]["prob"]), bt["yes"]["fair"],
                _pc(bt["no"]["prob"]), bt["no"]["fair"]))
    ah = bk["asian_handicap"].get("-0.50")
    if ah:
        L.append("   AH -0.5  dom %s (%.2f)   ext %s (%.2f)"
                 % (_pc(ah["home"]["prob_norm"]), ah["home"]["fair_odds"],
                    _pc(ah["away"]["prob_norm"]), ah["away"]["fair_odds"]))
    L.append("   Scores   " + "  ".join(
        "%s %s" % (t["score"], _pc(t["prob"])) for t in bk["top_scores"][:5]))
    L.append("   Incertitude du match : %.2f bits (max 1.58)" % bk["entropy_bits"])

    vb = res.get("value_bets")
    if vb:
        L.append("")
        L.append("Comparaison au marche")
        L.append("   %-24s %6s %6s %8s %6s" % ("pari", "cote", "juste", "edge", "z"))
        for v in vb[:max_bets]:
            L.append("   %-24s %6.2f %6.2f %+7.2f%% %6.2f%s"
                     % (v["label"], v["odds"], v["fair"], 100 * v["edge"],
                        v["edge_z"], "  <<<" if v["value"] else ""))
    sp = res.get("stake_plan")
    if sp:
        played = [b for b in sp["bets"] if b["stake"] > 0]
        L.append("")
        pen = sp.get("disagreement_penalty", 1.0)
        L.append("Plan de mise (banque %.0f, Kelly x%.3f%s)"
                 % (sp["bankroll"], sp["kelly_fraction"],
                    "" if pen > 0.999 else
                    "  = base x%.2f de penalite de desaccord" % pen))
        if not played:
            L.append("   AUCUN PARI : pas d'avantage suffisant apres decote. "
                     "Ne pas forcer.")
        for b in played:
            L.append("   %-24s %8.2f   (%.2f%% de banque)"
                     % (b["label"], b["stake"], 100 * b["fraction"]))
        if played:
            L.append("   exposition totale %.2f%%   croissance log attendue %+.4f%%"
                     % (100 * sp["total_exposure"], 100 * sp["expected_growth"]))
    L.append("=" * 66)
    return "\n".join(L)


# --------------------------------------------------------------------------
# 12. Simulation Monte-Carlo de fin de saison
# --------------------------------------------------------------------------

def _flat_cdf(grid, cutoff=1e-7):
    items, cum = [], 0.0
    for i, row in enumerate(grid.m):
        for j, p in enumerate(row):
            if p > cutoff:
                cum += p
                items.append([cum, i, j])
    scale = items[-1][0]
    for it in items:
        it[0] /= scale
    return items


def _sample(cdf, u):
    lo, hi = 0, len(cdf) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if cdf[mid][0] < u:
            lo = mid + 1
        else:
            hi = mid
    return cdf[lo][1], cdf[lo][2]


def simulate_season(model, fixtures, standings=None, n_sims=10000, seed=7,
                    promo=2, playoff=None, releg=3, neutral=False,
                    adjustments=None):
    """
    Simule les journees restantes et renvoie les probabilites de classement.

    Indispensable en D2 : les cotes "montee / barrages / descente" y sont
    souvent tres mal tarifees, et la motivation de fin de saison (equipe deja
    sauvee, deja qualifiee) est un facteur exploitable que le modele de match
    seul ne capture pas.
    """
    rng = random.Random(seed)
    standings = standings or {}
    teams = sorted({f["home"] for f in fixtures} | {f["away"] for f in fixtures}
                   | set(standings.keys()))
    base = {t: {"pts": standings.get(t, {}).get("pts", 0),
                "gf": standings.get(t, {}).get("gf", 0),
                "ga": standings.get(t, {}).get("ga", 0)} for t in teams}
    adjustments = adjustments or {}

    cdfs = []
    for f in fixtures:
        ah = adjustments.get(f["home"], {}).get("attack", 1.0)
        aa = adjustments.get(f["away"], {}).get("attack", 1.0)
        g = model.grid(f["home"], f["away"],
                       neutral=bool(f.get("neutral", neutral)),
                       adj_home=ah, adj_away=aa)
        cdfs.append((f["home"], f["away"], _flat_cdf(g)))

    n_t = len(teams)
    pos_counts = {t: [0] * n_t for t in teams}
    pts_sum = {t: 0.0 for t in teams}
    for _ in range(n_sims):
        pts = {t: base[t]["pts"] for t in teams}
        gf = {t: base[t]["gf"] for t in teams}
        ga = {t: base[t]["ga"] for t in teams}
        for hteam, ateam, cdf in cdfs:
            hg, ag = _sample(cdf, rng.random())
            gf[hteam] += hg
            ga[hteam] += ag
            gf[ateam] += ag
            ga[ateam] += hg
            if hg > ag:
                pts[hteam] += 3
            elif hg < ag:
                pts[ateam] += 3
            else:
                pts[hteam] += 1
                pts[ateam] += 1
        order = sorted(teams, key=lambda t: (-pts[t], -(gf[t] - ga[t]), -gf[t],
                                             rng.random()))
        for rank, t in enumerate(order):
            pos_counts[t][rank] += 1
            pts_sum[t] += pts[t]

    out = []
    for t in teams:
        c = pos_counts[t]
        row = {
            "team": t,
            "mean_points": pts_sum[t] / n_sims,
            "p_champion": c[0] / n_sims,
            "p_promotion": sum(c[:promo]) / n_sims if promo else None,
            "p_relegation": sum(c[n_t - releg:]) / n_sims if releg else None,
            "position_dist": [x / n_sims for x in c],
            "expected_position": sum((i + 1) * x for i, x in enumerate(c)) / n_sims,
        }
        if playoff:
            lo, hi = playoff
            row["p_playoff"] = sum(c[lo - 1:hi]) / n_sims
        out.append(row)
    out.sort(key=lambda r: r["expected_position"])
    return {"n_sims": n_sims, "teams": out,
            "fair_odds_hint": "1 / p, puis appliquer une marge de securite"}


def simulate_parlay(legs, n_sims=20000, seed=11):
    """
    Probabilite d'un combine EN TENANT COMPTE DES CORRELATIONS intra-match.

    legs : [{"grid": ScoreGrid, "match_id": str, "test": callable(hg, ag)->bool}]
    Deux selections du meme match sont simulees sur le meme tirage de score :
    c'est la seule facon correcte de tarifer un "combine boosté" (ex :
    victoire + plus de 2,5 buts), que la multiplication naive des
    probabilites sous-estime ou surestime selon le sens de la correlation.
    """
    rng = random.Random(seed)
    by_match = defaultdict(list)
    for lg in legs:
        by_match[lg["match_id"]].append(lg)
    cdfs = {mid: _flat_cdf(lgs[0]["grid"]) for mid, lgs in by_match.items()}
    hits = 0
    for _ in range(n_sims):
        ok = True
        for mid, lgs in by_match.items():
            hg, ag = _sample(cdfs[mid], rng.random())
            for lg in lgs:
                if not lg["test"](hg, ag):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            hits += 1
    p = hits / n_sims
    naive = 1.0
    for mid, lgs in by_match.items():
        g = lgs[0]["grid"]
        for lg in lgs:
            naive *= sum(g.m[i][j] for i in range(g.n + 1)
                         for j in range(g.n + 1) if lg["test"](i, j))
    se = math.sqrt(max(p * (1 - p) / n_sims, 0.0))
    return {"prob": p, "fair_odds": fair_odds(p), "naive_independent": naive,
            "correlation_effect": (p - naive), "std_error": se,
            "n_sims": n_sims}


# --------------------------------------------------------------------------
# 13. Entrees / sorties CSV
# --------------------------------------------------------------------------

COLUMN_ALIASES = {
    "date":   ["date", "matchdate", "match_date", "kickoff", "day"],
    "home":   ["hometeam", "home", "home_team", "hometeamname", "localteam"],
    "away":   ["awayteam", "away", "away_team", "awayteamname", "visitorteam"],
    "hg":     ["fthg", "hg", "home_goals", "homegoals", "hscore", "goals_home"],
    "ag":     ["ftag", "ag", "away_goals", "awaygoals", "ascore", "goals_away"],
    "league": ["div", "league", "competition", "comp", "tournament"],
    "season": ["season", "saison", "year"],
    "hxg":    ["hxg", "xg_home", "home_xg", "xgh"],
    "axg":    ["axg", "xg_away", "away_xg", "xga"],
    "neutral": ["neutral", "neutre"],
    # cotes d'ouverture / pre-match (ordre de preference : Pinnacle > B365 > moyenne)
    "odds_h": ["psh", "ph", "pinnacleh", "b365h", "avgh", "bwh", "odds_h", "oddsh", "home_odds"],
    "odds_d": ["psd", "pd", "pinnacled", "b365d", "avgd", "bwd", "odds_d", "oddsd", "draw_odds"],
    "odds_a": ["psa", "pa", "pinnaclea", "b365a", "avga", "bwa", "odds_a", "oddsa", "away_odds"],
    # cotes de cloture (pour le CLV)
    "close_h": ["psch", "closeh", "close_h", "closing_h", "maxch"],
    "close_d": ["pscd", "closed_", "close_d", "closing_d", "maxcd"],
    "close_a": ["psca", "closea", "close_a", "closing_a", "maxca"],
}


def _norm(col):
    return "".join(ch for ch in col.strip().lower() if ch.isalnum() or ch == "_")


def load_matches_csv(path, encoding="utf-8-sig"):
    """
    Charge un CSV de matchs. Compatible directement avec les exports
    football-data.co.uk (Date, HomeTeam, AwayTeam, FTHG, FTAG, PSH/PSD/PSA,
    PSCH/PSCD/PSCA) et avec un schema generique en minuscules.
    """
    rows = []
    with open(path, "r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        headers = {_norm(h): h for h in (reader.fieldnames or [])}
        mapping = {}
        for key, aliases in COLUMN_ALIASES.items():
            for a in aliases:
                if a in headers:
                    mapping[key] = headers[a]
                    break
        missing = [k for k in ("date", "home", "away", "hg", "ag")
                   if k not in mapping]
        if missing:
            raise ValueError("colonnes manquantes dans %s : %s (entetes vues : %s)"
                             % (path, missing, list(headers.values())[:20]))
        for raw in reader:
            try:
                rec = {
                    "date": _parse_date(raw[mapping["date"]]),
                    "home": raw[mapping["home"]].strip(),
                    "away": raw[mapping["away"]].strip(),
                    "hg": int(float(raw[mapping["hg"]])),
                    "ag": int(float(raw[mapping["ag"]])),
                }
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
            for k in ("league", "season", "hxg", "axg", "neutral",
                      "odds_h", "odds_d", "odds_a",
                      "close_h", "close_d", "close_a"):
                if k in mapping:
                    v = raw.get(mapping[k], "")
                    if v not in ("", None):
                        try:
                            rec[k] = float(v) if k not in ("league", "season") else v
                        except ValueError:
                            rec[k] = v
            rows.append(rec)
    rows.sort(key=lambda r: r["date"])
    return rows


def write_json(obj, path=None):
    txt = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(txt)
    return txt


# --------------------------------------------------------------------------
# 14. Backtest walk-forward
# --------------------------------------------------------------------------

def backtest(matches, min_train=150, refit_every_days=21, half_life_days=180.0,
             reg=1.0, w_market=0.6, min_edge=0.03, kelly_fraction=0.25,
             bankroll=1000.0, max_iter=250, warm_iter=90, max_per_bet=0.02,
             train_window_days=1460, sigma_z=1.0, verbose=False):
    """
    Validation temporelle stricte : a chaque date, le modele n'a vu QUE le
    passe. Aucune fuite d'information (la fuite la plus frequente dans les
    systemes amateurs : reajuster sur toute la saison puis "backtester"
    dessus).

    Compare systematiquement trois jeux de probabilites :
      - modele seul ;
      - marche seul (cotes deviguees) : c'est LE benchmark a battre ;
      - fusion modele + marche.
    Un systeme qui ne bat pas le marche en RPS n'a aucune raison de generer
    du CLV positif. C'est le test d'echec le plus important du projet.
    """
    ms = sorted([m for m in matches if m.get("date")], key=lambda m: m["date"])
    if len(ms) <= min_train:
        raise ValueError("pas assez de matchs (%d) pour min_train=%d"
                         % (len(ms), min_train))

    model = None
    last_fit = None
    scores = {"model": [], "market": [], "blend": []}
    briers = {"model": [], "market": [], "blend": []}
    lls = {"model": [], "market": [], "blend": []}
    rel_pairs = []
    bets, returns, clvs = [], [], []
    bank = bankroll
    peak, max_dd = bankroll, 0.0
    n_priced = 0

    for i, m in enumerate(ms):
        if i < min_train:
            continue
        need = (model is None or last_fit is None or
                (m["date"] - last_fit).days >= refit_every_days)
        if need:
            train = [x for x in ms[:i]
                     if (m["date"] - x["date"]).days <= train_window_days]
            if len(train) < min_train:
                train = ms[:i]
            model = fit_dixon_coles(
                train, half_life_days=half_life_days, reg=reg,
                ref_date=m["date"], max_iter=(warm_iter if model else max_iter),
                init_model=model)
            last_fit = m["date"]
            if verbose:
                print("  refit @ %s sur %d matchs" % (m["date"], len(train)),
                      file=sys.stderr)

        if not (model.known(m["home"]) and model.known(m["away"])):
            continue
        lh, la = model.lambdas(m["home"], m["away"])
        g_model = ScoreGrid.from_lambdas(lh, la, model.rho)
        p_model = list(g_model.result_probs())

        has_odds = all(m.get(k) for k in ("odds_h", "odds_d", "odds_a"))
        if has_odds:
            dv = devig([m["odds_h"], m["odds_d"], m["odds_a"]])
            p_market = dv["probs"]
            mk = lambdas_from_1x2(*p_market, rho=model.rho)
            bl = blend_lambdas((lh, la), mk, w_market)
            p_blend = list(ScoreGrid.from_lambdas(bl[0], bl[1], model.rho).result_probs())
        else:
            dv = None
            p_market = None
            p_blend = p_model

        outcome = 0 if m["hg"] > m["ag"] else (1 if m["hg"] == m["ag"] else 2)
        n_priced += 1
        for name, pp in (("model", p_model), ("blend", p_blend),
                         ("market", p_market)):
            if pp is None:
                continue
            scores[name].append(rps(pp, outcome))
            briers[name].append(brier_multiclass(pp, outcome))
            lls[name].append(log_loss(pp, outcome))
        for k in range(3):
            rel_pairs.append((p_blend[k], 1 if outcome == k else 0))

        if has_odds:
            odds = [m["odds_h"], m["odds_d"], m["odds_a"]]
            spread = max(dv["method_spread"])
            rel = min(model.reliability(m["home"]), model.reliability(m["away"]))
            for k, lab in enumerate(("1", "X", "2")):
                e = p_blend[k] * odds[k] - 1.0
                if e < min_edge:
                    continue
                sig = estimate_sigma(p_blend[k], p_market[k], spread, rel)
                f = min(kelly_with_uncertainty(p_blend[k], sig, odds[k],
                                               kelly_fraction, z=sigma_z),
                        max_per_bet)
                if f <= 0:
                    continue
                stake = f * bank
                profit = stake * (odds[k] - 1.0) if outcome == k else -stake
                bank += profit
                peak = max(peak, bank)
                max_dd = max(max_dd, (peak - bank) / peak)
                r = profit / stake if stake else 0.0
                returns.append(r)
                row = {"date": str(m["date"]), "match": "%s-%s" % (m["home"], m["away"]),
                       "pick": lab, "odds": odds[k], "prob": p_blend[k],
                       "edge": e, "stake": stake, "profit": profit,
                       "bank": bank, "won": outcome == k}
                if all(m.get(c) for c in ("close_h", "close_d", "close_a")):
                    close = [m["close_h"], m["close_d"], m["close_a"]]
                    cfair = devig(close)["fair_odds"]
                    c = clv(odds[k], close[k], cfair[k])
                    row.update({"clv_fair": c["clv_fair"],
                                "beat_close": c["beat_close"]})
                    clvs.append(c["clv_fair"])
                bets.append(row)

    def avg(v):
        return sum(v) / len(v) if v else None

    summary = {
        "n_matches_priced": n_priced,
        "rps": {k: avg(v) for k, v in scores.items()},
        "brier": {k: avg(v) for k, v in briers.items()},
        "log_loss": {k: avg(v) for k, v in lls.items()},
        "rps_edge_vs_market": (avg(scores["market"]) - avg(scores["blend"]))
        if scores["market"] and scores["blend"] else None,
        "calibration": reliability_bins(rel_pairs),
        "betting": {
            "n_bets": len(bets),
            "final_bankroll": bank,
            "roi": avg(returns),
            "yield_pct": (avg(returns) * 100.0) if returns else None,
            "max_drawdown": max_dd,
            "significance": roi_significance(returns),
            "roi_ci95": bootstrap_ci(returns) if returns else None,
            "clv_mean": avg(clvs),
            "beat_close_rate": (sum(1 for b in bets if b.get("beat_close")) /
                                len([b for b in bets if "beat_close" in b]))
            if any("beat_close" in b for b in bets) else None,
        },
        "params": {"half_life_days": half_life_days, "reg": reg,
                   "w_market": w_market, "min_edge": min_edge,
                   "kelly_fraction": kelly_fraction},
    }
    return {"summary": summary, "bets": bets, "model": model}


# --------------------------------------------------------------------------
# 15. Donnees synthetiques (tests et demonstrations)
# --------------------------------------------------------------------------

def _rpois(rng, lam):
    """Tirage Poisson (methode de Knuth) — suffisant pour lambda < 20."""
    if lam <= 0:
        return 0
    ell, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= ell:
            return k
        k += 1
        if k > 30:
            return k


def synthetic_league(n_teams=18, seasons=3, seed=42, mu=0.10, hfa=0.22,
                     rho=-0.05, start=date(2022, 8, 1)):
    """Genere un championnat fictif aux parametres CONNUS, pour verifier que
    l'estimateur retrouve bien la verite terrain."""
    rng = random.Random(seed)
    teams = ["T%02d" % i for i in range(n_teams)]
    att = {t: rng.gauss(0, 0.30) for t in teams}
    dfn = {t: rng.gauss(0, 0.25) for t in teams}
    ma = sum(att.values()) / n_teams
    md = sum(dfn.values()) / n_teams
    att = {t: v - ma for t, v in att.items()}
    dfn = {t: v - md for t, v in dfn.items()}
    matches = []
    d = start
    for s in range(seasons):
        pairs = [(h, a) for h in teams for a in teams if h != a]
        rng.shuffle(pairs)
        for k, (h, a) in enumerate(pairs):
            lh = math.exp(mu + hfa + att[h] + dfn[a])
            la = math.exp(mu + att[a] + dfn[h])
            matches.append({"date": d + timedelta(days=(k * 300) // len(pairs)),
                            "home": h, "away": a,
                            "hg": _rpois(rng, lh), "ag": _rpois(rng, la),
                            "season": "S%d" % s})
        d = d + timedelta(days=365)
    matches.sort(key=lambda m: m["date"])
    return {"matches": matches, "att": att, "def": dfn, "mu": mu, "hfa": hfa,
            "teams": teams}


def add_synthetic_odds(matches, rho=-0.05, margin=0.045, noise=0.06, seed=7,
                       att=None, dfn=None, mu=0.10, hfa=0.22):
    """Ajoute des cotes 1X2 realistes : verite + bruit + marge bookmaker."""
    rng = random.Random(seed)
    for m in matches:
        lh = math.exp(mu + hfa + att[m["home"]] + dfn[m["away"]]) * math.exp(rng.gauss(0, noise))
        la = math.exp(mu + att[m["away"]] + dfn[m["home"]]) * math.exp(rng.gauss(0, noise))
        p = list(ScoreGrid.from_lambdas(lh, la, rho).result_probs())
        tot = sum(p) * (1.0 + margin)
        m["odds_h"], m["odds_d"], m["odds_a"] = [round(tot / x, 3) for x in p]
        pc = list(ScoreGrid.from_lambdas(
            math.exp(mu + hfa + att[m["home"]] + dfn[m["away"]]),
            math.exp(mu + att[m["away"]] + dfn[m["home"]]), rho).result_probs())
        totc = sum(pc) * (1.0 + margin * 0.6)
        m["close_h"], m["close_d"], m["close_a"] = [round(totc / x, 3) for x in pc]
    return matches


# --------------------------------------------------------------------------
# 16. Auto-test
# --------------------------------------------------------------------------

class _T:
    def __init__(self):
        self.ok = 0
        self.fail = []

    def check(self, name, cond, detail=""):
        if cond:
            self.ok += 1
            print("  [OK]   %s" % name)
        else:
            self.fail.append(name)
            print("  [FAIL] %s  %s" % (name, detail))

    def close(self, name, a, b, tol, unit=""):
        self.check("%s (%.6g ~ %.6g)%s" % (name, a, b, unit), abs(a - b) <= tol,
                   "ecart=%.3g > tol=%.3g" % (abs(a - b), tol))


def selftest(verbose=True):
    t = _T()
    print("\n=== FootyEdge %s — auto-test ===\n" % __version__)

    print("[1] Distributions")
    t.close("Poisson somme=1", sum(poisson_pmf(k, 1.7) for k in range(40)), 1.0, 1e-9)
    t.close("NegBin somme=1", sum(nbinom_pmf(k, 1.7, 8.0) for k in range(200)), 1.0, 1e-6)
    t.close("NegBin moyenne", sum(k * nbinom_pmf(k, 1.7, 8.0) for k in range(200)), 1.7, 1e-4)
    t.check("NegBin plus dispersee que Poisson",
            nbinom_pmf(0, 1.7, 3.0) > poisson_pmf(0, 1.7))

    print("\n[2] Grille de scores")
    g = ScoreGrid.from_lambdas(1.6, 1.1, 0.0)
    t.close("somme=1", sum(sum(r) for r in g.m), 1.0, 1e-10)
    eh, ea = g.expected_goals()
    t.close("E[buts dom]", eh, 1.6, 2e-3)
    t.close("E[buts ext]", ea, 1.1, 2e-3)
    h, d, a = g.result_probs()
    t.close("1X2 somme=1", h + d + a, 1.0, 1e-10)
    gdc = ScoreGrid.from_lambdas(1.6, 1.1, -0.06)
    t.close("DC somme=1", sum(sum(r) for r in gdc.m), 1.0, 1e-10)
    t.check("DC augmente le nul", gdc.result_probs()[1] > d)
    t.check("DC augmente le 0-0", gdc.correct_score(0, 0) > g.correct_score(0, 0))

    print("\n[3] Marches")
    ou = g.over_under(2.5)
    t.close("O/U 2.5 complementaires", ou["over"]["win"] + ou["under"]["win"], 1.0, 1e-10)
    ou3 = g.over_under(3.0)
    t.close("O/U 3.0 w+p+l", ou3["over"]["win"] + ou3["over"]["push"] + ou3["over"]["lose"], 1.0, 1e-10)
    t.check("O/U 3.0 remboursement > 0", ou3["over"]["push"] > 0)
    ah = g.asian_handicap(-0.5)
    t.close("AH -0.5 dom.gagne = 1X2 dom", ah["home"]["win"], h, 1e-10)
    ah0 = g.asian_handicap(0.0)
    t.close("AH 0 = DNB", ah0["home"]["prob_norm"], g.draw_no_bet()["home"], 1e-10)
    ahq = g.asian_handicap(-0.25)
    m0 = g.asian_handicap(0.0)["home"]
    m5 = g.asian_handicap(-0.5)["home"]
    t.close("AH -0.25 = moyenne(0 ; -0.5)", ahq["home"]["win"],
            0.5 * (m0["win"] + m5["win"]), 1e-10)
    t.close("AH symetrie w/p/l",
            ahq["home"]["win"] + ahq["home"]["push"] + ahq["home"]["lose"], 1.0, 1e-10)
    for ln in (-2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0,
               0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
        x = g.asian_handicap(ln)
        h_, a_ = x["home"], x["away"]
        t.close("AH %+.2f : dom.gagne = ext.perd" % ln, h_["win"], a_["lose"], 1e-12)
        t.close("AH %+.2f : dom.perd = ext.gagne" % ln, h_["lose"], a_["win"], 1e-12)
        t.close("AH %+.2f : remboursements egaux" % ln, h_["push"], a_["push"], 1e-12)
        t.close("AH %+.2f : dom w+p+l = 1" % ln,
                h_["win"] + h_["push"] + h_["lose"], 1.0, 1e-12)
        t.close("AH %+.2f : ext w+p+l = 1" % ln,
                a_["win"] + a_["push"] + a_["lose"], 1.0, 1e-12)
        t.close("AH %+.2f : cotes justes sans marge" % ln,
                1.0 / h_["fair_odds"] + 1.0 / a_["fair_odds"], 1.0, 1e-9)
    # AH +0.5 : le domicile recoit +0.5, l'exterieur porte donc -0.5 et ne
    # gagne qu'en gagnant le match sec.
    t.close("AH +0.5 ext.gagne = 1X2 ext", g.asian_handicap(0.5)["away"]["win"],
            a, 1e-12)
    t.close("AH +0.5 dom.gagne = 1X + nul", g.asian_handicap(0.5)["home"]["win"],
            h + d, 1e-12)
    t.close("AH -1.5 dom = P(marge>=2)", g.asian_handicap(-1.5)["home"]["win"],
            sum(p for k, p in g.margin_dist().items() if k >= 2), 1e-12)
    b = g.btts()
    t.close("BTTS somme=1", b["yes"] + b["no"], 1.0, 1e-10)
    t.close("odd/even somme=1", sum(g.odd_even().values()), 1.0, 1e-10)
    t.close("scores exacts somme=1", sum(x["prob"] for x in g.top_scores(500)), 1.0, 1e-9)
    t.close("multigoals partition",
            g.multigoals(0, 1) + g.multigoals(2, 3) + g.multigoals(4, 99), 1.0, 1e-9)
    t.close("cote equitable AH", ah["home"]["fair_odds"],
            1.0 + ah["home"]["lose"] / ah["home"]["win"], 1e-12)

    print("\n[4] Devig")
    odds = [2.10, 3.40, 3.60]
    dv = devig(odds)
    t.close("Shin somme=1", sum(dv["probs"]), 1.0, 1e-8)
    t.check("marge > 0", dv["overround"] > 0)
    for meth in DEVIG_METHODS:
        t.close("  %s somme=1" % meth, sum(dv["all_methods"][meth]), 1.0, 1e-7)
    t.check("Shin z dans [0,1)", 0.0 <= dv["shin_z"] < 1.0)
    t.check("prob favori < implicite brute", dv["probs"][0] < 1.0 / odds[0])
    long_shot = [1.20, 7.50, 15.0]
    dvl = devig(long_shot)
    mult = dvl["all_methods"]["multiplicative"]
    shin = dvl["all_methods"]["shin"]
    t.check("Shin coupe davantage les outsiders", shin[2] < mult[2])
    dv2 = devig([1.95, 1.95])
    t.close("marche 2 issues equilibre", dv2["probs"][0], 0.5, 1e-9)

    print("\n[5] Inversion du marche")
    for (lh0, la0) in ((1.60, 1.10), (2.30, 0.75), (0.95, 1.45), (1.25, 1.25)):
        gg = ScoreGrid.from_lambdas(lh0, la0, -0.04)
        ph, pd_, pa = gg.result_probs()
        rh, ra = lambdas_from_1x2(ph, pd_, pa, rho=-0.04)
        t.close("1X2 -> lambda dom (%.2f)" % lh0, rh, lh0, 5e-3)
        t.close("1X2 -> lambda ext (%.2f)" % la0, ra, la0, 5e-3)
    gg = ScoreGrid.from_lambdas(1.75, 1.05, -0.04)
    p_ah = gg.asian_handicap(-0.5)["home"]["prob_norm"]
    p_ov = gg.over_under(2.5)["over"]["prob_norm"]
    rh, ra = lambdas_from_asian(-0.5, p_ah, 2.5, p_ov, rho=-0.04)
    t.close("asiatique -> lambda dom", rh, 1.75, 5e-3)
    t.close("asiatique -> lambda ext", ra, 1.05, 5e-3)

    print("\n[6] Fusion")
    pooled = log_pool([[0.5, 0.3, 0.2], [0.3, 0.3, 0.4]], [0.5, 0.5])
    t.close("pooling somme=1", sum(pooled), 1.0, 1e-12)
    t.check("pooling entre les deux", 0.3 < pooled[0] < 0.5)
    bl = blend_lambdas((1.6, 1.1), (1.2, 1.4), 0.0)
    t.close("w=0 -> modele", bl[0], 1.6, 1e-12)
    bl = blend_lambdas((1.6, 1.1), (1.2, 1.4), 1.0)
    t.close("w=1 -> marche", bl[0], 1.2, 1e-12)

    print("\n[7] Mi-temps / fin de match")
    hv = halves_analysis(1.6, 1.1, 0.0, 0.455)
    t.close("HT/FT somme=1", sum(hv["htft"].values()), 1.0, 1e-6)
    t.close("HT 1X2 somme=1", sum(hv["ht_1x2"].values()), 1.0, 1e-6)
    rec = (hv["htft"]["1/1"] + hv["htft"]["X/1"] + hv["htft"]["2/1"])
    t.close("FT reconstruit = FT direct", rec, h, 3e-3)

    print("\n[8] Kelly et mise")
    t.close("Kelly (p=.55, o=2)", kelly_single(0.55, 2.0), 0.10, 1e-12)
    t.close("Kelly sans edge = 0", kelly_single(0.45, 2.0), 0.0, 1e-12)
    t.close("Kelly fractionnaire", kelly_single(0.55, 2.0, fraction=0.25), 0.025, 1e-12)
    t.close("Kelly asiatique = Kelly simple si pas de push",
            kelly_asian(0.55, 0.45, 2.0), kelly_single(0.55, 2.0), 1e-12)
    t.check("push reduit le risque -> mise plus elevee",
            kelly_asian(0.50, 0.35, 2.0) > kelly_asian(0.50, 0.50, 2.0))
    t.check("decote d'incertitude reduit la mise",
            kelly_with_uncertainty(0.55, 0.03, 2.0) < kelly_single(0.55, 2.0))
    kp, ko = [0.50, 0.28, 0.22], [2.16, 3.75, 2.27]   # marge > 0, pas d'arbitrage
    ke = kelly_exclusive(kp, ko)

    def _elog(f):
        # somme(f) == 1 est realisable quand les issues sont exhaustives
        tot = sum(f)
        if tot > 1.0 + 1e-12 or any(x < 0 for x in f):
            return float("-inf")
        s_ = 0.0
        for i, pi in enumerate(kp):
            w = 1.0 - tot + f[i] * ko[i]
            if w <= 0:
                return float("-inf")
            s_ += pi * math.log(w)
        return s_

    t.check("Kelly exclusif : fractions >= 0", all(f >= -1e-12 for f in ke))
    t.check("Kelly exclusif retient les 2 issues a valeur, exclut la 3e",
            ke[0] > 0 and ke[1] > 0 and ke[2] == 0.0)
    base_e = _elog(ke)
    improved = []
    for i in range(3):
        for step in (0.05, 0.02, 0.005, 0.001, -0.001, -0.005, -0.02, -0.05):
            trial = list(ke)
            trial[i] = max(trial[i] + step, 0.0)
            if _elog(trial) > base_e + 1e-12:
                improved.append((i, step, _elog(trial) - base_e))
    t.check("Kelly exclusif : optimum verifie numeriquement (croissance log)",
            not improved, str(improved[:3]))
    t.check("Kelly exclusif mise plus que Kelly independant (couverture mutuelle)",
            sum(ke) > sum(kelly_single(p, o) for p, o in zip(kp, ko)) - 1e-12)
    arb = kelly_exclusive([0.5, 0.3, 0.2], [2.5, 4.5, 6.5])   # somme 1/o < 1
    t.close("Kelly : arbitrage -> mise totale = banque", sum(arb), 1.0, 1e-9)
    t.close("Kelly : arbitrage -> allocation proportionnelle a p", arb[1], 0.30, 1e-9)
    sp = stake_plan([{"label": "A", "prob": 0.55, "odds": 2.0},
                     {"label": "B", "prob": 0.40, "odds": 3.0}],
                    bankroll=1000, kelly_fraction=0.25, max_total=0.05)
    t.check("exposition totale plafonnee", sp["total_exposure"] <= 0.05 + 1e-9)
    t.check("mises positives", all(x["stake"] >= 0 for x in sp["bets"]))

    print("\n[9] Metriques")
    t.close("RPS parfait", rps([1, 0, 0], 0), 0.0, 1e-12)
    t.close("RPS pire cas", rps([0, 0, 1], 0), 1.0, 1e-12)
    t.check("RPS penalise l'ordre", rps([0, 1, 0], 0) < rps([0, 0, 1], 0))
    t.close("Brier parfait", brier_multiclass([1, 0, 0], 0), 0.0, 1e-12)
    t.close("log-loss uniforme", log_loss([1 / 3] * 3, 0), math.log(3), 1e-9)
    rb = reliability_bins([(0.5, 1), (0.5, 0), (0.9, 1), (0.9, 1)])
    t.check("ECE dans [0,1]", 0 <= rb["ece"] <= 1)
    c = clv(2.10, 2.00, 1.95)
    t.check("CLV positif quand on bat la cloture", c["clv_fair"] > 0 and c["beat_close"])
    ci = bootstrap_ci([0.1, -0.2, 0.3, 0.05, -0.1] * 20)
    t.check("IC bootstrap encadre le point", ci["lo"] <= ci["point"] <= ci["hi"])

    print("\n[10] Estimation des forces (donnees synthetiques)")
    syn = synthetic_league(n_teams=18, seasons=3, seed=42)
    model = fit_dixon_coles(syn["matches"], half_life_days=100000, reg=0.5,
                            max_iter=800, lr=0.05)
    t.close("avantage terrain retrouve", model.home_adv, syn["hfa"], 0.06)
    t.close("mu retrouve", model.mu, syn["mu"], 0.08)
    corr_a = _corr([syn["att"][x] for x in syn["teams"]],
                   [model.att[x] for x in syn["teams"]])
    corr_d = _corr([syn["def"][x] for x in syn["teams"]],
                   [model.dfn[x] for x in syn["teams"]])
    t.check("correlation attaque > 0.90 (%.3f)" % corr_a, corr_a > 0.90)
    t.check("correlation defense > 0.85 (%.3f)" % corr_d, corr_d > 0.85)
    t.check("rho ~ 0 sur donnees independantes (%.4f)" % model.rho,
            abs(model.rho) < 0.06)
    t.check("table triee", model.table()[0]["rank"] == 1)

    print("\n[11] Tarification complete")
    res = price_match(lam_home=1.55, lam_away=1.15, rho=-0.05,
                      market={"1x2": [2.20, 3.40, 3.30]}, w_market=0.5,
                      offered={"1x2": {"home": 2.35, "draw": 3.40, "away": 3.30},
                               "ou": {"2.5": {"over": 1.95, "under": 1.95}},
                               "ah": {"-0.5": {"home": 2.05, "away": 1.85}}},
                      bankroll=1000, kelly_fraction=0.25)
    bk = res["book"]
    t.close("livre 1X2 somme=1",
            sum(bk["1x2"][k]["prob"] for k in ("home", "draw", "away")), 1.0, 1e-9)
    t.check("lambdas fusionnes entre modele et marche",
            min(res["lambdas_model"][0], res["lambdas_market"][0])
            <= res["lambdas_used"][0]
            <= max(res["lambdas_model"][0], res["lambdas_market"][0]) + 1e-12)
    t.check("paris de valeur detectes", any(v["value"] for v in res["value_bets"]))
    t.check("plan de mise coherent",
            res["stake_plan"]["total_exposure"] <= 0.10 + 1e-9)
    t.check("sigma > 0 sur tous les paris", all(v["sigma"] > 0 for v in res["value_bets"]))
    t.close("pas de penalite quand modele et marche s'accordent",
            res["disagreement_penalty"], 1.0, 1e-9)
    res_far = price_match(lam_home=2.60, lam_away=0.60, rho=-0.05,
                          market={"1x2": [2.20, 3.40, 3.30]}, w_market=0.5,
                          offered={"1x2": {"home": 2.35, "draw": 3.40, "away": 3.30}})
    t.check("penalite active en cas de fort desaccord (%.2f)"
            % res_far["disagreement_penalty"], res_far["disagreement_penalty"] < 0.75)
    t.check("penalite reduit la mise",
            res_far["stake_plan"]["kelly_fraction"] < 0.25)

    print("\n[12] Simulation de saison")
    fixtures = [{"home": a, "away": b} for a in syn["teams"][:6]
                for b in syn["teams"][:6] if a != b]
    sim = simulate_season(model, fixtures, n_sims=600, seed=3, promo=2, releg=2)
    t.close("distribution de positions somme=1",
            sum(sim["teams"][0]["position_dist"]), 1.0, 1e-9)
    t.close("somme des P(champion)=1",
            sum(x["p_champion"] for x in sim["teams"]), 1.0, 1e-9)

    print("\n[13] Combines correles")
    gpar = ScoreGrid.from_lambdas(1.9, 0.9, -0.05)
    legs = [{"grid": gpar, "match_id": "m1", "test": lambda hg, ag: hg > ag},
            {"grid": gpar, "match_id": "m1", "test": lambda hg, ag: hg + ag > 2.5}]
    pl = simulate_parlay(legs, n_sims=40000, seed=5)
    t.check("prob combine dans [0,1]", 0 <= pl["prob"] <= 1)
    t.check("correlation detectee (%.4f)" % pl["correlation_effect"],
            abs(pl["correlation_effect"]) > 3 * pl["std_error"])

    print("\n[14] Backtest walk-forward")
    syn2 = synthetic_league(n_teams=14, seasons=2, seed=9)
    add_synthetic_odds(syn2["matches"], att=syn2["att"], dfn=syn2["def"],
                       mu=syn2["mu"], hfa=syn2["hfa"], noise=0.10)
    bt = backtest(syn2["matches"], min_train=180, refit_every_days=45,
                  max_iter=200, warm_iter=60, min_edge=0.04, verbose=False)
    s = bt["summary"]
    t.check("matchs tarifes > 0", s["n_matches_priced"] > 0)
    t.check("RPS modele dans [0,1]", 0 < s["rps"]["model"] < 1)
    t.check("RPS marche dans [0,1]", 0 < s["rps"]["market"] < 1)
    t.check("fusion >= meilleur des deux - epsilon",
            s["rps"]["blend"] <= max(s["rps"]["model"], s["rps"]["market"]) + 1e-6)
    t.check("aucune fuite : ECE calcule", s["calibration"]["n"] > 0)

    print("\n[15] Chargement CSV")
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_tmp.csv")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,PSH,PSD,PSA,PSCH,PSCD,PSCA\n")
        fh.write("F1,12/08/2024,Lyon,Nice,2,1,1.95,3.60,3.90,1.90,3.65,4.00\n")
        fh.write("F1,13/08/2024,Lille,Brest,0,0,1.70,3.80,4.80,1.72,3.75,4.90\n")
    rows = load_matches_csv(tmp)
    t.check("CSV football-data lu", len(rows) == 2 and rows[0]["home"] == "Lyon")
    t.check("cotes lues", abs(rows[0]["odds_h"] - 1.95) < 1e-9)
    t.check("cloture lue", abs(rows[0]["close_a"] - 4.00) < 1e-9)
    t.check("date parsee", rows[0]["date"] == date(2024, 8, 12))
    os.remove(tmp)

    print("\n" + "=" * 62)
    total = t.ok + len(t.fail)
    print("Resultat : %d/%d tests reussis" % (t.ok, total))
    if t.fail:
        print("ECHECS :")
        for f in t.fail:
            print("   - %s" % f)
    print("=" * 62 + "\n")
    return len(t.fail) == 0


def _corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy) if dx and dy else 0.0


# --------------------------------------------------------------------------
# 17. Interface en ligne de commande
# --------------------------------------------------------------------------

def _load_json_arg(value):
    if value is None:
        return None
    if os.path.exists(value):
        with open(value, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(value)


def _cmd_devig(a):
    out = devig(a.odds, method=a.method)
    print(write_json(out))


def _cmd_price(a):
    market = _load_json_arg(a.market)
    if a.market_1x2:
        market = dict(market or {}, **{"1x2": a.market_1x2})
    res = price_match(lam_home=a.lh, lam_away=a.la, rho=a.rho, market=market,
                      w_market=a.w, offered=_load_json_arg(a.offered),
                      bankroll=a.bankroll, kelly_fraction=a.kelly,
                      min_edge=a.min_edge)
    if a.out:
        write_json(res, a.out)
    print(render_match(res) if a.brief else write_json(res))


def _cmd_invert(a):
    if a.ah is not None and a.ou is not None:
        dv_ah = devig([a.ah[1], a.ah[2]])
        dv_ou = devig([a.ou[1], a.ou[2]])
        lh, la = lambdas_from_asian(a.ah[0], dv_ah["probs"][0],
                                    a.ou[0], dv_ou["probs"][0], rho=a.rho)
        src = "asian"
    elif a.odds_1x2:
        dv = devig(a.odds_1x2)
        lh, la = lambdas_from_1x2(*dv["probs"], rho=a.rho)
        src = "1x2"
    else:
        raise SystemExit("fournir --1x2 ou (--ah et --ou)")
    g = ScoreGrid.from_lambdas(lh, la, a.rho)
    print(write_json({"source": src, "lambda_home": lh, "lambda_away": la,
                      "supremacy": lh - la, "total": lh + la,
                      "book": build_book(g)}, a.out))


def _cmd_fit(a):
    matches = load_matches_csv(a.csv)
    if a.league:
        matches = [m for m in matches if str(m.get("league", "")) == a.league]
    model = fit_dixon_coles(matches, half_life_days=a.half_life, reg=a.reg,
                            max_iter=a.iters, target=a.target,
                            verbose=a.verbose)
    write_json(model.to_dict(), a.out)
    print("Modele ajuste sur %d matchs, %d equipes -> %s"
          % (model.meta["n_matches"], len(model.teams), a.out))
    print("mu=%.4f  avantage_terrain=%.4f (x%.3f sur lambda_dom)  rho=%.4f"
          % (model.mu, model.home_adv, math.exp(model.home_adv), model.rho))
    for r in model.table()[:a.top]:
        print("  %2d. %-24s note=%+.3f  att=%+.3f  def=%+.3f  (n=%d)"
              % (r["rank"], r["team"], r["rating"], r["attack"], r["defense"],
                 r["matches"]))


def _cmd_table(a):
    model = DixonColesModel.from_dict(_load_json_arg(a.model))
    rows = model.table()
    print("%-4s %-26s %8s %8s %8s %6s" % ("#", "equipe", "note", "att", "def", "n"))
    for r in rows[:a.top]:
        print("%-4d %-26s %+8.3f %+8.3f %+8.3f %6d"
              % (r["rank"], r["team"], r["rating"], r["attack"],
                 r["defense"], r["matches"]))


def _cmd_predict(a):
    model = DixonColesModel.from_dict(_load_json_arg(a.model))
    market = _load_json_arg(a.market)
    if a.market_1x2:
        market = dict(market or {}, **{"1x2": a.market_1x2})
    res = price_match(model=model, home=a.home, away=a.away, rho=model.rho,
                      market=market, w_market=a.w, neutral=a.neutral,
                      adj_home=a.adj_home, adj_away=a.adj_away,
                      offered=_load_json_arg(a.offered), bankroll=a.bankroll,
                      kelly_fraction=a.kelly, min_edge=a.min_edge)
    if a.out:
        write_json(res, a.out)
    print(render_match(res, a.home, a.away) if a.brief else write_json(res))


def _cmd_backtest(a):
    matches = load_matches_csv(a.csv)
    if a.league:
        matches = [m for m in matches if str(m.get("league", "")) == a.league]
    bt = backtest(matches, min_train=a.min_train, refit_every_days=a.refit,
                  half_life_days=a.half_life, reg=a.reg, w_market=a.w,
                  min_edge=a.min_edge, kelly_fraction=a.kelly,
                  bankroll=a.bankroll, verbose=a.verbose)
    s = bt["summary"]
    print(write_json(s, a.out))
    if a.bets_out:
        with open(a.bets_out, "w", encoding="utf-8", newline="") as fh:
            if bt["bets"]:
                w = csv.DictWriter(fh, fieldnames=list(bt["bets"][0].keys()))
                w.writeheader()
                w.writerows(bt["bets"])
        print("Journal des paris -> %s" % a.bets_out, file=sys.stderr)


def _cmd_season(a):
    model = DixonColesModel.from_dict(_load_json_arg(a.model))
    fixtures = _load_json_arg(a.fixtures)
    standings = _load_json_arg(a.standings) if a.standings else None
    sim = simulate_season(model, fixtures, standings, n_sims=a.sims,
                          promo=a.promo, releg=a.releg,
                          playoff=tuple(a.playoff) if a.playoff else None)
    print(write_json(sim, a.out))


def _cmd_demo(a):
    print("--- Demonstration FootyEdge ---\n")
    print("1) Un book affiche 1X2 = 2.10 / 3.40 / 3.60. Que vaut vraiment le match ?")
    dv = devig([2.10, 3.40, 3.60])
    print("   marge = %.2f%%  |  probas Shin = %s"
          % (dv["margin_pct"], ["%.3f" % p for p in dv["probs"]]))
    lh, la = lambdas_from_1x2(*dv["probs"], rho=-0.04)
    print("   -> lambda = (%.3f, %.3f) ; suprematie %+.3f ; total %.3f"
          % (lh, la, lh - la, lh + la))
    g = ScoreGrid.from_lambdas(lh, la, -0.04)
    print("\n2) Tarif coherent des marches derives :")
    bk = build_book(g)
    print("   O/U 2.5     : over %.4f (cote juste %.3f) / under %.4f (%.3f)"
          % (bk["over_under"]["2.50"]["over"]["win"],
             bk["over_under"]["2.50"]["over"]["fair_odds"],
             bk["over_under"]["2.50"]["under"]["win"],
             bk["over_under"]["2.50"]["under"]["fair_odds"]))
    print("   BTTS        : oui %.4f (%.3f)"
          % (bk["btts"]["yes"]["prob"], bk["btts"]["yes"]["fair"]))
    print("   AH -0.5 dom : %.4f (%.3f)"
          % (bk["asian_handicap"]["-0.50"]["home"]["win"],
             bk["asian_handicap"]["-0.50"]["home"]["fair_odds"]))
    print("   Top scores  : " + ", ".join(
        "%s %.3f" % (x["score"], x["prob"]) for x in bk["top_scores"][:5]))
    print("\n3) Un autre book propose BTTS oui a 2.05. Valeur ?")
    p = bk["btts"]["yes"]["prob"]
    e = p * 2.05 - 1
    print("   proba %.4f -> cote juste %.3f | edge %+.2f%% | Kelly 1/4 = %.2f%% de banque"
          % (p, 1 / p, 100 * e, 100 * kelly_single(p, 2.05, 0.25)))
    print("\n(voir sources/ pour le protocole complet)")


def build_parser():
    p = argparse.ArgumentParser(
        prog="footyedge",
        description="Moteur quantitatif de pronostic football (zero dependance).")
    p.add_argument("--version", action="version", version="FootyEdge " + __version__)
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("selftest", help="verifie l'integrite du moteur")
    s.set_defaults(func=lambda a: sys.exit(0 if selftest() else 1))

    s = sub.add_parser("demo", help="demonstration guidee")
    s.set_defaults(func=_cmd_demo)

    s = sub.add_parser("devig", help="retire la marge d'un jeu de cotes")
    s.add_argument("--odds", type=float, nargs="+", required=True)
    s.add_argument("--method", default="auto", choices=("auto",) + DEVIG_METHODS)
    s.set_defaults(func=_cmd_devig)

    s = sub.add_parser("invert", help="cotes -> lambdas -> tarif complet")
    s.add_argument("--1x2", dest="odds_1x2", type=float, nargs=3)
    s.add_argument("--ah", type=float, nargs=3, metavar=("LIGNE", "DOM", "EXT"))
    s.add_argument("--ou", type=float, nargs=3, metavar=("LIGNE", "OVER", "UNDER"))
    s.add_argument("--rho", type=float, default=-0.04)
    s.add_argument("--out")
    s.set_defaults(func=_cmd_invert)

    s = sub.add_parser("price", help="tarifie un match a partir de lambdas")
    s.add_argument("--lh", type=float, required=True)
    s.add_argument("--la", type=float, required=True)
    s.add_argument("--rho", type=float, default=-0.04)
    s.add_argument("--market")
    s.add_argument("--market-1x2", type=float, nargs=3)
    s.add_argument("--offered")
    s.add_argument("--w", type=float, default=0.5)
    s.add_argument("--bankroll", type=float, default=1000.0)
    s.add_argument("--kelly", type=float, default=0.25)
    s.add_argument("--min-edge", type=float, default=0.02)
    s.add_argument("--brief", action="store_true", help="fiche lisible au lieu du JSON")
    s.add_argument("--out")
    s.set_defaults(func=_cmd_price)

    s = sub.add_parser("fit", help="ajuste le modele sur un CSV historique")
    s.add_argument("--csv", required=True)
    s.add_argument("--out", default="model.json")
    s.add_argument("--league")
    s.add_argument("--half-life", type=float, default=180.0)
    s.add_argument("--reg", type=float, default=1.0)
    s.add_argument("--iters", type=int, default=600)
    s.add_argument("--target", default="goals", choices=("goals", "xg", "blend"))
    s.add_argument("--top", type=int, default=20)
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=_cmd_fit)

    s = sub.add_parser("table", help="affiche le classement des forces")
    s.add_argument("--model", required=True)
    s.add_argument("--top", type=int, default=30)
    s.set_defaults(func=_cmd_table)

    s = sub.add_parser("predict", help="tarifie un match du modele")
    s.add_argument("--model", required=True)
    s.add_argument("--home", required=True)
    s.add_argument("--away", required=True)
    s.add_argument("--market")
    s.add_argument("--market-1x2", type=float, nargs=3)
    s.add_argument("--offered")
    s.add_argument("--w", type=float, default=0.6)
    s.add_argument("--neutral", action="store_true")
    s.add_argument("--adj-home", type=float, default=1.0)
    s.add_argument("--adj-away", type=float, default=1.0)
    s.add_argument("--bankroll", type=float, default=1000.0)
    s.add_argument("--kelly", type=float, default=0.25)
    s.add_argument("--min-edge", type=float, default=0.02)
    s.add_argument("--brief", action="store_true", help="fiche lisible au lieu du JSON")
    s.add_argument("--out")
    s.set_defaults(func=_cmd_predict)

    s = sub.add_parser("backtest", help="validation temporelle + simulation de mise")
    s.add_argument("--csv", required=True)
    s.add_argument("--league")
    s.add_argument("--min-train", type=int, default=200)
    s.add_argument("--refit", type=int, default=21)
    s.add_argument("--half-life", type=float, default=180.0)
    s.add_argument("--reg", type=float, default=1.0)
    s.add_argument("--w", type=float, default=0.6)
    s.add_argument("--min-edge", type=float, default=0.03)
    s.add_argument("--kelly", type=float, default=0.25)
    s.add_argument("--bankroll", type=float, default=1000.0)
    s.add_argument("--out")
    s.add_argument("--bets-out")
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=_cmd_backtest)

    s = sub.add_parser("season", help="simulation Monte-Carlo de fin de saison")
    s.add_argument("--model", required=True)
    s.add_argument("--fixtures", required=True)
    s.add_argument("--standings")
    s.add_argument("--sims", type=int, default=10000)
    s.add_argument("--promo", type=int, default=2)
    s.add_argument("--releg", type=int, default=3)
    s.add_argument("--playoff", type=int, nargs=2)
    s.add_argument("--out")
    s.set_defaults(func=_cmd_season)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
