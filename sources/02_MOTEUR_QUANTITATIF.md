# 02 — MOTEUR QUANTITATIF

Tout le système repose sur un objet unique : la **distribution jointe des
scores**. On l'estime, puis on en déduit tous les prix. Aucun marché n'est
modélisé séparément — c'est la garantie d'absence de contradiction interne.

---

## 1. Le modèle génératif

Pour une rencontre entre `i` (domicile) et `j` (extérieur) :

```
λ_dom = exp( μ + h + att_i + def_j )
λ_ext = exp( μ +     att_j + def_i )
```

- `μ` : niveau de buts du championnat (log) ;
- `h` : avantage du terrain, en log — typiquement 0,18 à 0,28, soit ×1,20 à
  ×1,32 sur l'intensité à domicile ;
- `att` : force offensive (moyenne nulle sur le championnat) ;
- `def` : **faiblesse** défensive (positif = encaisse plus).

La grille de scores combine deux marginales de Poisson **corrigées** par le
terme de Dixon-Coles :

```
τ(0,0) = 1 − λ_dom·λ_ext·ρ      τ(0,1) = 1 + λ_dom·ρ
τ(1,0) = 1 + λ_ext·ρ            τ(1,1) = 1 − ρ
τ(i,j) = 1 ailleurs
```

`ρ` est typiquement compris entre −0,15 et −0,02. Il corrige un défaut réel
de l'hypothèse d'indépendance : les 0-0 et 1-1 sont **plus fréquents** que le
Poisson pur ne le prévoit, les 1-0 et 0-1 un peu moins. Sans cette correction
on sous-évalue systématiquement le nul de 1 à 2 points de pourcentage — soit
plus que l'avantage moyen d'un pari.

### Reparamétrage utile

Les praticiens raisonnent en **(total, suprématie)** :

```
Total T = λ_dom + λ_ext        Suprématie S = λ_dom − λ_ext
λ_dom = (T + S)/2              λ_ext = (T − S)/2
```

C'est la grammaire du marché asiatique : la ligne de handicap encode `S`, la
ligne de total encode `T`. Les deux dimensions sont quasi orthogonales — un
avantage sur l'une n'entraîne pas d'avantage sur l'autre.

---

## 2. Pourquoi Poisson, et où il casse

**Ce qui marche.** Les buts arrivent comme des événements rares, quasi
indépendants dans le temps, avec une intensité à peu près constante. Le nombre
de buts d'une équipe suit de fait une loi proche de Poisson.

**Ce qui casse, et le correctif appliqué :**

| Défaut | Symptôme | Correctif du moteur |
|--------|----------|---------------------|
| Dépendance des scores bas | Nuls sous-évalués | Correction Dixon-Coles `ρ` |
| Sur-dispersion | Cartons et 0-0 trop rares | Marginales binomiales négatives (`shape`) |
| Intensité non constante | Plus de buts en fin de match | Décomposition en mi-temps (`h1_share ≈ 0,455`) |
| Effet du score en cours | Une équipe menée attaque plus | Modèle *live* seulement — hors périmètre pré-match |
| Corrélation entre marchés | Combinés mal tarifés | Simulation Monte-Carlo sur la même grille |

Sur-dispersion : utiliser `shape` (paramètre de forme de la binomiale
négative) quand le championnat produit des variances anormales. Ordres de
grandeur : `shape = None` (Poisson) pour les paliers 1–2 ; `shape ≈ 12` pour
une D2 volatile ; `shape ≈ 8` pour un championnat féminin très hétérogène.
Effet : épaissit les queues, augmente les gros scores et les 0-0.

---

## 3. Estimation

Maximum de vraisemblance pondéré, gradient analytique :

```
∂LL/∂att_i = Σ_m w_m ( y_m − λ_m )
```

sur toutes les rencontres où `i` attaque. Optimiseur Adam, contrainte
d'identifiabilité (attaque et défense de moyenne nulle à chaque itération),
pénalisation L2 `reg` vers la moyenne du championnat.

`ρ` est ajusté dans un second temps par section dorée sur la vraisemblance
des scores bas seulement — les autres cellules n'apportent aucune information
sur `ρ`.

```python
model = fe.fit_dixon_coles(matches, half_life_days=180, reg=1.0)
```

---

## 4. Pondération temporelle

Poids d'un match vieux de `d` jours : `w = exp(−ln2 · d / demi-vie)`.

| Demi-vie | Comportement | Quand l'utiliser |
|----------|--------------|------------------|
| 60 j | Très réactif, bruité | Après un mercato d'hiver lourd, changement d'entraîneur |
| 120 j | Réactif | Championnats à forte rotation d'effectif |
| **180 j** | **Défaut** | Cas général, ≈ une demi-saison |
| 270 j | Stable | Championnats stables, effectifs constants |
| 365 j+ | Très stable | Petits championnats, peu de matchs par saison |

**Piège classique.** Une demi-vie courte donne de meilleures vraisemblances
*in-sample* et de moins bonnes *out-of-sample*. Choisissez-la par backtest sur
le RPS hors échantillon, jamais à l'intuition. Testez 90 / 120 / 180 / 270 et
retenez le minimum de la courbe.

---

## 5. Rétrécissement, promus, intersaison

Le paramètre `reg` tire les notes vers la moyenne du championnat. Il résout
trois problèmes distincts :

1. **Petit échantillon** — une équipe à 4 matchs ne mérite pas une note
   extrême. `reg` la ramène mécaniquement vers le centre.
2. **Promus et relégués** — ils n'ont pas d'historique dans leur nouveau
   championnat. Trois options, par qualité décroissante :
   - conserver leur historique de division inférieure **avec une pénalité de
     niveau** (voir `05_D2_ET_FEMININ.md` §3 : environ −0,35 en log
     d'intensité offensive à la montée d'un cran) ;
   - les initialiser à la moyenne du championnat, avec `w_marché` +0,20 ;
   - ne pas les jouer pendant les 6 premières journées.
3. **Intersaison** — l'effectif change. Régressez les notes de 20 à 30 % vers
   la moyenne avant la reprise (`EloRatings.new_season()` fait cela pour l'Elo).

Valeurs : `reg = 0,5` (championnat riche en données), `1,0` (défaut),
`2,0` (peu de matchs, féminin, D3).

---

## 6. xG et signaux avancés

Les buts sont un signal bruité de la performance. Sur un même nombre de
matchs, les **buts attendus** (xG) estiment la force d'une équipe avec
sensiblement moins de variance — la finition régresse fortement vers la
moyenne, la création d'occasions beaucoup moins.

```python
model = fe.fit_dixon_coles(matches, target="blend", xg_weight=0.6)
```

Recommandations :

- `target="blend"` avec `xg_weight` entre 0,5 et 0,7 : meilleur compromis.
  Le pur xG ignore une réelle compétence de finition et de gardien.
- Vérifiez la **source** et la **version** du modèle xG : deux fournisseurs
  peuvent différer de 0,3 xG sur un même match. Ne mélangez jamais deux
  sources dans un même historique.
- Sans xG, les tirs cadrés et les tirs dans la surface sont des substituts
  acceptables ; les tirs bruts, non.
- L'écart `buts − xG` cumulé sur une saison est un **indicateur de correction
  à venir**, pas une compétence. C'est l'un des rares endroits où le modèle
  peut légitimement s'écarter du marché quand le marché suit les résultats.

---

## 7. Reconstruction rapide sans historique complet

Avec seulement les 8 à 10 derniers matchs de chaque équipe :

1. Pour chaque équipe, calculer `BM` = buts marqués/match et `BE` = buts
   encaissés/match sur la fenêtre, **séparément à domicile et à l'extérieur**
   si l'échantillon le permet.
2. Ajuster de la force adverse : diviser par la moyenne du championnat, puis
   pondérer par le niveau des adversaires rencontrés si connu.
3. Régresser vers la moyenne du championnat avec un poids `k/(k+n)`, où
   `n` = nombre de matchs et `k ≈ 6` : avec 8 matchs, on conserve environ 57 %
   du signal propre, et 43 % vient de la moyenne du championnat.
4. Recomposer :
   `λ_dom = μ_championnat × ATT_dom × DEF_ext × facteur_terrain`
   avec `ATT = BM_ajusté / μ`, `DEF = BE_ajusté / μ`.

**Ne jamais** utiliser des moyennes brutes sans ajustement du calendrier : sur
8 matchs, la différence de difficulté du calendrier dépasse couramment l'écart
réel de niveau entre les deux équipes.

---

## 8. Mode dégradé (sans exécution de code)

Ces formules sont **exactes** pour des marginales de Poisson indépendantes.
Elles suffisent à 2 points de pourcentage près sur la plupart des marchés.

| Marché | Formule fermée |
|--------|----------------|
| Total ≤ n | `e^−T · Σ_{k=0..n} T^k / k!` — le total est exactement Poisson(T) |
| Plus de 2,5 buts | `1 − e^−T (1 + T + T²/2)` |
| Clean sheet dom. | `e^−λ_ext` |
| Clean sheet ext. | `e^−λ_dom` |
| BTTS oui | `1 − e^−λ_dom − e^−λ_ext + e^−T` |
| Score exact (i,j) | `e^−T · λ_dom^i λ_ext^j / (i! j!)` × τ(i,j) |
| 0-0 | `e^−T × (1 − λ_dom λ_ext ρ)` |

Pour le **1X2** et les **handicaps**, la marge suit une loi de Skellam sans
forme élémentaire simple : utilisez les tables ci-dessous.

### Table A — 1X2 en fonction du total et de la suprématie (ρ = −0,04)

Lecture : ligne = total attendu de buts, colonne = suprématie (λ_dom − λ_ext).
Chaque cellule : **P(1) / P(X) / P(2)** en %.

| Total \ Supr. | -1.50 | -1.25 | -1.00 | -0.75 | -0.50 | -0.25 | +0.00 | +0.25 | +0.50 | +0.75 | +1.00 | +1.25 | +1.50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **2.00** | 4/21/75 | 8/24/68 | 12/27/62 | 16/29/55 | 22/31/48 | 28/32/41 | 34/32/34 | 41/32/28 | 48/31/22 | 55/29/16 | 62/27/12 | 68/24/8 | 75/21/4 |
| **2.25** | 6/20/74 | 10/23/68 | 14/25/61 | 18/27/55 | 23/29/48 | 29/30/41 | 35/30/35 | 41/30/29 | 48/29/23 | 55/27/18 | 61/25/14 | 68/23/10 | 74/20/6 |
| **2.50** | 8/19/73 | 11/22/67 | 15/24/61 | 20/26/55 | 25/27/48 | 30/28/42 | 36/28/36 | 42/28/30 | 48/27/25 | 55/26/20 | 61/24/15 | 67/22/11 | 73/19/8 |
| **2.75** | 9/19/72 | 13/21/66 | 17/23/60 | 21/24/55 | 26/26/49 | 31/26/43 | 37/27/37 | 43/26/31 | 49/26/26 | 55/24/21 | 60/23/17 | 66/21/13 | 72/19/9 |
| **3.00** | 11/18/71 | 14/20/66 | 18/22/60 | 22/23/54 | 27/24/49 | 32/25/43 | 37/25/37 | 43/25/32 | 49/24/27 | 54/23/22 | 60/22/18 | 66/20/14 | 71/18/11 |
| **3.25** | 12/18/70 | 15/20/65 | 19/21/60 | 23/22/54 | 28/23/49 | 33/24/43 | 38/24/38 | 43/24/33 | 49/23/28 | 54/22/23 | 60/21/19 | 65/20/15 | 70/18/12 |
| **3.50** | 13/17/70 | 16/19/65 | 20/20/60 | 24/22/54 | 29/22/49 | 33/23/44 | 38/23/38 | 44/23/33 | 49/22/29 | 54/22/24 | 60/20/20 | 65/19/16 | 70/17/13 |

### Table B — Totaux (exacts pour des marginales de Poisson indépendantes)

| Total λ | P(+0,5) | P(+1,5) | P(+2,5) | P(+3,5) | P(+4,5) |
|---|---|---|---|---|---|
| 1.75 | 82.6% | 52.2% | 25.6% | 10.1% | 3.3% |
| 2.00 | 86.5% | 59.4% | 32.3% | 14.3% | 5.3% |
| 2.25 | 89.5% | 65.7% | 39.1% | 19.1% | 7.8% |
| 2.50 | 91.8% | 71.3% | 45.6% | 24.2% | 10.9% |
| 2.75 | 93.6% | 76.0% | 51.9% | 29.7% | 14.5% |
| 3.00 | 95.0% | 80.1% | 57.7% | 35.3% | 18.5% |
| 3.25 | 96.1% | 83.5% | 63.0% | 40.9% | 22.8% |
| 3.50 | 97.0% | 86.4% | 67.9% | 46.3% | 27.5% |
| 3.75 | 97.6% | 88.8% | 72.3% | 51.6% | 32.2% |
| 4.00 | 98.2% | 90.8% | 76.2% | 56.7% | 37.1% |

### Table C — BTTS « oui » selon total et suprématie

| Total \ Supr. | 0,00 | 0,25 | 0,50 | 0,75 | 1,00 | 1,25 | 1,50 |
|---|---|---|---|---|---|---|---|
| **2.00** | 40.5% | 39.9% | 38.2% | 35.2% | 31.0% | 25.4% | 18.5% |
| **2.25** | 46.1% | 45.6% | 44.1% | 41.5% | 37.8% | 32.9% | 26.8% |
| **2.50** | 51.4% | 51.0% | 49.6% | 47.3% | 44.0% | 39.7% | 34.4% |
| **2.75** | 56.3% | 55.9% | 54.7% | 52.7% | 49.8% | 46.0% | 41.3% |
| **3.00** | 60.8% | 60.4% | 59.4% | 57.6% | 55.1% | 51.7% | 47.5% |
| **3.25** | 64.9% | 64.6% | 63.7% | 62.1% | 59.8% | 56.9% | 53.2% |
| **3.50** | 68.6% | 68.4% | 67.5% | 66.1% | 64.2% | 61.6% | 58.3% |

### Table D — Ligne de handicap asiatique équitable selon la suprématie

Ligne pour laquelle les deux camps valent 2,00 (probabilité hors remboursement = 50 %).
Total fixé à 2,60 ; la ligne équitable dépend peu du total.

| Suprématie | Ligne AH équitable (dom.) | P(1) | P(X) | P(2) |
|---|---|---|---|---|
| +0.00 | +0.00 | 36.3% | 27.4% | 36.3% |
| +0.15 | -0.25 | 39.9% | 27.3% | 32.8% |
| +0.30 | -0.25 | 43.5% | 27.0% | 29.5% |
| +0.45 | -0.50 | 47.2% | 26.6% | 26.3% |
| +0.60 | -0.50 | 50.9% | 26.0% | 23.2% |
| +0.80 | -0.75 | 55.8% | 24.9% | 19.3% |
| +1.00 | -1.00 | 60.7% | 23.5% | 15.8% |
| +1.25 | -1.25 | 66.7% | 21.5% | 11.8% |
| +1.50 | -1.50 | 72.4% | 19.1% | 8.4% |

**Interpolation.** Linéaire entre deux cellules ; l'erreur reste sous
1 point de pourcentage sur les plages du tableau.

**Annonce obligatoire.** En mode dégradé, écrire explicitement :
« calcul en mode dégradé, précision ±2 points de probabilité ; pas de mise
au-delà du seuil d'avantage majoré de 1 point ».

---

## 9. Diagnostics du modèle

Avant de faire confiance à un modèle ajusté, vérifier :

| Diagnostic | Valeur attendue | Alerte si |
|------------|-----------------|-----------|
| `home_adv` | 0,15 – 0,30 | < 0,05 ou > 0,40 → données ou terrain neutre mal codés |
| `rho` | −0,15 – 0,00 | > +0,05 → probable erreur de sens des colonnes buts |
| `mu` | ln(moyenne buts / 2) ± 0,15 | écart important → filtre de championnat mal appliqué |
| Étendue des notes | 1,0 – 2,0 en log | > 2,5 → sur-ajustement, augmenter `reg` |
| Corrélation Elo / Dixon-Coles | > 0,85 | < 0,7 → une équipe a un profil de buts atypique |
| RPS hors échantillon vs marché | écart < 0,010 | modèle nettement battu → ne pas s'en écarter |

Le dernier point est le plus important : **si votre modèle seul ne s'approche
pas du RPS du marché en validation temporelle, il n'a pas vocation à corriger
le marché.** Il ne sert alors qu'à tarifer les marchés dérivés que l'opérateur
n'affiche pas.
