# 01 — PROTOCOLE OPÉRATOIRE

Mode d'emploi détaillé des neuf phases. Chaque phase indique : ce qui entre,
ce qui sort, l'appel moteur correspondant, et le critère d'arrêt.

---

## Phase 0 — Recevabilité

**Entrée.** La demande brute de l'utilisateur.

**Contrôles.**

| Contrôle | Seuil de blocage |
|----------|------------------|
| Équipes identifiées sans ambiguïté | homonymes (Ex. « Arsenal » : ENG / ARG) |
| Compétition identifiée | palier de championnat inconnu → prior impossible |
| Date et heure du coup d'envoi | > 72 h → compositions inconnues, σ élargi |
| Au moins un bloc marché **ou** un bloc modèle | sinon : non tarifable |
| Cotes accompagnées de l'opérateur | une cote sans source n'est pas exploitable |

**Sortie.** `GO` ou une demande **ciblée** — au maximum trois questions, les
plus discriminantes d'abord. Ne jamais réclamer un formulaire complet.

---

## Phase 1 — Ancrage marché

**Entrée.** Cotes de l'opérateur de référence (voir `03_MARCHE_DEVIG_CLV.md`
pour le classement des opérateurs).

**Traitement.**
1. Retrait de marge, 5 méthodes, retenir Shin pour 2–3 issues.
2. Noter la **dispersion inter-méthodes** : c'est une composante directe de σ.
3. Inverser en intensités de buts. Si des lignes asiatiques sont disponibles,
   les préférer au 1X2 : marge plus faible, flux plus informé.

```python
import footyedge as fe

# 1X2 seul
dv = fe.devig([2.10, 3.40, 3.60])          # -> probs, overround, 5 methodes
lh, la = fe.lambdas_from_1x2(*dv["probs"], rho=-0.04)

# Handicap + total (preferable)
lh, la, info = fe.market_to_lambdas({
    "ah": {"line": -0.5, "home": 1.95, "away": 1.95},
    "ou": {"line": 2.5,  "over": 1.90, "under": 1.98},
}, rho=-0.04)
```

**Sortie.** `λ_marché = (λ_dom, λ_ext)`, marge, dispersion de devig.

**Point de contrôle.** Marge > 8 % sur du 1X2 → opérateur non fiable comme
ancrage ; chercher une référence plus serrée avant de continuer.

---

## Phase 2 — Estimation modèle

Trois voies, par ordre de qualité décroissante.

### 2a. Modèle ajusté (nominal)

```python
matches = fe.load_matches_csv("data/history/france.csv")   # D1 + D2 ensemble
model = fe.fit_dixon_coles(matches, half_life_days=180, reg=1.0)
lh_m, la_m = model.lambdas("Guingamp", "Amiens")
sigma = model.lambda_uncertainty("Guingamp", "Amiens")     # incertitude reelle
```

Deux points qui changent tout :

- **Charger toutes les divisions d'un pays dans le même fichier** (champ
  `league`). Les notes deviennent comparables entre divisions, les promus
  gardent leur historique et les matchs de coupe se tarifient
  (`02_MOTEUR_QUANTITATIF.md` §5 bis).
- **Régler les hyperparamètres par `tune`, pas à l'intuition**
  (`02_MOTEUR_QUANTITATIF.md` §4).

Si `lambda_uncertainty` renvoie un écart-type supérieur à 0,25 sur log(λ), les
données sont trop maigres : élargir σ, diviser Kelly par deux, ou s'abstenir.

### 2b. Reconstruction à partir des dernières rencontres

Sans historique complet mais avec les 8–10 derniers matchs de chaque équipe :
appliquer la procédure de `02_MOTEUR_QUANTITATIF.md` §7 (moyennes ajustées de
la force adverse, régression vers la moyenne du championnat).

### 2c. Prior de championnat seul

Sans donnée d'équipe : `λ = prior de championnat`, aucune différenciation.
Le modèle n'apporte rien ; `w_marché = 1`. On ne parie pas sur un modèle
qui n'a aucune information propre — sauf marché manifestement aberrant.

**Sortie.** `λ_modèle`, plus un indice de fiabilité (poids effectif de données
sur les deux équipes).

---

## Phase 3 — Ajustements contextuels

Multiplicateurs appliqués à `λ_modèle` uniquement — **jamais** à `λ_marché`,
qui intègre déjà l'information publique.

Règles strictes (barème complet dans `06_FACTEURS_CONTEXTUELS.md`) :

- produit total des ajustements borné à **[0,80 ; 1,25]** par équipe ;
- au maximum **trois** facteurs simultanés ;
- chaque facteur doit être **vérifiable** et **daté** ;
- une information déjà reflétée dans le mouvement de cote ne se compte
  **pas deux fois**.

```python
res = fe.price_match(model=model, home="Guingamp", away="Amiens",
                     adj_home=0.92,      # titulaire majeur absent
                     adj_away=1.00,
                     market={"1x2": [2.35, 3.20, 3.30]}, w_market=0.55)
```

---

## Phase 4 — Fusion

Pooling log-linéaire des intensités : `λ = λ_modèle^(1−w) · λ_marché^w`.

| Palier | Exemples | `w_marché` |
|--------|----------|------------|
| 1 — très efficient | Premier League, Liga, Serie A, Bundesliga, Ligue 1, C1 | 0,65 – 0,80 |
| 2 — efficient | Championship, 2. Bundesliga, Serie B, Eredivisie, Liga Portugal, MLS | 0,50 – 0,65 |
| 3 — moyen | Ligue 2, Segunda, 3e divisions majeures, championnats scandinaves | 0,40 – 0,55 |
| 4 — mou | Féminin élite, D2 mineures, coupes tours préliminaires | 0,25 – 0,45 |

Deux correctifs :

- **Modèle peu fiable** (< 8 matchs sur une équipe, promu, mercato lourd) :
  `w_marché` +0,15.
- **Marché peu liquide** (marge > 6 %, cotes figées, opérateur unique) :
  `w_marché` −0,10.

**Ne jamais descendre sous `w_marché = 0,20` quand un marché liquide existe.**

**Ce tableau n'est qu'un point de départ.** Dès que vous disposez de deux
saisons du championnat avec des cotes, mesurez-le :

```bash
python3 engine/footyedge.py tune --csv data/history/ligue2.csv
```

La courbe de `w_marché` est en U. Son minimum donne la valeur à retenir, et sa
position dit si le modèle apporte quelque chose : un minimum en `w = 1`
signifie qu'il n'apporte rien et qu'il ne faut pas parier le 1X2.

---

## Phase 5 — Tarification

Une seule grille de scores alimente tous les marchés : aucun prix ne peut
contredire un autre.

```python
grid = fe.ScoreGrid.from_lambdas(lh, la, rho=-0.04)
book = fe.build_book(grid)
```

Marchés produits : 1X2, double chance, DNB, handicaps asiatiques (quarts
compris), totaux, totaux par équipe, BTTS, pair/impair, multi-buts, marge de
victoire, scores exacts, mi-temps et MT/FT.

---

## Phase 6 — Confrontation

```python
res = fe.price_match(..., offered={
    "1x2": {"home": 2.45, "draw": 3.40, "away": 3.10},
    "ou":  {"2.5": {"over": 1.98, "under": 1.92}},
    "ah":  {"-0.25": {"home": 1.97, "away": 1.93}},
    "btts": {"yes": 1.85, "no": 1.95}})
print(fe.render_match(res, "Guingamp", "Amiens", "Ligue 2"))
```

Les cotes peuvent être données **par opérateur** — le moteur retient alors la
meilleure et chiffre le gain par rapport à la médiane :

```python
offered = {"1x2": {"home": {"BookA": 2.42, "BookB": 2.55}, "draw": 3.40}}
```

Trois nombres par pari :

- `edge` = espérance par unité misée ;
- `σ` = écart-type de la probabilité estimée — information de Fisher du
  modèle, dispersion de devig, désaccord avec le marché ;
- `z` = edge / (σ · cote) — **le vrai critère de tri**. Un edge de 6 % à
  σ = 5 % est plus fragile qu'un edge de 3 % à σ = 1 %.

Seuil de retenue : `edge ≥ seuil du palier` **et** `z ≥ 1,0`. Le moteur
applique désormais les deux conditions lui-même.

Chaque pari retenu porte en plus son **seuil de bascule** : de combien le
total du match doit bouger pour que l'avantage disparaisse. C'est la réponse
chiffrée à l'exigence d'invalidation.

---

## Phase 7 — Mise

```python
plan = fe.stake_plan(bets, bankroll=2000, kelly_fraction=0.20,
                     max_per_bet=0.02, max_total=0.08,
                     correlation_haircut=0.35)
```

Enchaînement des garde-fous : Kelly fractionnaire → décote σ → pénalité de
désaccord modèle/marché → plafond par pari → décote de corrélation intra-groupe
→ plafond d'exposition totale. Barème complet dans `07_STAKING_RISQUE.md`.

---

## Phase 8 — Journal

Une ligne par pari, **écrite avant le coup d'envoi**, jamais après.
Colonnes : voir `data/bets_log_template.csv`. Les champs `closing_*` et
`result` sont complétés après coup ; les champs de décision ne sont
**jamais** modifiés rétroactivement.

---

## Phase 9 — Post-match

1. Renseigner les cotes de clôture → CLV déviguée.
2. Renseigner le résultat → rendement.
3. Toutes les 50 lignes : `/calib` (courbe de fiabilité, ECE).
4. Toutes les 200 lignes : `/audit` complet + décision de continuer, réduire
   ou arrêter (critères d'arrêt dans `08_CALIBRATION_AUDIT.md` §6).

**Le post-mortem porte sur la décision, jamais sur le résultat.** La bonne
question n'est pas « ai-je gagné ? » mais « referais-je ce pari avec la même
information ? ».

---

## Cadence d'utilisation recommandée

| Fréquence | Action |
|-----------|--------|
| Hebdomadaire | Réajuster le modèle (`/fit`) avec les résultats de la journée |
| Avant chaque journée | `/slate` sur les rencontres retenues |
| J−1 à J−0 | Réévaluer après compositions officielles (≈ 1 h avant) |
| Après chaque journée | Saisir clôtures et résultats |
| Toutes les 50 lignes | `/calib` |
| Toutes les 200 lignes | `/audit` + décision |
| Chaque intersaison | Refit complet, `tune` sur la saison écoulée, révision des priors et des paliers |
