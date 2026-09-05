# 04 — PRIORS PAR CHAMPIONNAT

## Statut de ces chiffres — à lire avant tout usage

Ces valeurs sont des **ordres de grandeur pluriannuels**, pas des statistiques
mesurées sur une saison précise. Elles ont trois usages légitimes et un seul
usage interdit.

**Usages légitimes :**
1. **Point de départ** quand aucune donnée d'équipe n'est disponible.
2. **Contrôle de vraisemblance** : une intensité issue du modèle ou du marché
   qui s'écarte de plus de 25 % du prior de son championnat doit être
   justifiée, sinon suspectée.
3. **Paramétrage** : `w_marché`, avantage minimal, fraction de Kelly et
   sur-dispersion sont attachés au palier d'efficience, pas au championnat.

**Usage interdit :** les citer comme des faits statistiques, ou s'en servir
comme substitut à un modèle ajusté quand des données existent.

**Recalibrage.** Dès que vous disposez d'un historique, remplacez ces priors
par vos propres estimations :

```bash
python3 engine/footyedge.py fit --csv data/history/ligue2.csv --out model_l2.json
# lire mu, home_adv et rho dans la sortie, puis mettre a jour league_priors.csv
```

**Note de construction.** Les colonnes `P(1) / P(X) / P(2) / +2,5 / BTTS` ne
sont pas des comptages historiques : elles sont **déduites** du couple
(total, suprématie) par le moteur lui-même. Le fichier est donc, par
construction, cohérent avec le modèle — ce qui évite qu'un prior contredise
une tarification. Le couple (total, suprématie), lui, est saisi à la main.

Source machine : `data/league_priors.csv` — 55 compétitions.
Régénération : `python3 scripts/generate_priors.py`.

---

### Palier 1 — marchés très efficients

| Championnat | Pays | Div. | Total | Supr. | ρ | P(1) | P(X) | P(2) | +2,5 | BTTS |
|---|---|---|---|---|---|---|---|---|---|---|
| Premier League | Angleterre | D1 | 2.80 | +0.28 | -0.05 | 43% | 26% | 31% | 53% | 57% |
| LaLiga | Espagne | D1 | 2.60 | +0.30 | -0.05 | 43% | 27% | 29% | 48% | 53% |
| Serie A | Italie | D1 | 2.75 | +0.26 | -0.05 | 43% | 26% | 31% | 52% | 56% |
| Bundesliga | Allemagne | D1 | 3.10 | +0.30 | -0.03 | 44% | 24% | 31% | 60% | 62% |
| Ligue 1 | France | D1 | 2.75 | +0.28 | -0.05 | 43% | 26% | 30% | 52% | 56% |
| Ligue des champions | UEFA | C | 3.10 | +0.30 | -0.03 | 44% | 24% | 31% | 60% | 62% |

*Réglages du palier :* `w_marché` **0.72** · avantage minimal **2.5 %** · Kelly **×0.25** · marge 1X2 typique **2.5 %** · sur-dispersion `shape` **aucune (Poisson)**

### Palier 2 — marchés efficients

| Championnat | Pays | Div. | Total | Supr. | ρ | P(1) | P(X) | P(2) | +2,5 | BTTS |
|---|---|---|---|---|---|---|---|---|---|---|
| Ligue Europa | UEFA | C | 2.90 | +0.32 | -0.05 | 44% | 26% | 30% | 55% | 59% |
| Ligue Conference | UEFA | C | 2.95 | +0.35 | -0.05 | 45% | 25% | 30% | 57% | 59% |
| Eredivisie | Pays-Bas | D1 | 3.15 | +0.35 | -0.03 | 46% | 24% | 31% | 61% | 63% |
| Liga Portugal | Portugal | D1 | 2.60 | +0.32 | -0.05 | 44% | 27% | 29% | 48% | 53% |
| Pro League | Belgique | D1 | 2.90 | +0.30 | -0.05 | 44% | 26% | 30% | 55% | 59% |
| Super Lig | Turquie | D1 | 2.90 | +0.32 | -0.05 | 44% | 26% | 30% | 55% | 59% |
| Championship | Angleterre | D2 | 2.60 | +0.28 | -0.05 | 43% | 27% | 30% | 48% | 53% |
| 2. Bundesliga | Allemagne | D2 | 3.00 | +0.30 | -0.05 | 44% | 25% | 31% | 58% | 60% |
| Serie B | Italie | D2 | 2.55 | +0.28 | -0.05 | 43% | 28% | 30% | 47% | 52% |
| MLS | Etats-Unis | D1 | 3.00 | +0.30 | -0.05 | 44% | 25% | 31% | 58% | 60% |
| Liga MX | Mexique | D1 | 2.75 | +0.35 | -0.05 | 45% | 26% | 29% | 52% | 56% |
| Brasileirao Serie A | Bresil | D1 | 2.40 | +0.35 | -0.07 | 44% | 29% | 27% | 43% | 49% |
| Premiership | Ecosse | D1 | 2.70 | +0.28 | -0.05 | 43% | 27% | 30% | 51% | 55% |
| Super League | Suisse | D1 | 3.00 | +0.28 | -0.05 | 44% | 25% | 31% | 58% | 60% |
| Bundesliga | Autriche | D1 | 3.00 | +0.28 | -0.05 | 44% | 25% | 31% | 58% | 60% |
| J1 League | Japon | D1 | 2.65 | +0.25 | -0.05 | 42% | 27% | 31% | 49% | 54% |
| Liga Profesional | Argentine | D1 | 2.30 | +0.30 | -0.07 | 42% | 30% | 28% | 40% | 47% |

*Réglages du palier :* `w_marché` **0.6** · avantage minimal **3.0 %** · Kelly **×0.22** · marge 1X2 typique **3.5 %** · sur-dispersion `shape` **aucune (Poisson)**

### Palier 3 — marchés moyens (2e divisions, championnats secondaires)

| Championnat | Pays | Div. | Total | Supr. | ρ | P(1) | P(X) | P(2) | +2,5 | BTTS |
|---|---|---|---|---|---|---|---|---|---|---|
| Ligue 2 | France | D2 | 2.30 | +0.28 | -0.07 | 42% | 30% | 28% | 40% | 47% |
| LaLiga Hypermotion | Espagne | D2 | 2.30 | +0.30 | -0.07 | 42% | 30% | 28% | 40% | 47% |
| Liga Portugal 2 | Portugal | D2 | 2.45 | +0.30 | -0.05 | 43% | 28% | 29% | 44% | 50% |
| Eerste Divisie | Pays-Bas | D2 | 3.30 | +0.35 | -0.03 | 46% | 23% | 31% | 64% | 65% |
| Challenger Pro League | Belgique | D2 | 2.75 | +0.30 | -0.05 | 44% | 26% | 30% | 52% | 56% |
| 1. Lig | Turquie | D2 | 2.55 | +0.32 | -0.05 | 44% | 28% | 29% | 47% | 52% |
| League One | Angleterre | D3 | 2.65 | +0.30 | -0.05 | 44% | 27% | 30% | 49% | 54% |
| League Two | Angleterre | D4 | 2.60 | +0.30 | -0.05 | 43% | 27% | 29% | 48% | 53% |
| Championship | Ecosse | D2 | 2.70 | +0.28 | -0.05 | 43% | 27% | 30% | 51% | 55% |
| Super League | Grece | D1 | 2.45 | +0.35 | -0.05 | 44% | 28% | 28% | 44% | 50% |
| Ekstraklasa | Pologne | D1 | 2.70 | +0.30 | -0.05 | 44% | 27% | 30% | 51% | 55% |
| Chance Liga | Tchequie | D1 | 2.75 | +0.30 | -0.05 | 44% | 26% | 30% | 52% | 56% |
| HNL | Croatie | D1 | 2.65 | +0.30 | -0.05 | 44% | 27% | 30% | 49% | 54% |
| Superliga | Danemark | D1 | 2.85 | +0.28 | -0.05 | 43% | 26% | 31% | 54% | 58% |
| Eliteserien | Norvege | D1 | 3.00 | +0.30 | -0.05 | 44% | 25% | 31% | 58% | 60% |
| Allsvenskan | Suede | D1 | 2.90 | +0.28 | -0.05 | 43% | 26% | 31% | 55% | 59% |
| K League 1 | Coree du Sud | D1 | 2.60 | +0.25 | -0.05 | 42% | 27% | 30% | 48% | 53% |
| A-League Men | Australie | D1 | 3.00 | +0.28 | -0.05 | 44% | 25% | 31% | 58% | 60% |
| Saudi Pro League | Arabie S. | D1 | 2.90 | +0.30 | -0.05 | 44% | 26% | 30% | 55% | 59% |
| J2 League | Japon | D2 | 2.45 | +0.25 | -0.05 | 42% | 28% | 30% | 44% | 50% |
| Brasileirao Serie B | Bresil | D2 | 2.25 | +0.35 | -0.07 | 44% | 30% | 26% | 39% | 46% |
| Copa Libertadores | CONMEBOL | C | 2.45 | +0.45 | -0.05 | 47% | 28% | 25% | 44% | 49% |
| NWSL | Etats-Unis | D1 ♀ | 2.65 | +0.22 | -0.03 | 42% | 27% | 32% | 49% | 54% |

*Réglages du palier :* `w_marché` **0.48** · avantage minimal **4.0 %** · Kelly **×0.18** · marge 1X2 typique **5.0 %** · sur-dispersion `shape` **14**

### Palier 4 — marchés mous (féminin élite, divisions inférieures)

| Championnat | Pays | Div. | Total | Supr. | ρ | P(1) | P(X) | P(2) | +2,5 | BTTS |
|---|---|---|---|---|---|---|---|---|---|---|
| Women's Super League | Angleterre | D1 ♀ | 3.20 | +0.25 | -0.03 | 43% | 24% | 33% | 62% | 64% |
| Premiere Ligue | France | D1 ♀ | 3.40 | +0.20 | -0.03 | 43% | 23% | 34% | 66% | 67% |
| Frauen-Bundesliga | Allemagne | D1 ♀ | 3.20 | +0.22 | -0.03 | 43% | 24% | 33% | 62% | 64% |
| Liga F | Espagne | D1 ♀ | 3.40 | +0.22 | -0.03 | 43% | 23% | 34% | 66% | 67% |
| Serie A Femminile | Italie | D1 ♀ | 3.10 | +0.22 | -0.03 | 43% | 24% | 33% | 60% | 62% |
| Damallsvenskan | Suede | D1 ♀ | 3.00 | +0.22 | -0.03 | 42% | 25% | 33% | 58% | 60% |
| A-League Women | Australie | D1 ♀ | 3.30 | +0.25 | -0.03 | 44% | 23% | 33% | 64% | 65% |
| Women's Champions Lg | UEFA | C ♀ | 3.60 | +0.15 | -0.03 | 42% | 22% | 36% | 70% | 70% |
| Women's Championship | Angleterre | D2 ♀ | 3.10 | +0.25 | -0.03 | 43% | 24% | 32% | 60% | 62% |

*Réglages du palier :* `w_marché` **0.35** · avantage minimal **5.5 %** · Kelly **×0.13** · marge 1X2 typique **7.5 %** · sur-dispersion `shape` **10**

---

## Comment lire la colonne « Suprématie »

La suprématie est l'avantage du terrain **exprimé en buts** :
`λ_dom − λ_ext` pour deux équipes de force égale.

- 0,20 – 0,25 : avantage faible — football féminin élite, championnats
  asiatiques, matchs à huis clos.
- 0,26 – 0,32 : norme des grands championnats européens masculins.
- 0,33 – 0,40 : avantage marqué — Eredivisie, Turquie, championnats à forte
  ferveur, D2 avec déplacements longs.
- 0,40 + : cas particuliers — Amérique du Sud, altitude, coupes continentales
  à déplacement lointain.

Ce paramètre a **fortement baissé** au niveau mondial depuis 2020. Un modèle
ajusté sur dix ans surestime l'avantage du terrain actuel : c'est un
argument supplémentaire pour une demi-vie de 180 jours plutôt que 730.

---

## Champs du fichier CSV

| Colonne | Signification |
|---------|---------------|
| `goals_per_game` | Total de buts attendu, deux équipes confondues |
| `home_supremacy` | λ_dom − λ_ext pour des équipes de force égale |
| `home_adv_log` | Le même avantage, en log d'intensité (paramètre `h` du modèle) |
| `rho` | Correction Dixon-Coles du championnat |
| `p_home / p_draw / p_away` | 1X2 impliqué par (total, suprématie) |
| `p_over25`, `p_btts` | Repères de contrôle |
| `efficiency_tier` | 1 (très efficient) à 4 (mou) — pilote tous les réglages |
| `typical_margin_1x2_pct` | Marge 1X2 attendue chez un opérateur généraliste |
| `w_market_default` | Poids du marché dans la fusion |
| `min_edge` | Avantage minimal pour retenir un pari |
| `kelly_fraction` | Fraction de Kelly du palier |
| `nb_shape` | Paramètre de sur-dispersion (vide = Poisson) |

---

## Championnat absent de la table

Procédure, dans l'ordre :

1. **Classer le palier d'efficience** à partir de la marge observée chez un
   opérateur généraliste : ≤ 3 % → palier 1 ; 3–4,5 % → palier 2 ;
   4,5–6,5 % → palier 3 ; > 6,5 % → palier 4. C'est le meilleur indicateur
   disponible, et il est directement observable.
2. **Total de buts** : partir d'un championnat comparable en niveau et en
   géographie. À défaut : 2,70 (masculin), 3,20 (féminin élite).
3. **Suprématie** : 0,30 (masculin), 0,22 (féminin), +0,05 si les
   déplacements sont longs ou le championnat très fervent.
4. **ρ** : −0,05 par défaut ; −0,07 si le total est inférieur à 2,45.
5. Marquer tous ces nombres `[PRIOR]` et **majorer l'avantage minimal
   d'un point** tant qu'aucune donnée réelle ne les a confirmés.

---

## Contrôles de cohérence rapides

Si l'un de ces contrôles échoue, il y a une erreur quelque part — ne pas
parier avant de l'avoir trouvée.

| Contrôle | Plage acceptable |
|----------|------------------|
| P(1) + P(X) + P(2) | exactement 1 |
| P(X) masculin | 22 % – 30 % |
| P(X) féminin élite | 14 % – 24 % |
| P(+2,5) vs total | 2,5 buts → ≈ 46 % ; 3,0 → ≈ 58 % ; 3,5 → ≈ 68 % |
| P(BTTS) vs total | environ P(+2,5) + 4 à 6 points sur un match équilibré |
| Suprématie implicite du marché vs prior | écart < 0,35 but, sinon enquêter |
| Total implicite du marché vs prior | écart < 0,50 but, sinon enquêter |
