# 09 — DÉRIVATION DE TOUS LES MARCHÉS

Un seul objet probabiliste, `P(i, j)` = probabilité du score exact
(i buts domicile, j buts extérieur), engendre l'intégralité des marchés.
Aucun prix ne peut alors en contredire un autre.

---

## 1. Table de dérivation

Notations : `M = i − j` (marge), `T = i + j` (total).

| Marché | Formule sur la grille |
|---|---|
| 1 (domicile) | `Σ P(i,j)` pour `i > j` |
| X (nul) | `Σ P(i,i)` |
| 2 (extérieur) | `Σ P(i,j)` pour `i < j` |
| Double chance 1X | `P(1) + P(X)` |
| Draw no bet domicile | `P(1) / (P(1) + P(2))` |
| Plus de n,5 buts | `Σ P(i,j)` pour `T > n` |
| Total exactement n | `Σ P(i,j)` pour `T = n` (remboursement d'une ligne entière) |
| Handicap asiatique dom. ligne `h` | gain si `M > −h`, remboursé si `M = −h` |
| Handicap asiatique ext. ligne `h` | gain si `M < −h`, remboursé si `M = −h` |
| BTTS oui | `Σ P(i,j)` pour `i ≥ 1` et `j ≥ 1` |
| Clean sheet domicile | `Σ_i P(i, 0)` |
| Victoire domicile sans encaisser | `Σ_{i≥1} P(i, 0)` |
| Total équipe domicile > n,5 | `Σ P(i,j)` pour `i > n` |
| Pair / impair | parité de `T` |
| Multi-buts [a ; b] | `Σ P(i,j)` pour `a ≤ T ≤ b` |
| Marge de victoire = k | `Σ P(i,j)` pour `M = k` |
| Score exact (i,j) | `P(i,j)` |

Les deux lignes des handicaps asiatiques partagent **le même seuil** `−h` :
seul le sens de comparaison change. C'est la source d'erreur la plus courante
dans les implémentations maison — elle produit des prix incohérents entre les
deux camps sans que rien ne le signale.

Contrôle : `1/cote_juste_dom + 1/cote_juste_ext = 1` exactement, pour toute
ligne. Le moteur le vérifie sur quinze lignes à chaque auto-test.

---

## 2. Lignes quart (x,25 et x,75)

Une ligne quart est **deux paris de demi-mise** sur les deux demi-lignes
adjacentes.

```
AH −0,25  =  ½ sur AH 0,00  +  ½ sur AH −0,50
Plus 2,25 =  ½ sur Plus 2,0 +  ½ sur Plus 2,5
```

Probabilités : moyenne des deux composantes.
Cote équitable : `1 + perte_moyenne / gain_moyen`.

**Attention.** La cote équitable d'une ligne quart n'est **pas** la moyenne
des cotes équitables des deux demi-lignes. Il faut moyenner les probabilités
de gain et de perte, puis calculer la cote. L'erreur est de l'ordre de 1 à 3 %
— soit l'avantage entier.

---

## 3. Mi-temps

Le moteur décompose le match en deux mi-temps indépendantes :

```
λ_1re mi-temps = λ × 0,455        λ_2e mi-temps = λ × 0,545
```

La part de 45,5 % est un prior robuste : on marque un peu plus en seconde
période (fatigue, prises de risque, temps additionnel plus long).

```python
hv = fe.halves_analysis(1.85, 0.95, rho=-0.05, h1_share=0.455)
hv["ht_1x2"]      # 1X2 à la mi-temps
hv["htft"]        # les 9 combinaisons mi-temps / fin de match
```

**Propriété de cohérence.** La somme de deux lois de Poisson étant une loi de
Poisson, la grille temps plein reconstruite à partir des deux mi-temps
coïncide avec la grille directe. L'auto-test le vérifie à 0,3 point près
(l'écart résiduel vient de la correction Dixon-Coles appliquée par mi-temps).

**Où est la valeur.** Beaucoup d'opérateurs dérivent la mi-temps par une règle
de trois (`λ/2`), ce qui surévalue la première période d'environ 9 %. Sur les
totaux de mi-temps, l'écart est directement exploitable.

**Ajustements légitimes de `h1_share` :**
- équipe très supérieure attendue pour « gérer » en seconde période : 0,47 ;
- match à enjeu défensif fort (barrage retour, maintien) : 0,44 ;
- forte chaleur : 0,47 (rythme qui chute davantage en seconde période).

---

## 4. Scores exacts

Marché à forte marge (souvent 15 à 25 %) et à très forte variance. Deux
usages légitimes :

1. **Contrôle de cohérence** : la somme des scores exacts doit reconstituer
   exactement le 1X2 et les totaux. Si un opérateur affiche des scores exacts
   incompatibles avec son propre 1X2, il y a une erreur de tarification quelque
   part — souvent exploitable.
2. **Couverture** : combiner plusieurs scores exacts pour reproduire un
   marché non proposé (par exemple « victoire par exactement deux buts »).

Ne pas jouer un score exact isolé pour son avantage nominal : la variance
détruit tout intérêt pratique, et la marge y est la plus élevée du marché.

---

## 5. Marchés hors périmètre du modèle de buts

| Marché | Traitement |
|---|---|
| Cartons | Modèle séparé : profil d'arbitre + enjeu + rivalité. **Pas** dérivable de la grille de buts |
| Corners | Corrélé au total de buts et à la domination, mais loi différente (moyenne ≈ 10, variance plus faible) |
| Tirs, possession | Marchés statistiques : modèle dédié |
| Buteurs | Nécessite une répartition des buts par joueur ; à partir de la grille et des parts de tirs |
| Temps du premier but | Déductible : `P(pas de but avant t) = exp(−T·t/90)` en intensité constante |

Règle du système : **ne pas tarifer un marché dont le modèle générateur n'est
pas explicité.** Un prix sans modèle est une opinion.

---

## 6. Buteurs : méthode approchée

À partir de `λ_équipe` et de la part `s_j` de joueur `j` dans les buts de son
équipe (moyenne mobile sur 15 matchs, régressée vers la moyenne du poste) :

```
λ_joueur = λ_équipe × s_j × (minutes attendues / 90)
P(marque au moins un but) = 1 − exp(−λ_joueur)
```

Limites à annoncer : la part `s_j` est instable sur moins de 15 matchs ; les
penalties doivent être traités séparément (tireur désigné) ; les minutes
attendues sont l'entrée la plus incertaine. Élargir σ en conséquence, et ne
jamais miser plus de 1 % sur ce type de marché.

---

## 7. Combinés : la corrélation change tout

Multiplier les probabilités de deux sélections du **même match** est faux, et
l'erreur est très supérieure à l'avantage recherché.

Match de référence : λ = 1,85 − 0,95 (ρ = −0,05).

| Combinaison sur le MÊME match | Naïf (produit) | Réel (grille) | Écart relatif | Cote juste naïve | Cote juste réelle |
|---|---|---|---|---|---|
| Domicile gagne + plus de 2,5 buts | 30.8% | 36.9% | +20% | 3.25 | 2.71 |
| Domicile gagne + moins de 2,5 buts | 27.2% | 21.1% | -22% | 3.67 | 4.73 |
| Domicile gagne + BTTS oui | 30.3% | 25.9% | -14% | 3.30 | 3.86 |
| Domicile gagne + BTTS non | 27.7% | 32.1% | +16% | 3.61 | 3.12 |
| Nul + moins de 2,5 buts | 11.1% | 17.8% | +61% | 9.04 | 5.61 |
| Plus de 2,5 buts + BTTS oui | 27.7% | 41.0% | +48% | 3.61 | 2.44 |

**Lecture.** « Nul + moins de 2,5 buts » vaut réellement 17,8 %, pas 11,1 % :
la multiplication naïve sous-estime de **61 %**. Un opérateur qui tarife
naïvement offre 9,04 là où le prix juste est 5,61 — c'est un avantage énorme.
Inversement, « domicile gagne + moins de 2,5 buts » est **surévalué** de 22 %
par le calcul naïf : le pari paraît bon et ne l'est pas.

**Sens des corrélations à retenir :**
- Total et BTTS : fortement corrélés positivement.
- Nul et total bas : fortement corrélés positivement.
- Victoire nette et BTTS : corrélés négativement.
- Victoire et total : dépend de la suprématie — positif si le favori est net,
  quasi nul sur un match équilibré.

**Méthode correcte, toujours :**

```python
legs = [{"grid": g, "match_id": "m1", "test": lambda h, a: h > a},
        {"grid": g, "match_id": "m1", "test": lambda h, a: h + a > 2.5}]
print(fe.simulate_parlay(legs, n_sims=50000))
```

**Combinés de matchs différents.** Là, la multiplication est correcte — sauf
si les matchs partagent un facteur commun (même journée, même météo, même
championnat en fin de saison). Dans le doute, appliquer la décote de
corrélation de `07_STAKING_RISQUE.md` §5.2.

**Position du système.** Les combinés multiplient les marges : deux
sélections chez un opérateur à 5 % de marge coûtent environ 10 %. Ils ne sont
justifiés que lorsque la corrélation est **positive et mal tarifée par
l'opérateur** — cas réel, mais rare, et à démontrer par simulation avant de
miser.

---

## 8. Encaissement anticipé et trading

L'encaissement proposé par un opérateur intègre systématiquement une marge
supplémentaire, souvent 5 à 10 %. Il n'a d'intérêt que dans deux cas :

1. **Re-tarification** : une information nouvelle (carton rouge, blessure)
   rend votre probabilité initiale caduque, et la valeur proposée dépasse
   votre nouvelle estimation.
2. **Contrainte de risque** : l'exposition dépasse vos plafonds à la suite
   d'un événement imprévu.

Dans tous les autres cas, encaisser revient à payer une seconde fois la marge
pour acheter du confort psychologique. Le calcul est simple : encaisser vaut
la peine si `montant_proposé > p_actuelle × gain_potentiel`.
