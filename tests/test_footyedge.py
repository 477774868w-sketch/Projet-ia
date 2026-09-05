#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests independants du moteur FootyEdge.

Complementaires de l'auto-test embarque (`footyedge.py selftest`) : on y
verifie surtout des INVARIANTS sur de larges plages de parametres, des cas
limites et la robustesse aux entrees degenerees.

Executable de deux facons :
    python3 tests/test_footyedge.py        (aucune dependance)
    pytest tests/test_footyedge.py         (si pytest est installe)
"""

import math
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "engine"))
import footyedge as fe  # noqa: E402

LAMBDA_GRID = [(0.35, 0.30), (0.90, 0.75), (1.60, 1.10), (2.30, 0.55),
               (1.25, 1.25), (3.40, 0.45), (0.60, 2.10), (2.75, 2.40)]
RHOS = [0.0, -0.03, -0.08, 0.04]
LINES = [-2.0, -1.75, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5,
         0.75, 1.0, 1.25, 1.75, 2.0]


# ---------------------------------------------------------------- invariants

def test_grid_is_a_probability_distribution():
    for lh, la in LAMBDA_GRID:
        for rho in RHOS:
            g = fe.ScoreGrid.from_lambdas(lh, la, rho)
            total = sum(sum(r) for r in g.m)
            assert abs(total - 1.0) < 1e-10, (lh, la, rho, total)
            assert all(p >= 0.0 for row in g.m for p in row)


def test_marginals_match_lambdas_without_dc():
    """Sans correction DC, les marginales doivent redonner exactement lambda."""
    for lh, la in LAMBDA_GRID:
        g = fe.ScoreGrid.from_lambdas(lh, la, 0.0, max_goals=20)
        eh, ea = g.expected_goals()
        assert abs(eh - lh) < 1e-6, (lh, eh)
        assert abs(ea - la) < 1e-6, (la, ea)


def test_1x2_partitions_the_space():
    for lh, la in LAMBDA_GRID:
        for rho in RHOS:
            h, d, a = fe.ScoreGrid.from_lambdas(lh, la, rho).result_probs()
            assert abs(h + d + a - 1.0) < 1e-10
            assert min(h, d, a) >= 0.0


def test_asian_handicap_two_sided_coherence():
    """Invariant fondamental : les deux camps forment un marche sans marge."""
    for lh, la in LAMBDA_GRID:
        g = fe.ScoreGrid.from_lambdas(lh, la, -0.05)
        for ln in LINES:
            x = g.asian_handicap(ln)
            hm, aw = x["home"], x["away"]
            assert abs(hm["win"] - aw["lose"]) < 1e-12, (lh, la, ln)
            assert abs(hm["lose"] - aw["win"]) < 1e-12, (lh, la, ln)
            assert abs(hm["push"] - aw["push"]) < 1e-12, (lh, la, ln)
            assert abs(hm["win"] + hm["push"] + hm["lose"] - 1.0) < 1e-12
            inv = 1.0 / hm["fair_odds"] + 1.0 / aw["fair_odds"]
            assert abs(inv - 1.0) < 1e-9, (lh, la, ln, inv)


def test_asian_handicap_is_monotone_in_the_line():
    """Plus le handicap est genereux, plus le camp domicile gagne souvent."""
    g = fe.ScoreGrid.from_lambdas(1.6, 1.1, -0.05)
    prev = -1.0
    for ln in sorted(LINES):
        w = g.asian_handicap(ln)["home"]["prob_norm"]
        assert w >= prev - 1e-12, (ln, w, prev)
        prev = w


def test_quarter_lines_are_half_stakes():
    g = fe.ScoreGrid.from_lambdas(1.7, 1.2, -0.05)
    for q in (-1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75):
        lo, hi = q - 0.25, q + 0.25
        for side in ("home", "away"):
            got = g.asian_handicap(q)[side]["win"]
            exp = 0.5 * (g.asian_handicap(lo)[side]["win"]
                         + g.asian_handicap(hi)[side]["win"])
            assert abs(got - exp) < 1e-12, (q, side, got, exp)


def test_over_under_monotone_and_complementary():
    g = fe.ScoreGrid.from_lambdas(1.6, 1.1, -0.05)
    prev = 2.0
    for ln in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        ou = g.over_under(ln)
        assert abs(ou["over"]["win"] + ou["under"]["win"] - 1.0) < 1e-12
        assert ou["over"]["win"] <= prev + 1e-12
        prev = ou["over"]["win"]


def test_total_distribution_is_poisson_when_independent():
    """Sans DC, le total est exactement une loi de Poisson de moyenne T."""
    lh, la = 1.55, 1.20
    g = fe.ScoreGrid.from_lambdas(lh, la, 0.0, max_goals=20)
    td = g.total_dist()
    for k in range(8):
        assert abs(td.get(k, 0.0) - fe.poisson_pmf(k, lh + la)) < 1e-9, k


def test_closed_forms_match_the_grid():
    """Verifie les formules du mode degrade (02_MOTEUR_QUANTITATIF §8)."""
    for lh, la in LAMBDA_GRID:
        g = fe.ScoreGrid.from_lambdas(lh, la, 0.0, max_goals=20)
        T = lh + la
        assert abs(g.clean_sheet("home") - math.exp(-la)) < 1e-9
        assert abs(g.clean_sheet("away") - math.exp(-lh)) < 1e-9
        btts = 1 - math.exp(-lh) - math.exp(-la) + math.exp(-T)
        assert abs(g.btts()["yes"] - btts) < 1e-9
        over25 = 1 - math.exp(-T) * (1 + T + T * T / 2)
        assert abs(g.over_under(2.5)["over"]["win"] - over25) < 1e-9


def test_dixon_coles_raises_draw_probability():
    for lh, la in LAMBDA_GRID:
        base = fe.ScoreGrid.from_lambdas(lh, la, 0.0).result_probs()[1]
        corr = fe.ScoreGrid.from_lambdas(lh, la, -0.06).result_probs()[1]
        assert corr > base, (lh, la)


def test_negative_binomial_fattens_the_tails():
    lh, la = 3.20, 0.60
    gp = fe.ScoreGrid.from_lambdas(lh, la, 0.0)
    gn = fe.ScoreGrid.from_lambdas(lh, la, 0.0, shape_home=8, shape_away=8)
    assert gn.result_probs()[2] > gp.result_probs()[2]          # plus d'exploits
    assert gn.over_under(5.5)["over"]["win"] > gp.over_under(5.5)["over"]["win"]
    assert gn.result_probs()[1] > gp.result_probs()[1]          # plus de nuls


# --------------------------------------------------------------------- devig

def test_devig_all_methods_are_valid_distributions():
    rng = random.Random(3)
    for _ in range(60):
        raw = [rng.uniform(0.1, 0.7) for _ in range(3)]
        total = sum(raw)
        probs = [x / total for x in raw]                 # vraies probabilites
        margin = rng.uniform(0.01, 0.12)
        odds = [max(1.0 / (q * (1.0 + margin)), 1.02) for q in probs]
        dv = fe.devig(odds)
        for name, probs in dv["all_methods"].items():
            assert abs(sum(probs) - 1.0) < 1e-6, name
            assert all(0.0 < q < 1.0 for q in probs), name


def test_devig_removes_margin_and_preserves_ranking():
    odds = [1.80, 3.90, 4.60]
    dv = fe.devig(odds)
    assert dv["overround"] > 0
    for name, probs in dv["all_methods"].items():
        assert probs[0] < 1.0 / odds[0], name          # marge retiree
        assert probs[0] > probs[1] > probs[2], name    # ordre preserve


def test_shin_discounts_longshots_more_than_multiplicative():
    dv = fe.devig([1.15, 8.50, 19.0])
    assert dv["all_methods"]["shin"][2] < dv["all_methods"]["multiplicative"][2]
    assert 0.0 <= dv["shin_z"] < 1.0


def test_devig_rejects_invalid_odds():
    for bad in ([1.0, 3.0, 4.0], [0.9, 3.0, 4.0], [2.0, -1.0]):
        try:
            fe.devig(bad)
        except ValueError:
            continue
        raise AssertionError("cotes invalides acceptees: %r" % (bad,))


# ----------------------------------------------------------------- inversion

def test_market_inversion_round_trip():
    for lh, la in LAMBDA_GRID:
        if min(lh, la) < 0.30:
            continue
        for rho in (0.0, -0.05):
            g = fe.ScoreGrid.from_lambdas(lh, la, rho)
            rh, ra = fe.lambdas_from_1x2(*g.result_probs(), rho=rho)
            assert abs(rh - lh) < 6e-3, (lh, la, rho, rh)
            assert abs(ra - la) < 6e-3, (lh, la, rho, ra)


def test_asian_inversion_round_trip():
    for lh, la in [(1.75, 1.05), (1.20, 1.35), (2.40, 0.80)]:
        g = fe.ScoreGrid.from_lambdas(lh, la, -0.04)
        p_ah = g.asian_handicap(-0.5)["home"]["prob_norm"]
        p_ov = g.over_under(2.5)["over"]["prob_norm"]
        rh, ra = fe.lambdas_from_asian(-0.5, p_ah, 2.5, p_ov, rho=-0.04)
        assert abs(rh - lh) < 6e-3 and abs(ra - la) < 6e-3, (lh, la, rh, ra)


# --------------------------------------------------------------------- kelly

def _expected_log(fractions, probs, odds):
    """
    Croissance logarithmique attendue.

    Attention : somme(f) == 1 est REALISABLE quand les issues sont
    exhaustives (il n'existe alors aucun scenario ou aucun pari ne gagne).
    Exclure ce point frontiere ferait echouer a tort le cas d'arbitrage.
    """
    tot = sum(fractions)
    if tot > 1.0 + 1e-12 or any(f < 0 for f in fractions):
        return float("-inf")
    s = 0.0
    for p, o, f in zip(probs, odds, fractions):
        w = 1.0 - tot + f * o
        if w <= 0:
            return float("-inf")
        s += p * math.log(w)
    return s


def test_kelly_exclusive_is_numerically_optimal():
    cases = [([0.50, 0.28, 0.22], [2.16, 3.75, 2.27]),
             ([0.45, 0.30, 0.25], [2.40, 3.10, 3.60]),
             ([0.62, 0.22, 0.16], [1.70, 4.20, 5.80])]
    for probs, odds in cases:
        f = fe.kelly_exclusive(probs, odds)
        base = _expected_log(f, probs, odds)
        for i in range(len(f)):
            for step in (0.05, 0.01, 0.002, -0.002, -0.01, -0.05):
                trial = list(f)
                trial[i] = max(trial[i] + step, 0.0)
                assert _expected_log(trial, probs, odds) <= base + 1e-12, \
                    (probs, odds, i, step)


def test_kelly_is_monotone_in_edge_and_zero_without_edge():
    prev = -1.0
    for p in [0.50, 0.52, 0.55, 0.60, 0.70]:
        f = fe.kelly_single(p, 2.0)
        assert f >= prev
        prev = f
    assert fe.kelly_single(0.49, 2.0) == 0.0
    assert fe.kelly_single(0.99, 1.0) == 0.0        # cote invalide


def test_kelly_asian_rewards_push_probability():
    """A esperance egale, un pari remboursable supporte une mise superieure."""
    dry = fe.kelly_asian(0.55, 0.45, 2.0)
    with_push = fe.kelly_asian(0.50, 0.35, 2.0)     # meme edge, push 15 %
    assert with_push > dry


def test_stake_plan_respects_every_cap():
    bets = [{"label": "b%d" % i, "prob": 0.55, "odds": 2.2, "group": "g%d" % (i % 2)}
            for i in range(8)]
    plan = fe.stake_plan(bets, bankroll=1000, kelly_fraction=0.25,
                         max_per_bet=0.015, max_total=0.05,
                         correlation_haircut=0.35)
    assert plan["total_exposure"] <= 0.05 + 1e-9
    assert all(b["fraction"] <= 0.015 + 1e-9 for b in plan["bets"])
    assert all(b["stake"] >= 0 for b in plan["bets"])


def test_uncertainty_haircut_is_monotone():
    prev = 1.0
    for sigma in [0.0, 0.01, 0.02, 0.05, 0.10]:
        f = fe.kelly_with_uncertainty(0.55, sigma, 2.0)
        assert f <= prev + 1e-12
        prev = f
    assert fe.kelly_with_uncertainty(0.55, 0.20, 2.0) == 0.0


# ------------------------------------------------------------------ metriques

def test_rps_respects_outcome_ordering():
    """Se tromper d'une issue adjacente doit couter moins que de deux crans."""
    near = fe.rps([0.0, 1.0, 0.0], 0)      # on annonce X, c'est 1
    far = fe.rps([0.0, 0.0, 1.0], 0)       # on annonce 2, c'est 1
    assert near < far
    assert abs(fe.rps([1.0, 0.0, 0.0], 0)) < 1e-12
    assert abs(fe.rps([0.0, 0.0, 1.0], 0) - 1.0) < 1e-12


def test_metrics_reward_the_truth():
    """Une prevision plus proche de la verite doit obtenir un meilleur score."""
    good, bad = [0.60, 0.25, 0.15], [0.20, 0.25, 0.55]
    for metric in (fe.rps, fe.brier_multiclass, fe.log_loss):
        assert metric(good, 0) < metric(bad, 0), metric.__name__


def test_reliability_bins_detect_miscalibration():
    perfect = [(0.7, 1)] * 70 + [(0.7, 0)] * 30
    biased = [(0.7, 1)] * 40 + [(0.7, 0)] * 60
    assert fe.reliability_bins(perfect)["ece"] < 0.02
    assert fe.reliability_bins(biased)["ece"] > 0.25


def test_clv_signs():
    assert fe.clv(2.20, 2.00, 1.95)["clv_fair"] > 0
    assert fe.clv(1.80, 2.00, 1.95)["clv_fair"] < 0
    assert fe.clv(2.20, 2.00)["beat_close"] is True


def test_roi_significance_and_bootstrap():
    rng = random.Random(11)
    returns = [1.0 if rng.random() < 0.53 else -1.0 for _ in range(4000)]
    sig = fe.roi_significance(returns)
    assert sig["n"] == 4000 and sig["t"] is not None
    ci = fe.bootstrap_ci(returns, n_boot=400)
    assert ci["lo"] <= ci["point"] <= ci["hi"]


# ------------------------------------------------------------------- modele

def _fit_corr(seasons, seed, n_teams=16):
    syn = fe.synthetic_league(n_teams=n_teams, seasons=seasons, seed=seed)
    model = fe.fit_dixon_coles(syn["matches"], half_life_days=1e6,
                               reg=0.5, max_iter=700)
    teams = syn["teams"]
    return (_corr([syn["att"][t] for t in teams], [model.att[t] for t in teams]),
            _corr([syn["def"][t] for t in teams], [model.dfn[t] for t in teams]),
            model, syn)


def test_fit_recovers_synthetic_truth_on_several_seeds():
    for seed in (7, 21, 99):
        ca, cd, model, syn = _fit_corr(3, seed)
        assert ca > 0.85, (seed, ca)
        assert cd > 0.85, (seed, cd)
        assert abs(model.home_adv - syn["hfa"]) < 0.08, (seed, model.home_adv)


def test_fit_is_consistent_more_data_means_better_estimates():
    """Test de consistance : l'erreur d'estimation doit decroitre avec n."""
    small_a, small_d, _, _ = _fit_corr(2, 7)
    large_a, large_d, _, _ = _fit_corr(6, 7)
    assert large_a > small_a, (small_a, large_a)
    assert large_d > small_d, (small_d, large_d)
    assert large_a > 0.93 and large_d > 0.93, (large_a, large_d)


def test_warm_start_converges_to_the_same_place():
    syn = fe.synthetic_league(n_teams=14, seasons=2, seed=5)
    cold = fe.fit_dixon_coles(syn["matches"], max_iter=600, reg=1.0)
    warm = fe.fit_dixon_coles(syn["matches"], max_iter=150, reg=1.0,
                              init_model=cold)
    for t in syn["teams"]:
        assert abs(cold.att[t] - warm.att[t]) < 0.05, t


def test_regularisation_shrinks_ratings():
    syn = fe.synthetic_league(n_teams=14, seasons=1, seed=13)
    loose = fe.fit_dixon_coles(syn["matches"], reg=0.2, max_iter=500)
    tight = fe.fit_dixon_coles(syn["matches"], reg=6.0, max_iter=500)
    spread = lambda m: max(m.att.values()) - min(m.att.values())
    assert spread(tight) < spread(loose)


def test_unknown_team_falls_back_to_league_average():
    syn = fe.synthetic_league(n_teams=12, seasons=1, seed=4)
    model = fe.fit_dixon_coles(syn["matches"], max_iter=300)
    assert not model.known("Equipe Inexistante")
    lh, la = model.lambdas("Equipe Inexistante", "Autre Inconnue")
    assert 0.2 < lh < 5.0 and 0.2 < la < 5.0
    assert lh > la                                   # avantage du terrain


def test_model_serialisation_round_trip():
    syn = fe.synthetic_league(n_teams=12, seasons=1, seed=6)
    m1 = fe.fit_dixon_coles(syn["matches"], max_iter=300)
    m2 = fe.DixonColesModel.from_dict(m1.to_dict())
    a1 = m1.lambdas(syn["teams"][0], syn["teams"][1])
    a2 = m2.lambdas(syn["teams"][0], syn["teams"][1])
    assert abs(a1[0] - a2[0]) < 1e-12 and abs(a1[1] - a2[1]) < 1e-12


def test_elo_tracks_dixon_coles():
    syn = fe.synthetic_league(n_teams=16, seasons=3, seed=8)
    dc = fe.fit_dixon_coles(syn["matches"], half_life_days=1e6, max_iter=600)
    elo = fe.EloRatings().fit(syn["matches"])
    teams = syn["teams"]
    c = _corr([dc.att[t] - dc.dfn[t] for t in teams],
              [elo.rating(t) for t in teams])
    assert c > 0.85, c


# ------------------------------------------------------------------ pipeline

def test_price_match_blends_between_model_and_market():
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        res = fe.price_match(lam_home=1.90, lam_away=0.90, rho=-0.05,
                             market={"1x2": [2.60, 3.20, 2.90]}, w_market=w)
        lm, lk, lu = (res["lambdas_model"], res["lambdas_market"],
                      res["lambdas_used"])
        assert min(lm[0], lk[0]) - 1e-9 <= lu[0] <= max(lm[0], lk[0]) + 1e-9
    r0 = fe.price_match(lam_home=1.9, lam_away=0.9, rho=-0.05,
                        market={"1x2": [2.60, 3.20, 2.90]}, w_market=0.0)
    assert abs(r0["lambdas_used"][0] - 1.9) < 1e-9


def test_disagreement_penalty_reduces_stakes():
    common = dict(market={"1x2": [2.20, 3.40, 3.30]}, w_market=0.5, rho=-0.05,
                  offered={"1x2": {"home": 2.60, "draw": 3.60, "away": 3.60}})
    close = fe.price_match(lam_home=1.45, lam_away=1.15, **common)
    far = fe.price_match(lam_home=3.00, lam_away=0.45, **common)
    assert close["disagreement_penalty"] > far["disagreement_penalty"]
    assert far["disagreement_penalty"] < 1.0


def test_value_scan_signs_are_correct():
    grid = fe.ScoreGrid.from_lambdas(1.5, 1.2, -0.05)
    h, d, a = grid.result_probs()
    rows = fe.scan_value(grid, {"1x2": {"home": 1.10 / h,      # +10 % de valeur
                                        "draw": 1.00 / d,      # prix juste
                                        "away": 0.85 / a}})    # -15 %
    by = {r["label"]: r for r in rows}
    assert abs(by["1X2 home"]["edge"] - 0.10) < 1e-9
    assert abs(by["1X2 draw"]["edge"]) < 1e-9
    assert abs(by["1X2 away"]["edge"] + 0.15) < 1e-9
    assert by["1X2 home"]["value"] and not by["1X2 away"]["value"]
    assert rows[0]["label"] == "1X2 home"                      # tri par edge


def test_build_book_is_internally_consistent():
    g = fe.ScoreGrid.from_lambdas(1.75, 1.05, -0.05)
    b = fe.build_book(g)
    p = b["1x2"]
    assert abs(sum(p[k]["prob"] for k in ("home", "draw", "away")) - 1) < 1e-9
    assert abs(b["double_chance"]["1X"]["prob"]
               - (p["home"]["prob"] + p["draw"]["prob"])) < 1e-12
    assert abs(b["btts"]["yes"]["prob"] + b["btts"]["no"]["prob"] - 1) < 1e-12
    ah = b["asian_handicap"]["-0.50"]["home"]["win"]
    assert abs(ah - p["home"]["prob"]) < 1e-12       # AH -0.5 == 1X2 domicile
    assert abs(sum(b["halves"]["htft"].values()) - 1.0) < 1e-6


def test_render_match_produces_text():
    res = fe.price_match(lam_home=1.6, lam_away=1.1, rho=-0.05,
                         market={"1x2": [2.30, 3.30, 3.20]},
                         offered={"1x2": {"home": 2.60}})
    txt = fe.render_match(res, "A", "B", "Test")
    assert "A" in txt and "1X2" in txt and "Plan de mise" in txt
    assert len(txt.splitlines()) > 15


# --------------------------------------------------------------------- live

def test_remaining_share_endpoints_and_monotonicity():
    assert abs(fe.remaining_share(0) - 1.0) < 1e-12
    assert abs(fe.remaining_share(90) - 0.0) < 1e-12
    assert abs(fe.remaining_share(45) - (1 - fe.DEFAULT_H1_SHARE)) < 1e-12
    for m in range(0, 90):
        assert fe.remaining_share(m) > fe.remaining_share(m + 1)


def test_remaining_share_always_exceeds_linear_time():
    """Le taux de buts etant croissant, il reste toujours plus de buts que de temps."""
    for m in range(0, 91):
        assert fe.remaining_share(m) >= (90 - m) / 90.0 - 1e-12, m


def test_live_grid_reduces_to_prematch_at_kickoff():
    pre = fe.ScoreGrid.from_lambdas(1.7, 1.15, -0.05)
    live = fe.live_grid(1.7, 1.15, 0, 0, 0, rho=-0.05)
    for i in range(9):
        for j in range(9):
            assert abs(pre.m[i][j] - live.m[i][j]) < 1e-12, (i, j)


def test_live_grid_is_a_distribution_over_final_scores():
    for minute, sh, sa in [(1, 0, 0), (30, 1, 0), (55, 1, 2), (89, 3, 3)]:
        g = fe.live_grid(1.6, 1.1, minute, sh, sa, rho=-0.05)
        assert abs(sum(sum(r) for r in g.m) - 1.0) < 1e-9, (minute, sh, sa)
        # aucun score final inferieur au score deja acquis
        for i in range(g.n + 1):
            for j in range(g.n + 1):
                if i < sh or j < sa:
                    assert g.m[i][j] == 0.0, (minute, i, j)
        td = g.total_dist()
        assert min(k for k, p in td.items() if p > 1e-12) == sh + sa


def test_live_win_probability_grows_as_the_clock_runs_down():
    prev = 0.0
    for minute in (10, 30, 50, 70, 85, 89):
        p = fe.live_grid(1.6, 1.1, minute, 1, 0, rho=-0.05).result_probs()[0]
        assert p > prev, minute
        prev = p
    assert prev > 0.90


def test_live_red_cards_move_probabilities_the_right_way():
    base = fe.live_grid(1.6, 1.1, 25, 0, 0, rho=-0.05).result_probs()
    red_h = fe.live_grid(1.6, 1.1, 25, 0, 0, red_home=1, rho=-0.05).result_probs()
    red_a = fe.live_grid(1.6, 1.1, 25, 0, 0, red_away=1, rho=-0.05).result_probs()
    assert red_h[0] < base[0] and red_h[2] > base[2]
    assert red_a[0] > base[0] and red_a[2] < base[2]
    assert fe.live_grid(1.6, 1.1, 25, 0, 0, red_home=2,
                        rho=-0.05).result_probs()[0] < red_h[0]


def test_live_game_state_can_be_disabled():
    on = fe.live_grid(1.6, 1.1, 40, 2, 0, rho=-0.05, game_state=True)
    off = fe.live_grid(1.6, 1.1, 40, 2, 0, rho=-0.05, game_state=False)
    assert on.lam_h < off.lam_h        # l'equipe en tete leve le pied
    assert on.lam_a > off.lam_a        # l'equipe menee pousse


def test_live_book_omits_halftime_markets_and_stays_coherent():
    b = fe.build_book(fe.live_grid(1.6, 1.1, 70, 1, 1, rho=-0.05))
    assert "halves" not in b and b["live"]["minute"] == 70
    assert abs(sum(b["1x2"][k]["prob"] for k in ("home", "draw", "away")) - 1) < 1e-9
    ah = b["asian_handicap"]["-0.50"]
    assert abs(1 / ah["home"]["fair_odds"] + 1 / ah["away"]["fair_odds"] - 1) < 1e-9


# ---------------------------------------------------------------- simulation

def test_season_simulation_is_a_distribution():
    syn = fe.synthetic_league(n_teams=10, seasons=2, seed=15)
    model = fe.fit_dixon_coles(syn["matches"], max_iter=300)
    teams = syn["teams"][:8]
    fixtures = [{"home": a, "away": b} for a in teams for b in teams if a != b]
    sim = fe.simulate_season(model, fixtures, n_sims=400, seed=2,
                             promo=2, releg=2, playoff=(3, 5))
    assert abs(sum(t["p_champion"] for t in sim["teams"]) - 1.0) < 1e-9
    for t in sim["teams"]:
        assert abs(sum(t["position_dist"]) - 1.0) < 1e-9
        assert 0.0 <= t["p_promotion"] <= 1.0
        assert 1.0 <= t["expected_position"] <= len(teams)


def test_season_simulation_respects_current_standings():
    syn = fe.synthetic_league(n_teams=8, seasons=2, seed=17)
    model = fe.fit_dixon_coles(syn["matches"], max_iter=300)
    teams = syn["teams"][:6]
    fixtures = [{"home": a, "away": b} for a in teams for b in teams if a != b]
    lead = {t: {"pts": (40 if t == teams[0] else 0), "gf": 0, "ga": 0}
            for t in teams}
    sim = fe.simulate_season(model, fixtures, lead, n_sims=300, seed=1)
    champ = {t["team"]: t["p_champion"] for t in sim["teams"]}
    assert champ[teams[0]] > 0.85, champ


def test_parlay_correlation_beats_naive_product():
    g = fe.ScoreGrid.from_lambdas(1.85, 0.95, -0.05)
    legs = [{"grid": g, "match_id": "m", "test": lambda h, a: h == a},
            {"grid": g, "match_id": "m", "test": lambda h, a: h + a < 2.5}]
    out = fe.simulate_parlay(legs, n_sims=30000, seed=4)
    assert out["prob"] > out["naive_independent"]
    assert out["correlation_effect"] > 3 * out["std_error"]


def test_parlay_across_matches_is_near_independent():
    g1 = fe.ScoreGrid.from_lambdas(1.6, 1.1, -0.05)
    g2 = fe.ScoreGrid.from_lambdas(1.3, 1.3, -0.05)
    legs = [{"grid": g1, "match_id": "a", "test": lambda h, a: h > a},
            {"grid": g2, "match_id": "b", "test": lambda h, a: h > a}]
    out = fe.simulate_parlay(legs, n_sims=40000, seed=9)
    assert abs(out["correlation_effect"]) < 4 * out["std_error"] + 0.005


# --------------------------------------------------------------------- CSV

def _write(tmp, text):
    path = os.path.join(tmp, "f.csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_csv_reads_both_conventions():
    with tempfile.TemporaryDirectory() as tmp:
        p1 = _write(tmp, "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,PSH,PSD,PSA\n"
                         "F1,12/08/2024,Lyon,Nice,2,1,1.95,3.60,3.90\n")
        rows = fe.load_matches_csv(p1)
        assert rows[0]["home"] == "Lyon" and rows[0]["hg"] == 2
        assert abs(rows[0]["odds_d"] - 3.60) < 1e-9
    with tempfile.TemporaryDirectory() as tmp:
        p2 = _write(tmp, "date,home,away,hg,ag,league,hxg,axg\n"
                         "2024-08-12,Lyon,Nice,2,1,F1,1.84,0.97\n")
        rows = fe.load_matches_csv(p2)
        assert rows[0]["league"] == "F1"
        assert abs(rows[0]["hxg"] - 1.84) < 1e-9


def test_csv_skips_bad_rows_and_sorts_by_date():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "date,home,away,hg,ag\n"
                        "2024-09-01,C,D,1,1\n"
                        "2024-08-01,A,B,2,0\n"
                        "2024-08-15,E,F,,\n"           # score manquant
                        "pas-une-date,G,H,1,0\n")
        rows = fe.load_matches_csv(p)
        assert len(rows) == 2
        assert rows[0]["home"] == "A" and rows[1]["home"] == "C"


def test_csv_missing_columns_raises_a_clear_error():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "date,home,away\n2024-08-01,A,B\n")
        try:
            fe.load_matches_csv(p)
        except ValueError as exc:
            assert "colonnes manquantes" in str(exc)
            return
        raise AssertionError("aucune erreur levee")


# ------------------------------------------------------------- journal

def _log_row(**kw):
    base = {"odds": 2.10, "stake": 20.0, "prob": 0.52, "pnl": 22.0,
            "closing_fair": 2.00, "closing": 1.98, "competition": "FRA2",
            "market": "1X2", "bankroll_after": 1000.0}
    base.update(kw)
    return base


def test_log_reads_the_shipped_template():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "bets_log_template.csv")
    rows = fe.load_bets_log(path)
    assert len(rows) == 1
    assert abs(rows[0]["odds"] - 1.80) < 1e-9
    assert rows[0]["competition"] == "FRA2"
    assert abs(rows[0]["clv"] - 0.0465) < 1e-9


def test_log_requires_odds_and_stake():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "j.csv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("date,competition\n2026-01-01,FRA2\n")
        try:
            fe.load_bets_log(p)
        except ValueError as exc:
            assert "colonnes manquantes" in str(exc)
            return
        raise AssertionError("aucune erreur levee")


def test_analyse_log_computes_clv_from_the_fair_closing_price():
    rep = fe.analyse_log([_log_row()] * 12, min_segment=5)
    assert abs(rep["clv"]["mean"] - 0.05) < 1e-12          # 2.10 / 2.00 - 1
    assert rep["clv"]["beat_close_rate"] == 1.0
    assert rep["clv"]["warning"] is None


def test_analyse_log_warns_when_closing_is_not_devigged():
    rep = fe.analyse_log([{"odds": 2.10, "stake": 10.0, "closing": 2.00}])
    assert rep["clv"]["warning"] is not None
    assert abs(rep["clv"]["mean"] - 0.05) < 1e-12


def test_analyse_log_verdicts_follow_the_documented_bands():
    for fair, expected in ((1.95, "avantage reel"), (2.09, "aucun avantage"),
                           (2.40, "mauvais cote")):
        rows = [_log_row(closing_fair=fair) for _ in range(10)]
        for r in rows:
            r.pop("clv", None)
        v = fe.analyse_log(rows)["clv"]["verdict"]
        assert expected in v, (fair, v)


def test_analyse_log_triggers_stop_criteria():
    rows = [_log_row(closing_fair=2.40) for _ in range(160)]
    rep = fe.analyse_log(rows)
    assert any("CLV" in x for x in rep["stop_criteria_triggered"])
    deep = [_log_row(bankroll_after=b) for b in (1000, 900, 800, 600, 550)]
    assert any("drawdown" in x for x in fe.analyse_log(deep)["stop_criteria_triggered"])


def test_analyse_log_separates_segments_and_honours_min_segment():
    rows = ([_log_row(competition="FRA2") for _ in range(20)]
            + [_log_row(competition="WENG1") for _ in range(3)])
    rep = fe.analyse_log(rows, min_segment=10)
    names = [x["name"] for x in rep["segments"]["competition"]]
    assert names == ["FRA2"]                    # segment trop court ecarte


def test_analyse_log_roi_and_significance():
    rows = [_log_row(pnl=22.0) for _ in range(9)] + [_log_row(pnl=-20.0)]
    rep = fe.analyse_log(rows)
    assert abs(rep["returns"]["roi"] - (9 * 22.0 - 20.0) / 200.0) < 1e-12
    assert rep["returns"]["significance"]["n_required_95"] is not None
    assert rep["returns"]["ci95"]["lo"] <= rep["returns"]["ci95"]["hi"]


def test_analyse_log_handles_an_unsettled_journal():
    rows = [{"odds": 2.0, "stake": 10.0, "closing_fair": 1.95}]
    rep = fe.analyse_log(rows)
    assert rep["n_settled"] == 0
    assert rep["returns"]["roi"] is None
    assert rep["calibration"] is None
    assert "AUDIT DU JOURNAL" in fe.render_log_report(rep)


# ------------------------------------------------------------------ backtest

def test_backtest_has_no_lookahead_and_beats_nothing_by_magic():
    syn = fe.synthetic_league(n_teams=12, seasons=2, seed=23)
    fe.add_synthetic_odds(syn["matches"], att=syn["att"], dfn=syn["def"],
                          mu=syn["mu"], hfa=syn["hfa"], noise=0.10)
    bt = fe.backtest(syn["matches"], min_train=150, refit_every_days=60,
                     max_iter=150, warm_iter=50, min_edge=0.05)
    s = bt["summary"]
    assert s["n_matches_priced"] > 0
    for key in ("model", "market", "blend"):
        assert 0.0 < s["rps"][key] < 0.35, key
        assert 0.0 < s["log_loss"][key] < 3.0, key
    assert s["rps"]["blend"] <= max(s["rps"]["model"], s["rps"]["market"]) + 1e-6
    assert s["calibration"]["n"] > 0
    for b in bt["bets"]:
        assert b["stake"] > 0 and b["odds"] > 1.0


def test_backtest_refuses_insufficient_data():
    syn = fe.synthetic_league(n_teams=8, seasons=1, seed=31)
    try:
        fe.backtest(syn["matches"], min_train=10 ** 6)
    except ValueError:
        return
    raise AssertionError("le backtest aurait du refuser")


# --------------------------------------------------------------- robustesse

def test_extreme_lambdas_do_not_break():
    for lh, la in [(0.01, 0.01), (0.05, 6.0), (9.0, 0.02), (7.5, 7.5)]:
        g = fe.ScoreGrid.from_lambdas(lh, la, 0.0, max_goals=25)
        assert abs(sum(sum(r) for r in g.m) - 1.0) < 1e-8, (lh, la)
        h, d, a = g.result_probs()
        assert abs(h + d + a - 1.0) < 1e-9
        assert 0.0 <= g.over_under(2.5)["over"]["win"] <= 1.0


def test_rho_is_clipped_to_a_valid_range():
    """Un rho absurde ne doit jamais produire de probabilite negative."""
    for rho in (-5.0, -1.0, 0.9, 5.0):
        g = fe.ScoreGrid.from_lambdas(2.0, 1.5, rho)
        assert all(p >= 0.0 for row in g.m for p in row), rho
        assert abs(sum(sum(r) for r in g.m) - 1.0) < 1e-10, rho


def test_devig_handles_two_and_many_outcomes():
    for n in (2, 3, 4, 8, 16):
        odds = [n * 1.05] * n
        dv = fe.devig(odds)
        assert abs(sum(dv["probs"]) - 1.0) < 1e-6, n
        assert all(abs(p - 1.0 / n) < 1e-6 for p in dv["probs"]), n


def test_fit_rejects_empty_input():
    for bad in ([], [{"home": "A", "away": "B"}]):
        try:
            fe.fit_dixon_coles(bad)
        except ValueError:
            continue
        raise AssertionError("entree vide acceptee: %r" % (bad,))


def _corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy) if dx and dy else 0.0


# --------------------------------------------------------------------- main

def main():
    tests = [(n, o) for n, o in sorted(globals().items())
             if n.startswith("test_") and callable(o)]
    failed = []
    print("FootyEdge — %d tests independants\n" % len(tests))
    for name, fn in tests:
        try:
            fn()
            print("  [OK]   %s" % name)
        except AssertionError as exc:
            failed.append((name, exc))
            print("  [FAIL] %s\n         %s" % (name, exc))
        except Exception as exc:                       # noqa: BLE001
            failed.append((name, exc))
            print("  [ERR]  %s\n         %s: %s"
                  % (name, type(exc).__name__, exc))
    print("\n%d/%d tests reussis" % (len(tests) - len(failed), len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
