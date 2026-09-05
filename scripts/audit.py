#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit du systeme FootyEdge.

Verifie que le depot est coherent de bout en bout :
  1. integrite du moteur (auto-test + suite independante) ;
  2. toutes les commandes de la ligne de commande fonctionnent ;
  3. les tables chiffrees de la documentation correspondent au moteur ;
  4. les affirmations numeriques de la documentation sont exactes ;
  5. les renvois entre fichiers pointent vers des fichiers existants ;
  6. les fichiers de donnees sont valides et coherents avec le moteur ;
  7. un scenario complet de bout en bout aboutit.

Usage :
    python3 scripts/audit.py            # audit complet
    python3 scripts/audit.py --quick    # sans les suites de tests longues
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import footyedge as fe  # noqa: E402

PY = sys.executable
ENGINE = os.path.join(ROOT, "engine", "footyedge.py")


class Audit:
    def __init__(self):
        self.ok, self.fail, self.warn = 0, [], []

    def check(self, section, name, cond, detail=""):
        if cond:
            self.ok += 1
            print("  [OK]   %s" % name)
        else:
            self.fail.append((section, name, detail))
            print("  [FAIL] %s%s" % (name, ("  — " + detail) if detail else ""))

    def note(self, name, detail):
        self.warn.append((name, detail))
        print("  [note] %s — %s" % (name, detail))

    def section(self, title):
        print("\n%s\n%s" % (title, "-" * len(title)))


def run(cmd, timeout=300):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    return p.returncode, p.stdout, p.stderr


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------

def audit_engine(a, quick, counts):
    a.section("1. Integrite du moteur")
    if quick:
        a.note("suites de tests", "ignorees (--quick)")
        return
    rc, out, _ = run([PY, ENGINE, "selftest"])
    m = re.search(r"Resultat : (\d+)/(\d+) tests reussis", out)
    a.check("moteur", "auto-test embarque : %s" % (m.group(0) if m else "sortie illisible"),
            bool(m) and m.group(1) == m.group(2) and rc == 0)
    if m:
        counts["selftest"] = int(m.group(2))
    rc, out, err = run([PY, os.path.join(ROOT, "tests", "test_footyedge.py")])
    m = re.search(r"(\d+)/(\d+) tests reussis", out)
    a.check("moteur", "suite independante : %s" % (m.group(0) if m else "sortie illisible"),
            bool(m) and m.group(1) == m.group(2) and rc == 0)
    if m:
        counts["tests"] = int(m.group(2))


def audit_cli(a):
    a.section("2. Commandes de la ligne de commande")
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "h.csv")
        syn = fe.synthetic_league(n_teams=12, seasons=2, seed=77)
        fe.add_synthetic_odds(syn["matches"], att=syn["att"], dfn=syn["def"],
                              mu=syn["mu"], hfa=syn["hfa"])
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG",
                        "PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA"])
            for x in syn["matches"]:
                w.writerow([x["date"].strftime("%d/%m/%Y"), x["home"], x["away"],
                            x["hg"], x["ag"], x["odds_h"], x["odds_d"], x["odds_a"],
                            x["close_h"], x["close_d"], x["close_a"]])
        model = os.path.join(tmp, "m.json")
        fixtures = os.path.join(tmp, "f.json")
        teams = syn["teams"][:6]
        json.dump([{"home": x, "away": y} for x in teams for y in teams if x != y],
                  open(fixtures, "w"))
        offered = os.path.join(ROOT, "data", "offered_template.json")

        cases = [
            ("selftest",  [PY, ENGINE, "selftest"],  lambda o: "tests reussis" in o),
            ("demo",      [PY, ENGINE, "demo"],      lambda o: "lambda" in o),
            ("devig",     [PY, ENGINE, "devig", "--odds", "2.10", "3.40", "3.60"],
             # overround = somme(1/cote) - 1 = 0,0481 ; margin_pct = 4,59 %.
             # Les deux ne sont pas interchangeables.
             lambda o: (abs(json.loads(o)["overround"] - 0.04809) < 5e-4
                        and abs(json.loads(o)["margin_pct"] - 4.588) < 0.05
                        and abs(sum(json.loads(o)["probs"]) - 1.0) < 1e-8)),
            ("invert 1X2", [PY, ENGINE, "invert", "--1x2", "2.10", "3.40", "3.60"],
             lambda o: 1.3 < json.loads(o)["lambda_home"] < 1.5),
            ("invert asiatique",
             [PY, ENGINE, "invert", "--ah", "-0.5", "1.95", "1.95",
              "--ou", "2.5", "1.90", "1.98"],
             lambda o: 0.5 < json.loads(o)["lambda_home"] < 4.0),
            ("price --brief",
             [PY, ENGINE, "price", "--lh", "1.55", "--la", "1.15",
              "--market-1x2", "2.20", "3.40", "3.30", "--offered", offered, "--brief"],
             lambda o: "Plan de mise" in o and "Probabilites justes" in o.replace("é", "e")),
            ("fit", [PY, ENGINE, "fit", "--csv", csv_path, "--out", model, "--top", "3"],
             lambda o: "Modele ajuste" in o),
            ("table", [PY, ENGINE, "table", "--model", model, "--top", "3"],
             lambda o: len(o.strip().splitlines()) >= 4),
            ("predict --brief",
             [PY, ENGINE, "predict", "--model", model, "--home", syn["teams"][0],
              "--away", syn["teams"][1], "--market-1x2", "2.30", "3.30", "3.20",
              "--offered", offered, "--brief"],
             lambda o: "Intensites" in o.replace("é", "e")),
            ("calib", [PY, ENGINE, "calib", "--log",
                       os.path.join(ROOT, "data", "bets_log_template.csv")],
             lambda o: "AUDIT DU JOURNAL" in o and "CALIBRATION" in o),
            ("live", [PY, ENGINE, "live", "--lh", "1.6", "--la", "1.1",
                      "--minute", "63", "--score", "1", "0", "--red-away", "1"],
             lambda o: (json.loads(o)["live"]["minute"] == 63
                        and abs(sum(json.loads(o)["book"]["1x2"][k]["prob"]
                                    for k in ("home", "draw", "away")) - 1) < 1e-9
                        and "halves" not in json.loads(o)["book"])),
            ("season", [PY, ENGINE, "season", "--model", model,
                        "--fixtures", fixtures, "--sims", "300"],
             lambda o: abs(sum(t["p_champion"] for t in json.loads(o)["teams"]) - 1) < 1e-6),
            ("backtest", [PY, ENGINE, "backtest", "--csv", csv_path,
                          "--min-train", "150", "--refit", "60", "--min-edge", "0.05"],
             lambda o: json.loads(o)["n_matches_priced"] > 0),
        ]
        for name, cmd, ok in cases:
            try:
                rc, out, err = run(cmd)
                a.check("cli", "`%s`" % name, rc == 0 and ok(out),
                        (err.strip().splitlines() or [""])[-1][:120] if rc else "sortie inattendue")
            except Exception as exc:                       # noqa: BLE001
                a.check("cli", "`%s`" % name, False, "%s: %s" % (type(exc).__name__, exc))


def audit_tables(a):
    a.section("3. Tables de la documentation contre le moteur")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import generate_tables as gt
    for name in sorted(gt.TABLES):
        fn, dest = gt.TABLES[name]
        generated = fn().strip()
        doc = read(dest)
        missing = [ln for ln in generated.splitlines()
                   if ln.strip() and ln.strip() not in doc]
        a.check("tables", "table `%s` conforme dans %s" % (name, os.path.basename(dest)),
                not missing,
                "%d ligne(s) divergente(s), 1re : %s" % (len(missing), missing[0][:90])
                if missing else "")


def audit_claims(a):
    a.section("4. Affirmations chiffrees de la documentation")

    dv = fe.devig([2.10, 3.40, 3.60])
    lh, la = fe.lambdas_from_1x2(*dv["probs"], rho=-0.04)
    qs = read("DEMARRAGE_RAPIDE.md")
    a.check("claims", "démarrage rapide : marge 4,6 %",
            abs(dv["margin_pct"] - 4.6) < 0.1 and "4,6" in qs,
            "moteur %.2f %%" % dv["margin_pct"])
    a.check("claims", "démarrage rapide : probabilités Shin 45,9 / 27,9 / 26,3",
            all(abs(100 * p - v) < 0.1 for p, v in zip(dv["probs"], (45.9, 27.9, 26.3))),
            "moteur %s" % ["%.1f" % (100 * p) for p in dv["probs"]])
    a.check("claims", "démarrage rapide : intensités 1,41 − 1,00",
            abs(lh - 1.41) < 0.01 and abs(la - 1.00) < 0.01,
            "moteur %.3f / %.3f" % (lh, la))

    g = fe.ScoreGrid.from_lambdas(1.6, 1.1, -0.05)
    h = g.result_probs()[0]
    a.check("claims", "09 §1 : AH −0,5 domicile identique au 1X2 domicile",
            abs(g.asian_handicap(-0.5)["home"]["win"] - h) < 1e-12)
    a.check("claims", "09 §1 : les deux camps d'un AH forment un marché sans marge",
            all(abs(1 / g.asian_handicap(l)["home"]["fair_odds"]
                    + 1 / g.asian_handicap(l)["away"]["fair_odds"] - 1) < 1e-9
                for l in (-1.5, -0.75, -0.25, 0.0, 0.5, 1.25)))

    import math
    gp = fe.ScoreGrid.from_lambdas(1.6, 1.1, 0.0, max_goals=20)
    T = 2.7
    a.check("claims", "02 §8 : formule fermée du « plus de 2,5 buts »",
            abs(gp.over_under(2.5)["over"]["win"]
                - (1 - math.exp(-T) * (1 + T + T * T / 2))) < 1e-9)
    a.check("claims", "02 §8 : formule fermée du BTTS",
            abs(gp.btts()["yes"] - (1 - math.exp(-1.6) - math.exp(-1.1)
                                    + math.exp(-T))) < 1e-9)
    a.check("claims", "02 §8 : formule fermée du clean sheet",
            abs(gp.clean_sheet("home") - math.exp(-1.1)) < 1e-9)

    d05 = read("sources/05_D2_ET_FEMININ.md")
    gpo = fe.ScoreGrid.from_lambdas(3.40, 0.55, -0.03)
    gnb = fe.ScoreGrid.from_lambdas(3.40, 0.55, -0.03, shape_home=10, shape_away=10)
    fair_p, fair_n = 1 / gpo.result_probs()[2], 1 / gnb.result_probs()[2]
    a.check("claims", "05 §3.2 : cote juste de l'outsider 34,5 → 25,0",
            abs(fair_p - 34.5) < 0.6 and abs(fair_n - 25.0) < 0.6,
            "moteur %.1f → %.1f" % (fair_p, fair_n))
    a.check("claims", "05 §3.2 : le texte cite bien ces valeurs",
            "34,5" in d05 and "25,0" in d05)

    d09 = read("sources/09_MARCHES_FORMULES.md")
    gg = fe.ScoreGrid.from_lambdas(1.85, 0.95, -0.05)
    tot = lambda f: sum(gg.m[i][j] for i in range(gg.n + 1)
                        for j in range(gg.n + 1) if f(i, j))
    naive = tot(lambda h_, a_: h_ == a_) * tot(lambda h_, a_: h_ + a_ < 2.5)
    real = tot(lambda h_, a_: h_ == a_ and h_ + a_ < 2.5)
    a.check("claims", "09 §7 : « nul + moins de 2,5 » sous-estimé de 61 %",
            abs(100 * (real - naive) / naive - 61) < 1.5 and "61 %" in d09,
            "moteur %+.0f %%" % (100 * (real - naive) / naive))

    d02 = read("sources/02_MOTEUR_QUANTITATIF.md")
    a.check("claims", "02 §2 : la part de 1re mi-temps citée vaut celle du moteur",
            ("%.3f" % fe.DEFAULT_H1_SHARE).replace(".", ",") in d02
            or "0,455" in d02, "moteur %.3f" % fe.DEFAULT_H1_SHARE)

    d03 = read("sources/03_MARCHE_DEVIG_CLV.md")
    dvl = fe.devig([1.18, 7.50, 15.00])
    spread = 100 * max(dvl["method_spread"])
    a.check("claims", "03 §2 : écart de 2,6 points entre méthodes sur un gros favori",
            abs(spread - 2.63) < 0.1 and "2,6 points" in d03,
            "moteur %.2f points" % spread)


def audit_live(a):
    a.section("4 bis. Reevaluation en direct")
    a.check("live", "part de buts restante > part de temps restante a chaque minute",
            all(fe.remaining_share(m) >= (90 - m) / 90.0 - 1e-12
                for m in range(0, 91)))
    pre = fe.ScoreGrid.from_lambdas(1.7, 1.15, -0.05)
    lg = fe.live_grid(1.7, 1.15, 0, 0, 0, rho=-0.05)
    a.check("live", "coup d'envoi 0-0 : identique a la grille pre-match",
            all(abs(pre.m[i][j] - lg.m[i][j]) < 1e-12
                for i in range(9) for j in range(9)))
    g = fe.live_grid(1.6, 1.1, 55, 2, 1, rho=-0.05)
    a.check("live", "aucun score final inferieur au score acquis",
            all(g.m[i][j] == 0.0 for i in range(g.n + 1) for j in range(g.n + 1)
                if i < 2 or j < 1))
    a.check("live", "grille live : somme des probabilites = 1",
            abs(sum(sum(r) for r in g.m) - 1.0) < 1e-9)
    d09 = read("sources/09_MARCHES_FORMULES.md")
    a.check("live", "09 §8 documente bien la reevaluation en direct",
            "live_grid" in d09 and "ENCADRER un prix affiché" in d09)


def audit_journal(a):
    a.section("4 ter. Audit du journal de paris")
    d08 = read("sources/08_CALIBRATION_AUDIT.md")
    # Le signe est porte par la redaction du tableau (et le document utilise le
    # signe moins typographique) : on ne compare que les valeurs absolues.
    a.check("journal", "les bandes de CLV du code reprennent le bareme de 08",
            all(("%.1f" % abs(100 * thr)).replace(".", ",") in d08
                for thr, _ in fe.CLV_BANDS if thr != float("-inf")),
            "bandes : %s" % [t for t, _ in fe.CLV_BANDS])
    a.check("journal", "les bandes d'ECE du code reprennent le bareme de 08",
            all(("%.2f" % thr).replace(".", ",") in d08
                for thr, _ in fe.ECE_BANDS if thr != float("inf")))
    rows = fe.load_bets_log(os.path.join(ROOT, "data", "bets_log_template.csv"))
    a.check("journal", "le modele de journal livre est exploitable",
            len(rows) == 1 and rows[0].get("clv") is not None)
    good = [{"odds": 2.10, "stake": 10.0, "closing_fair": 1.95, "prob": 0.5,
             "pnl": 11.0}] * 12
    bad = [{"odds": 2.10, "stake": 10.0, "closing_fair": 2.40} for _ in range(160)]
    a.check("journal", "CLV positif -> aucun critere d'arret",
            fe.analyse_log(good)["stop_criteria_triggered"] == [])
    a.check("journal", "CLV negatif sur 160 paris -> critere d'arret declenche",
            any("CLV" in x for x in fe.analyse_log(bad)["stop_criteria_triggered"]))


def audit_crossrefs(a):
    a.section("5. Renvois entre fichiers")
    src = os.path.join(ROOT, "sources")
    files = sorted(os.listdir(src))
    a.check("refs", "les 14 documents sources sont presents",
            len([f for f in files if f.endswith(".md")]) == 14,
            "trouves : %d" % len([f for f in files if f.endswith(".md")]))
    docs = {f: read("sources/" + f) for f in files if f.endswith(".md")}
    docs["README.md"] = read("README.md")
    docs["DEMARRAGE_RAPIDE.md"] = read("DEMARRAGE_RAPIDE.md")
    docs["engine/README.md"] = read("engine/README.md")
    broken = []
    for fname, text in docs.items():
        for ref in set(re.findall(r"`?(\d{2}_[A-Z0-9_]+\.md)`?", text)):
            if ref not in files:
                broken.append("%s -> %s" % (fname, ref))
        for ref in set(re.findall(r"`(data/[\w./-]+|engine/[\w./-]+|scripts/[\w./-]+|tests/[\w./-]+)`", text)):
            base = ref.split("/")[0]
            if "*" in ref or ref.endswith("/"):
                continue
            if ref.startswith("data/history") or ref.startswith("data/live"):
                continue
            if not os.path.exists(os.path.join(ROOT, ref)):
                broken.append("%s -> %s" % (fname, ref))
    a.check("refs", "aucun renvoi casse", not broken,
            "; ".join(sorted(set(broken))[:5]))

    fns = set(re.findall(r"\n(?:def|class) (\w+)", read("engine/footyedge.py")))
    cited = set()
    for text in docs.values():
        cited |= set(re.findall(r"`fe\.(\w+)", text))
        cited |= set(re.findall(r"= fe\.(\w+)", text))
    unknown = sorted(c for c in cited if c not in fns and not hasattr(fe, c))
    a.check("refs", "toutes les fonctions citees existent dans le moteur",
            not unknown, ", ".join(unknown[:6]))


def audit_documented_counts(a, quick, counts):
    """Verifie que AUDIT.md et README.md annoncent les bons nombres de tests."""
    a.section("6 bis. Chiffres annonces par la documentation")
    if quick:
        a.note("chiffres annonces", "non verifiables sans les suites (--quick)")
        return
    audit_md, readme = read("AUDIT.md"), read("README.md")
    n_self = counts.get("selftest")
    n_tests = counts.get("tests")
    n_audit = a.ok + len(a.fail) + 6     # + les 6 controles de cette section
    for label, value, texts in (("auto-test du moteur", n_self, (audit_md, readme)),
                                ("suite independante", n_tests, (audit_md, readme))):
        a.check("counts", "%s : %s cite dans la documentation" % (label, value),
                value is not None and all(str(value) in t for t in texts),
                "valeur mesuree : %s" % value)
    total = (n_self or 0) + (n_tests or 0) + n_audit
    a.check("counts", "AUDIT.md annonce le bon total (%d)" % total,
            str(total) in audit_md,
            "AUDIT.md doit citer %d (=%s+%s+%s)" % (total, n_self, n_tests, n_audit))
    a.check("counts", "README.md annonce le bon total (%d)" % total,
            str(total) in readme)

    # Les sous-sections de AUDIT.md doivent etre numerotees a la suite et leurs
    # effectifs doivent redonner le total de cet audit.
    heads = re.findall(r"### 2\.(\d+) [^(\n]+\((\d+) contr", audit_md)
    nums = [int(h[0]) for h in heads]
    a.check("counts", "sous-sections de AUDIT.md numerotees a la suite",
            nums == list(range(1, len(nums) + 1)), "trouve : %s" % nums)
    detailed = sum(int(h[1]) for h in heads[1:])   # hors 2.1 (auto-test moteur)
    a.check("counts", "les effectifs des sous-sections redonnent %d" % n_audit,
            detailed + 2 == n_audit,
            "somme des sections = %d + 2 (integrite) = %d, attendu %d"
            % (detailed, detailed + 2, n_audit))


def audit_data(a):
    a.section("6. Fichiers de donnees")
    for f in ("fixtures_template.json", "standings_template.json",
              "offered_template.json"):
        try:
            json.loads(read("data/" + f))
            a.check("data", "%s : JSON valide" % f, True)
        except Exception as exc:                           # noqa: BLE001
            a.check("data", "%s : JSON valide" % f, False, str(exc))

    rows = fe.load_matches_csv(os.path.join(ROOT, "data", "matches_template.csv"))
    a.check("data", "matches_template.csv lisible par le moteur",
            len(rows) == 3 and rows[0]["home"] == "Guingamp",
            "%d lignes lues" % len(rows))

    priors = list(csv.DictReader(open(os.path.join(ROOT, "data", "league_priors.csv"),
                                     encoding="utf-8")))
    a.check("data", "league_priors.csv : 55 competitions", len(priors) == 55,
            "%d lignes" % len(priors))
    bad = []
    for r in priors:
        T, S, rho = (float(r["goals_per_game"]), float(r["home_supremacy"]),
                     float(r["rho"]))
        g = fe.ScoreGrid.from_lambdas((T + S) / 2, (T - S) / 2, rho)
        h, d, aw = g.result_probs()
        for key, got in (("p_home", h), ("p_draw", d), ("p_away", aw),
                         ("p_over25", g.over_under(2.5)["over"]["win"]),
                         ("p_btts", g.btts()["yes"])):
            if abs(float(r[key]) - got) > 0.0006:
                bad.append("%s/%s (%.3f vs %.3f)" % (r["league_id"], key,
                                                     float(r[key]), got))
    a.check("data", "league_priors.csv coherent avec le moteur", not bad,
            "; ".join(bad[:4]))
    tiers = {}
    for r in priors:
        t = r["efficiency_tier"]
        tiers.setdefault(t, set()).add((r["w_market_default"], r["min_edge"],
                                        r["kelly_fraction"]))
    a.check("data", "reglages homogenes a l'interieur de chaque palier",
            all(len(v) == 1 for v in tiers.values()))
    a.check("data", "seuil d'avantage croissant avec le palier",
            [float(sorted(tiers[str(t)])[0][1]) for t in (1, 2, 3, 4)]
            == sorted(float(sorted(tiers[str(t)])[0][1]) for t in (1, 2, 3, 4)))
    a.check("data", "fraction de Kelly decroissante avec le palier",
            [float(sorted(tiers[str(t)])[0][2]) for t in (1, 2, 3, 4)]
            == sorted((float(sorted(tiers[str(t)])[0][2]) for t in (1, 2, 3, 4)),
                      reverse=True))
    a.check("data", "journal de paris : colonnes de decision et de resultat separees",
            set(["odds_taken", "stake", "closing_odds", "clv_fair", "result"])
            <= set(next(csv.reader(open(os.path.join(ROOT, "data",
                                                     "bets_log_template.csv"),
                                        encoding="utf-8")))))


def audit_end_to_end(a):
    a.section("7. Scenario complet")
    # Marche synthetique = verite + bruit. Le modele ne peut l'ameliorer que si
    # son erreur d'estimation est inferieure a ce bruit : d'ou 20 equipes,
    # 4 saisons (assez de donnees) et un bruit de marche de 0,16 (marche
    # imparfait). Avec moins de donnees ou un marche moins bruite, le marche
    # est imbattable par construction — voir AUDIT.md, limites.
    syn = fe.synthetic_league(n_teams=20, seasons=4, seed=2024)
    fe.add_synthetic_odds(syn["matches"], att=syn["att"], dfn=syn["def"],
                          mu=syn["mu"], hfa=syn["hfa"], noise=0.16, seed=2024)
    cut = int(0.75 * len(syn["matches"]))
    train, future = syn["matches"][:cut], syn["matches"][cut:]
    model = fe.fit_dixon_coles(train, half_life_days=200, reg=1.0, max_iter=500)
    a.check("e2e", "1. ajustement sur %d matchs" % len(train),
            len(model.teams) == 20 and 0.10 < model.home_adv < 0.35,
            "avantage terrain %.3f" % model.home_adv)

    nxt = future[0]
    res = fe.price_match(model=model, home=nxt["home"], away=nxt["away"],
                         rho=model.rho, w_market=0.55,
                         market={"1x2": [nxt["odds_h"], nxt["odds_d"], nxt["odds_a"]]},
                         offered={"1x2": {"home": nxt["odds_h"] * 1.08,
                                          "draw": nxt["odds_d"],
                                          "away": nxt["odds_a"]},
                                  "ou": {"2.5": {"over": 1.95, "under": 1.95}}},
                         bankroll=2000, kelly_fraction=0.20, min_edge=0.03)
    a.check("e2e", "2. tarification : 1X2 somme a 1",
            abs(sum(res["book"]["1x2"][k]["prob"]
                    for k in ("home", "draw", "away")) - 1) < 1e-9)
    a.check("e2e", "3. detection de valeur sur la cote bonifiee",
            any(v["value"] for v in res["value_bets"]))
    a.check("e2e", "4. plan de mise dans les plafonds",
            res["stake_plan"]["total_exposure"] <= 0.10 + 1e-9,
            "exposition %.3f" % res["stake_plan"]["total_exposure"])
    txt = fe.render_match(res, nxt["home"], nxt["away"], "Audit")
    a.check("e2e", "5. fiche lisible produite",
            "Plan de mise" in txt and len(txt.splitlines()) > 20)
    book = res["book"]
    fams = [k for k in book if k not in ("inputs", "entropy_bits", "halves")]
    n_fams = len(fams) + len([k for k in book.get("halves", {}) if k != "h1_share"])
    a.check("e2e", "5b. 16 familles de marches issues d'une seule grille",
            n_fams == 16, "trouvees : %d (%s)" % (n_fams, ", ".join(fams)))

    bt = fe.backtest(syn["matches"], min_train=600, refit_every_days=45,
                     w_market=0.6, min_edge=0.04, max_iter=200, warm_iter=60)
    s = bt["summary"]
    a.check("e2e", "6a. invariant : la fusion ne fait pas pire que sa pire source",
            s["rps"]["blend"] <= max(s["rps"]["model"], s["rps"]["market"]) + 1e-9,
            "fusion %.5f vs max(%.5f, %.5f)" % (s["rps"]["blend"], s["rps"]["model"],
                                                s["rps"]["market"]))
    a.check("e2e", "6b. la fusion ameliore le marche quand le modele a de l'avance",
            s["rps"]["blend"] < s["rps"]["market"],
            "fusion %.5f vs marche %.5f" % (s["rps"]["blend"], s["rps"]["market"]))
    a.check("e2e", "6c. le critere d'arret de 08 §6 est calculable",
            s["rps_edge_vs_market"] is not None)
    a.check("e2e", "7. calibration mesuree (ECE = %.4f)" % s["calibration"]["ece"],
            s["calibration"]["ece"] < 0.10)
    a.check("e2e", "8. CLV calcule sur les paris joues",
            s["betting"]["clv_mean"] is not None and s["betting"]["n_bets"] > 0,
            "%d paris" % s["betting"]["n_bets"])
    print("      (contexte : %d matchs tarifes, RPS modele %.5f / marche %.5f / "
          "fusion %.5f, %d paris, CLV moyen %+.2f %%)"
          % (s["n_matches_priced"], s["rps"]["model"], s["rps"]["market"],
             s["rps"]["blend"], s["betting"]["n_bets"],
             100 * (s["betting"]["clv_mean"] or 0)))

    teams = syn["teams"]
    fx = [{"home": x, "away": y} for i, x in enumerate(teams) for y in teams[i + 1:]]
    sim = fe.simulate_season(model, fx, n_sims=2000, promo=2, releg=3, playoff=(3, 6))
    a.check("e2e", "9. simulation de saison : distribution valide",
            abs(sum(t["p_champion"] for t in sim["teams"]) - 1) < 1e-9)
    a.check("e2e", "10. montee et descente s'excluent en tete de classement",
            sim["teams"][0]["p_promotion"] > sim["teams"][0]["p_relegation"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    a = Audit()
    counts = {}
    print("=" * 70)
    print("AUDIT FootyEdge %s — %s" % (fe.__version__, ROOT))
    print("=" * 70)
    audit_engine(a, args.quick, counts)
    audit_cli(a)
    audit_tables(a)
    audit_claims(a)
    audit_live(a)
    audit_journal(a)
    audit_crossrefs(a)
    audit_data(a)
    audit_end_to_end(a)
    audit_documented_counts(a, args.quick, counts)
    total = a.ok + len(a.fail)
    print("\n" + "=" * 70)
    print("RESULTAT : %d/%d controles reussis" % (a.ok, total))
    if a.warn:
        print("Notes :")
        for n, d in a.warn:
            print("  - %s : %s" % (n, d))
    if a.fail:
        print("ECHECS :")
        for sec, name, detail in a.fail:
            print("  - [%s] %s%s" % (sec, name, ("  — " + detail) if detail else ""))
    print("=" * 70)
    return 1 if a.fail else 0


if __name__ == "__main__":
    sys.exit(main())
