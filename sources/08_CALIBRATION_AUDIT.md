# 08 — CALIBRATION, MESURE ET AUDIT

Ce que vous ne mesurez pas, vous ne le contrôlez pas. Cette page définit les
indicateurs, les seuils et les critères d'arrêt.

---

## 1. Les quatre indicateurs, par ordre d'importance

| Rang | Indicateur | Ce qu'il mesure | Converge en |
|---|---|---|---|
| 1 | **CLV** | Votre information bat-elle la clôture ? | 100 – 200 paris |
| 2 | **RPS hors échantillon** | Vos probabilités sont-elles meilleures que celles du marché ? | 300 – 500 matchs |
| 3 | **Calibration (ECE)** | Vos 60 % sortent-ils 60 % du temps ? | 300 – 500 paris |
| 4 | **ROI** | Avez-vous gagné de l'argent ? | 1 000 – 2 000 paris |

Le ROI est le dernier de la liste, et c'est délibéré : c'est celui qui met le
plus longtemps à devenir informatif. Un système jugé sur trois mois de ROI est
un système jugé sur du bruit.

---

## 2. Le RPS et son étalon

Le *Ranked Probability Score* est la métrique de référence du 1X2 : il tient
compte de l'ordre naturel des issues, et pénalise moins « 1 au lieu de X »
que « 1 au lieu de 2 ».

```
RPS = 1/(r−1) · Σ_{i=1}^{r−1} ( Σ_{j≤i} p_j − Σ_{j≤i} y_j )²
```

Ordres de grandeur sur du 1X2 de championnat :

| RPS moyen | Interprétation |
|---|---|
| 0,333 | Prédiction uniforme (1/3, 1/3, 1/3) |
| ≈ 0,22 – 0,23 | Prior de championnat seul, sans information d'équipe |
| ≈ 0,19 – 0,21 | Marché efficient (cotes de clôture déviguées) |
| < marché − 0,005 | Modèle qui apporte réellement de l'information |

**Le test décisif.** Dans un backtest walk-forward, comparez trois séries :
modèle seul, marché seul, fusion. Si la fusion ne bat pas le marché, votre
poids `w_marché` est trop faible — ou le modèle n'apporte rien.

```python
bt = fe.backtest(matches, min_train=300, refit_every_days=21, w_market=0.6)
print(bt["summary"]["rps"])            # {'model':…, 'market':…, 'blend':…}
print(bt["summary"]["rps_edge_vs_market"])
```

**Ne devinez pas `w_marché`, mesurez-le.** La commande `tune` balaie
demi-vie × rétrécissement × poids du marché et renvoie la configuration qui
minimise le RPS hors échantillon, plus la sensibilité marginale de chaque
paramètre :

```bash
python3 engine/footyedge.py tune --csv data/history/ligue2.csv \
    --half-lives 90 150 240 360 --regs 0.5 1 2
```

La courbe de `w_marché` est en U : elle vous dit à la fois si votre modèle
apporte quelque chose (minimum strictement à l'intérieur de [0 ; 1]) et
combien lui accorder.

Un gain de **0,003 à 0,008** de RPS sur le marché est déjà un très bon
résultat. Un gain supérieur à 0,02 doit déclencher une recherche de fuite
d'information, pas une célébration.

---

## 3. Calibration

Un système calibré vérifie : parmi les paris annoncés à 60 %, environ 60 %
passent. La calibration est **indépendante** de la rentabilité — on peut être
parfaitement calibré et perdre (si on paie la marge), ou mal calibré et gagner.

```bash
python3 engine/footyedge.py calib --log data/journal.csv
```

Cette commande lit le journal et produit d'un coup : CLV (moyen, IC95, taux
battu-clôture), courbe de fiabilité et ECE, ROI avec t-statistique et nombre
de paris encore nécessaires pour conclure, drawdown maximal, segmentation par
championnat et par marché, et **les critères d'arrêt du §6 automatiquement
déclenchés**. C'est l'implémentation de `/calib` et du cœur de `/audit`.

Elle signale aussi le cas où la cote de clôture n'est pas déviguée — le CLV
est alors surestimé de la marge entière.

En bibliothèque :

```python
rows = fe.load_bets_log("data/journal.csv")
rep = fe.analyse_log(rows)
print(fe.render_log_report(rep))
print(rep["clv"]["verdict"], rep["stop_criteria_triggered"])
```

| ECE | Diagnostic |
|---|---|
| < 0,02 | Excellent |
| 0,02 – 0,04 | Correct |
| 0,04 – 0,07 | Recalibrage nécessaire |
| > 0,07 | Modèle non exploitable en l'état |

### Corriger, et pas seulement mesurer

Le moteur sait aussi **recalibrer** : mise à l'échelle vectorielle sur les
log-probabilités,

```
p_calibré ∝ exp( log(p_k) / T + b_k )
```

`T` corrige la sur-confiance globale (T > 1 aplatit), les `b_k` un biais
systématique par issue — typiquement le nul. Trois paramètres seulement : le
sur-ajustement est négligeable et la transformation est monotone, donc elle ne
peut jamais inverser un classement de probabilités.

Comportement sur cas témoins, où la bonne réponse est connue :

| Cas témoin | Température estimée | ECE avant | ECE après | Log-perte |
|---|---|---|---|---|
| modèle sur-confiant (exposant 1,6) | **1.175** | 0.0581 | 0.0001 | +0.01605 |
| modèle déjà calibré | **0.976** | 0.0091 | 0.0000 | +0.00054 |
| modèle sous-confiant (exposant 0,7) | **0.923** | 0.0434 | 0.0001 | +0.00945 |

Sur un modèle sur-confiant, l'ECE tombe de 0,058 à 0,000 et la log-perte
s'améliore de 0,016. Sur un modèle déjà calibré, la température reste à 0,98 :
la correction ne fait rien, ce qui est le comportement souhaité.

```bash
python3 engine/footyedge.py backtest --csv data/history/ligue2.csv --calibrate
```

En backtest, la recalibration est réajustée à chaque refit **sur les seules
prédictions passées** et appliquée aux suivantes : aucune fuite. Le rapport
donne les métriques avant et après.

> **Attention — la recalibration n'est pas gratuite.** Sur un modèle déjà
> proche de la calibration, elle améliore l'ECE mais coûte de la *finesse* :
> aplatir les probabilités réduit la log-perte des cas mal classés et augmente
> celle des cas bien classés. Sur nos données synthétiques, ECE 0,025 → 0,014
> mais log-perte **dégradée** de 0,003.
>
> Règle : n'activer la recalibration que si l'ECE dépasse **0,04**, et la
> conserver seulement si la log-perte hors échantillon s'améliore aussi. Le
> backtest donne les deux ; la décision est mesurée, pas dogmatique.

**Défauts typiques et correctifs :**

| Motif dans les bacs | Cause probable | Correctif |
|---|---|---|
| Extrêmes trop confiants (90 % → 80 % observé) | Sur-ajustement, `reg` trop faible | `tune` pour `reg` et `w_marché` ; recalibration si l'ECE reste > 0,04 |
| Tout tassé vers 33 % | Sous-ajustement, demi-vie trop longue | Réduire la demi-vie |
| Nuls systématiquement sous-estimés | `ρ` mal ajusté ou fixé à 0 | Réajuster `ρ` |
| Bon en 1X2, mauvais en totaux | Suprématie correcte, total faux | Vérifier les priors de total du championnat |

---

## 4. Le CLV en pratique

```python
c = fe.clv(taken_odds=2.10, closing_odds=2.00, closing_fair_odds=1.95)
# clv_fair = 2.10/1.95 − 1 = +7,7 %
```

**À toujours faire :**
- Utiliser la cote de clôture **déviguée** d'un opérateur à faible marge.
  Comparer à une cote brute d'un opérateur généraliste surestime le CLV de la
  marge entière.
- Segmenter par **fenêtre de prise** (J−3 / J−1 / H−1), par **championnat** et
  par **type de marché**. Un CLV global positif peut masquer un segment
  fortement négatif.
- Consigner aussi le CLV des paris **non joués** faute de seuil : c'est la
  meilleure façon de savoir si vos seuils sont trop stricts.

**Barème** (voir aussi `03_MARCHE_DEVIG_CLV.md` §5) : > +2 % excellent,
+0,5 à +2 % correct, −0,5 à +0,5 % nul, < −0,5 % arrêter.

---

## 5. Combien de paris pour savoir ?

Pour distinguer un avantage réel du hasard à 95 % :

```
n ≈ ( 1,96 · σ_rendement / rendement_moyen )²
```

Avec une volatilité typique du rendement par pari (≈ 1,0 à cote 2,00 ;
davantage sur cotes élevées) :

| Avantage réel | Paris nécessaires (ROI) | Paris nécessaires (CLV) |
|---|---|---|
| 1 % | ≈ 38 000 | ≈ 2 000 |
| 2 % | ≈ 9 600 | ≈ 500 |
| 3 % | ≈ 4 300 | ≈ 250 |
| 5 % | ≈ 1 500 | ≈ 100 |
| 8 % | ≈ 600 | ≈ 50 |

```python
print(fe.roi_significance(returns))    # t, n_required_95
print(fe.bootstrap_ci(returns))        # IC bootstrap du ROI
```

**Conséquence stratégique.** À raison de 5 paris par semaine, 4 300 paris
représentent seize ans. Vous ne saurez jamais par le ROI si votre système
fonctionne. **Le CLV n'est pas un indicateur secondaire : c'est le seul
utilisable à l'échelle d'une vie humaine.**

---

## 6. Critères d'arrêt

Décidés **à l'avance**, appliqués sans discussion. Écrire ces seuils avant de
commencer est la seule protection contre la rationalisation a posteriori.

| Condition | Action |
|---|---|
| CLV moyen < −0,5 % sur 150 paris | Arrêt des mises, audit complet |
| ECE > 0,07 sur 300 paris | Arrêt, recalibrage du modèle |
| RPS de la fusion > RPS du marché sur 400 matchs | `w_marché` = 1 ; on ne parie plus que les dérivés |
| Drawdown > 35 % | Arrêt, audit avant reprise |
| Trois mois sans respecter le journal | Arrêt : sans données, il n'y a plus de système |
| Un pari hors barème de mise | Arrêt de la journée, analyse de la cause |

---

## 7. Procédure d'audit (toutes les 200 lignes de journal)

1. **Intégrité des données** — lignes complètes, cotes de clôture renseignées,
   aucune modification rétroactive d'un champ de décision.
2. **CLV** — global, puis par championnat, fenêtre de prise et type de marché.
3. **Calibration** — bacs de fiabilité et ECE, sur les paris joués **et** sur
   l'ensemble des matchs tarifés.
4. **RPS** — backtest walk-forward complet, comparé au marché.
5. **Mise** — vérifier qu'aucun plafond n'a été dépassé ; recompter
   l'exposition maximale réellement atteinte.
6. **Décomposition du résultat** —
   `résultat = avantage réel + chance + erreur de mise`. Estimer la part de
   chance en comparant le ROI réalisé au ROI attendu
   (`Σ mise_i · edge_i` divisé par la mise totale).
7. **Décision explicite** : continuer / réduire / modifier / arrêter. Écrite
   et datée.

```bash
# 1. Le journal : CLV, calibration, rendement, segments, criteres d'arret
python3 engine/footyedge.py calib --log data/journal.csv

# 2. Le modele : validation temporelle et comparaison au marche
python3 engine/footyedge.py backtest --csv data/history/ligue2.csv \
  --min-train 300 --refit 21 --w 0.5 --min-edge 0.04 \
  --out audit_l2.json --bets-out audit_l2_bets.csv
```

**Segmenter est l'étape la plus instructive.** Un exemple réel de sortie :
le segment au meilleur ROI (+23 %) était celui au plus mauvais CLV (−0,7 %),
et les trois segments à CLV positif affichaient un ROI négatif. Sur quelques
dizaines de paris, le ROI mesure surtout la chance ; le CLV mesure le
processus. Piloter au ROI aurait conduit à renforcer le seul segment sans
avantage et à abandonner les trois autres.

---

## 8. Fuites d'information : la liste à vérifier

La fuite est la première cause de backtest trop beau. Six vérifications :

| Fuite | Symptôme | Contrôle |
|---|---|---|
| Ajustement sur toute la période puis test dessus | RPS anormalement bas | Le backtest doit refaire l'ajustement à chaque date |
| Cotes de clôture utilisées comme cotes de pari | ROI très élevé, CLV nul | Séparer strictement `odds_*` et `close_*` |
| Résultat utilisé dans un ajustement contextuel | Gain concentré sur peu de matchs | Relire les ajustements du journal |
| Choix des seuils après avoir vu les résultats | Seuils « ronds » très performants | Fixer les seuils avant, les tester après |
| Sélection du championnat après coup | Un seul championnat porte tout le résultat | Analyser tous les championnats testés |
| Équipes renommées ou fusionnées dans l'historique | Notes aberrantes | Contrôler la table des forces |

Le moteur protège du premier point (`backtest` réajuste par fenêtre glissante)
et du second (colonnes distinctes). Les quatre autres relèvent de la
discipline.

---

## 9. Journal : le contrat

Le journal est le seul actif durable du système. Le modèle se refait en une
heure ; trois ans de journal, jamais.

**Écrit avant le coup d'envoi**, jamais après :
`date, competition, match, marche, selection, cote_prise, operateur, proba_modele, proba_marche, edge, sigma, fraction_kelly, mise, banque_avant, w_marche, ajustements, note`

**Complété après :**
`cote_cloture, cote_cloture_devig, clv, resultat, gain, banque_apres`

**Jamais modifié :** tout champ de décision. Une erreur se corrige par une
ligne d'annulation datée, jamais par une réécriture.

Modèle : `data/bets_log_template.csv`.
