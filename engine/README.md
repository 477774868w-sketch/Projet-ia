# engine/ — le moteur

`footyedge.py` : moteur quantitatif mono-fichier, **zéro dépendance externe**
(bibliothèque standard de Python 3.8+ uniquement).

Ce choix est délibéré : le fichier doit pouvoir être déposé comme source d'un
Projet et exécuté tel quel par un assistant, sans `pip install`, sans réseau,
sans environnement virtuel.

## Vérifier

```bash
python3 footyedge.py selftest     # 193 contrôles internes
python3 footyedge.py demo         # démonstration guidée
python3 footyedge.py --help       # toutes les commandes
```

## Organisation du fichier

| § | Contenu | Points d'entrée |
|---|---|---|
| 1 | Utilitaires numériques | `poisson_pmf`, `nbinom_pmf`, `bisect`, `Adam` |
| 2 | Grille de scores | `ScoreGrid.from_lambdas`, `dixon_coles_tau` |
| 3 | Retrait de marge | `devig`, `devig_shin`, `devig_power` |
| 4 | Inversion du marché | `lambdas_from_1x2`, `lambdas_from_asian` |
| 5 | Fusion | `log_pool`, `blend_lambdas` |
| 6 | Mi-temps | `halves_analysis` |
| 7 | Estimation des forces | `fit_dixon_coles`, `DixonColesModel` |
| 8 | Elo à buts | `EloRatings` |
| 9 | Mise | `kelly_single`, `kelly_asian`, `kelly_exclusive`, `stake_plan` |
| 10 | Métriques | `rps`, `brier_multiclass`, `reliability_bins`, `clv` |
| 11 | Tarification complète | `price_match`, `build_book`, `scan_value` |
| 11b | Rendu lisible | `render_match` |
| 12 | Monte-Carlo | `simulate_season`, `simulate_parlay` |
| 13 | Entrées/sorties CSV | `load_matches_csv` |
| 14 | Backtest | `backtest` |
| 15 | Données synthétiques | `synthetic_league`, `add_synthetic_odds` |
| 16 | Auto-test | `selftest` |
| 17 | Ligne de commande | `main` |

## Usage en bibliothèque

```python
import sys; sys.path.insert(0, "engine")
import footyedge as fe

# 1. Lire le marché
dv = fe.devig([2.10, 3.40, 3.60])
lh, la = fe.lambdas_from_1x2(*dv["probs"], rho=-0.04)

# 2. Tarifer tous les marchés
grid = fe.ScoreGrid.from_lambdas(lh, la, -0.04)
book = fe.build_book(grid)

# 3. Chercher la valeur et dimensionner la mise
res = fe.price_match(lam_home=lh, lam_away=la, rho=-0.04,
                     market={"1x2": [2.10, 3.40, 3.60]}, w_market=0.6,
                     offered={"btts": {"yes": 2.05}},
                     bankroll=1000, kelly_fraction=0.25)
print(fe.render_match(res, "Domicile", "Extérieur"))
```

## Conventions

- **Handicap asiatique** : `line` s'applique toujours à l'équipe **à
  domicile**. `asian_handicap(-0.75)` = domicile rend 0,75 but.
- **Lignes quarts** : décomposées en deux demi-mises. Les probabilités sont
  moyennées, la cote équitable est recalculée après moyennage.
- **`prob_norm`** : probabilité hors remboursement, `win / (win + lose)`.
  C'est la valeur à comparer à une cote de type « 2,00 ».
- **`rho`** : borné automatiquement à l'intervalle qui garantit des
  probabilités positives.
- **Sortie JSON** : toutes les commandes renvoient du JSON par défaut ;
  `--brief` produit la fiche lisible sur `price` et `predict`.

## Performance (Python pur, sans accélération)

Mesures sur cette machine (Python 3.11, un seul cœur), à titre d'ordre de
grandeur :

| Opération | Temps |
|---|---|
| Construire une grille 13×13 | 0,04 ms |
| Tarifer tous les marchés d'un match (`build_book`) | 1,8 ms |
| Inverser un 1X2 en intensités | 28 ms |
| Inverser des lignes asiatiques (handicap + total) | 34 ms |
| Ajuster 1 520 matchs, 600 itérations | 0,54 s |
| Simuler 190 matchs × 10 000 saisons | 1,5 s |
| Combiné corrélé, 50 000 tirages | 38 ms |
| Backtest walk-forward de 1 520 matchs (1 120 tarifés) | 31 s |

Le poste dominant est **l'inversion du marché** : deux bissections imbriquées
qui reconstruisent une grille à chaque évaluation. C'est elle, et non
l'ajustement du modèle, qui pèse dans un backtest — un match tarifé coûte
environ 30 ms d'inversion contre 0,4 ms d'ajustement amorti.

Deux leviers si nécessaire : `INVERT_TOL` (tolérance des inversions, réglée à
1e-7, soit trois ordres de grandeur sous la précision d'une cote affichée) et
le démarrage à chaud `init_model`, déjà activé dans le backtest.
