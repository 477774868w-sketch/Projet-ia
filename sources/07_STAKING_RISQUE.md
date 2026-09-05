# 07 — MISE ET GESTION DU RISQUE

Un bon modèle mal misé perd de l'argent. Un modèle moyen bien misé survit.
Cette page prime sur toutes les autres en cas de conflit.

---

## 1. Le critère de Kelly

Kelly maximise le **taux de croissance logarithmique** de la banque :

```
f* = (p · cote − 1) / (cote − 1)
```

Pour un pari à remboursement possible (handicap ou total asiatique), avec
`w` = probabilité de gain, `l` = probabilité de perte, `push` = 1 − w − l :

```
f* = ( w·(cote − 1) − l ) / ( (cote − 1)·(w + l) )
```

Le remboursement réduit le risque sans réduire l'espérance : à avantage égal,
un pari asiatique à ligne entière **supporte une mise plus élevée** qu'un
pari sec. Le moteur en tient compte automatiquement.

**Propriétés à connaître :**
- Kelly maximise la croissance à long terme et minimise le temps pour
  atteindre un objectif donné.
- Kelly ne ruine jamais mathématiquement (mise proportionnelle), mais produit
  des drawdowns extrêmes.
- **Au-delà de 2× Kelly, la croissance attendue devient négative** même avec
  un avantage réel. Le sur-pari est le mode d'échec numéro un.
- Kelly suppose `p` **connue**. En pari sportif, `p` est **estimée**. C'est la
  raison de tout ce qui suit.

---

## 2. Pourquoi une fraction, et laquelle

**Hypothèses** : 1 000 paris successifs à cote 2,00, mise = fraction de Kelly, banque réinvestie.

### Cas A — l'estimation est juste (avantage réel 3,0 %, p = 0,515)

| Fraction | Mise | Médiane finale | 1er décile | Drawdown médian | Drawdown 95e c. | P(perte > 30 %) | P(perte > 50 %) |
|---|---|---|---|---|---|---|---|
| Kelly plein | 3.00% | ×1.57 | ×0.47 | 60% | 83% | 100% | 75% |
| 1/2 Kelly | 1.50% | ×1.40 | ×0.77 | 34% | 56% | 67% | 12% |
| **1/4 Kelly** | 0.75% | ×1.22 | ×0.90 | 18% | 33% | 8% | 0% |
| 1/8 Kelly | 0.38% | ×1.11 | ×0.96 | 9% | 18% | 0% | 0% |

### Cas B — l'avantage a été surestimé de moitié (on croit 3,0 %, il vaut 1,5 %)

| Fraction | Mise | Médiane finale | 1er décile | Drawdown médian | Drawdown 95e c. | P(perte > 30 %) | P(perte > 50 %) |
|---|---|---|---|---|---|---|---|
| Kelly plein | 3.00% | ×1.03 | ×0.29 | 65% | 88% | 100% | 85% |
| 1/2 Kelly | 1.50% | ×1.14 | ×0.60 | 39% | 63% | 77% | 21% |
| **1/4 Kelly** | 0.75% | ×1.10 | ×0.80 | 21% | 38% | 16% | 0% |
| 1/8 Kelly | 0.38% | ×1.05 | ×0.90 | 11% | 21% | 0% | 0% |

### Cas C — il n'y avait aucun avantage (p réel = 0,50, marge payée)

| Fraction | Médiane finale | 1er décile | Drawdown médian | P(perte > 50 %) |
|---|---|---|---|---|
| Kelly plein | ×0.60 | ×0.18 | 72% | 92% |
| 1/2 Kelly | ×0.87 | ×0.48 | 44% | 35% |
| **1/4 Kelly** | ×0.96 | ×0.71 | 24% | 1% |
| 1/8 Kelly | ×0.99 | ×0.85 | 13% | 0% |

**Lecture des trois tableaux.**

- **Cas A (vous avez raison).** Le Kelly plein multiplie la banque par 1,57 en
  médiane, mais avec un drawdown médian de **60 %** et trois chances sur
  quatre de perdre plus de la moitié de la banque à un moment. Le quart de
  Kelly rapporte ×1,22 avec un drawdown médian de 18 % et **aucune**
  occurrence de perte de moitié. On abandonne 22 % de la croissance pour
  diviser le risque par plus de trois.
- **Cas B (vous vous êtes trompé de moitié).** Le Kelly plein perd tout son
  avantage : ×1,03, autant dire rien, pour un drawdown médian de 65 %.
  Le quart de Kelly conserve ×1,10.
- **Cas C (vous n'aviez aucun avantage).** Le Kelly plein détruit 40 % de la
  banque en médiane et 92 % des trajectoires perdent la moitié. Le quart de
  Kelly perd 4 %. **C'est la seule ligne qui compte vraiment** : elle mesure
  ce qui arrive quand on se trompe, ce qui est le cas plus souvent qu'on ne
  le croit.

> **Règle du système : 1/4 de Kelly par défaut.** 1/5 en palier 3, 1/8 en
> palier 4 et sur tout marché nouveau tant que 200 paris n'ont pas été
> consignés avec un CLV positif.

---

## 3. Décote d'incertitude

Kelly suppose `p` connue. On mise donc sur une estimation prudente :

```
p_effectif = p − z · σ        (z = 1 par défaut)
```

`σ` combine trois sources (le moteur le fait dans `estimate_sigma`) :

| Source | Contribution |
|---|---|
| Désaccord modèle / marché | la plus informative — 45 % du désaccord |
| Dispersion inter-méthodes de devig | 70 % de l'écart max entre méthodes |
| Incertitude d'estimation du modèle | **information de Fisher observée**, propagée par la méthode delta |

La troisième composante n'est pas une approximation : c'est l'écart-type réel
de l'estimation, obtenu en inversant l'information de Fisher du modèle puis en
la propageant à la probabilité du marché considéré
(`02_MOTEUR_QUANTITATIF.md` §5 ter). Conséquence concrète : **deux équipes peu
vues produisent mécaniquement une mise plus petite**, sans aucune règle
supplémentaire à écrire. Une équipe à 6 matchs est environ 2,4 fois plus
incertaine qu'une équipe à 72 — et Kelly en tient compte tout seul.

Effet : un avantage de 4 % avec σ = 1 % conserve l'essentiel de sa mise ; le
même avantage avec σ = 4 % voit sa mise réduite à presque rien. **C'est
exactement le comportement souhaité.**

---

## 4. Pénalité de désaccord

Quand le modèle s'écarte fortement du marché, il a plus souvent tort que
raison : il lui manque une information que le marché possède.

```
écart = max( |Δsuprématie| / 0,60 , |Δtotal| / 0,90 )
pénalité = 1 / (1 + 2 · max(écart − 0,5 ; 0))
```

Appliquée directement à la fraction de Kelly. Un écart de suprématie de
0,6 but réduit la mise d'environ un tiers ; un écart de 1,2 but la divise
par trois.

---

## 5. Plusieurs paris simultanés

Trois problèmes distincts, trois traitements distincts.

### 5.1 Issues exclusives du même match

Traiter 1 et X du même match comme deux paris indépendants **sur-mise
systématiquement** : elles ne peuvent pas perdre ensemble. Utiliser le Kelly
multi-issues exact :

```python
f = fe.kelly_exclusive([p1, px, p2], [o1, ox, o2])
```

L'algorithme retient les issues dont l'espérance dépasse un taux de réserve
endogène, et calcule les mises optimales conjointes. Il gère aussi le cas
d'arbitrage.

### 5.2 Paris corrélés (même match, marchés différents)

« Domicile gagne » et « plus de 2,5 buts » sont corrélés positivement.
Les traiter séparément expose davantage que prévu.

- Décote de corrélation intra-groupe : `1 / (1 + 0,35 · (n − 1))` où `n` est
  le nombre de paris du groupe.
- Groupes définis par : même match > même championnat/journée > indépendant.

### 5.3 Paris indépendants simultanés

La somme des Kelly individuels dépasse l'optimum conjoint. Solution du
système : plafond d'exposition totale, avec mise à l'échelle proportionnelle.

| Contrainte | Valeur par défaut |
|---|---|
| Mise maximale par pari | 2 % de la banque |
| Exposition totale simultanée | 8 % (palier 1–2), 6 % (palier 3), 4 % (palier 4) |
| Exposition maximale sur un même match | 3 % |
| Exposition maximale sur une même journée de championnat | 5 % |

---

## 6. Enchaînement complet

L'ordre compte. Le moteur l'applique dans cet ordre exact :

```
1. Kelly brut                     f0 = (p·o − 1)/(o − 1)
2. Décote d'incertitude           p → p − z·σ
3. Fraction du palier             × 0,25 / 0,18 / 0,13
4. Pénalité de désaccord          × pénalité
5. Plafond par pari               min(·, 2 %)
6. Décote de corrélation          × 1/(1 + 0,35(n−1))
7. Plafond d'exposition totale    mise à l'échelle globale
8. Mise minimale                  en dessous → 0 (pas de mise symbolique)
```

```python
plan = fe.stake_plan(bets, bankroll=2000, kelly_fraction=0.18,
                     max_per_bet=0.02, max_total=0.06,
                     correlation_haircut=0.35, min_stake=2.0)
```

---

## 7. Définition et gestion de la banque

- **La banque est le capital dédié**, séparé du reste, dont la perte totale
  n'affecterait pas votre vie matérielle. Ni plus, ni moins.
- **Ne jamais la réalimenter pour compenser une perte.** Une réalimentation
  après drawdown transforme une gestion proportionnelle en martingale.
- **Réévaluer la taille de mise au maximum une fois par semaine**, pas après
  chaque pari : recalculer en continu sur une banque qui vient de chuter
  produit un effet de cliquet inutile.
- **Retraits** : possibles, mais ils réduisent la banque de référence. Les
  déclarer explicitement dans le journal.

### Paliers de réduction automatique

| Drawdown depuis le sommet | Action |
|---|---|
| −10 % | Aucune. C'est normal et attendu. |
| −20 % | Vérifier le CLV des 50 derniers paris. S'il est positif, continuer. |
| −25 % | Réduire la fraction de Kelly de moitié jusqu'au retour à −15 %. |
| −35 % | Arrêt des mises. Audit complet obligatoire avant reprise. |

Le drawdown seul n'est **pas** un signal d'échec : le tableau du §2 montre
qu'un système correct à 1/4 Kelly traverse couramment des baisses de 18 %.
Le signal d'échec, c'est **un drawdown accompagné d'un CLV négatif**.

---

## 8. Ce qui est interdit

| Pratique | Pourquoi |
|---|---|
| Augmenter la mise après une perte | Martingale déguisée ; ruine assurée |
| « Se refaire » sur le dernier match de la soirée | Décision prise sous contrainte, pas sur avantage |
| Miser un pourcentage fixe sans tenir compte de l'avantage | Ignore l'information ; sous-mise les bons paris et sur-mise les mauvais |
| Combiner des paris sans modéliser la corrélation | Espérance et variance toutes deux mal estimées |
| Miser sur un avantage sous le seuil « parce qu'il n'y a rien d'autre » | Le coût cumulé des petits paris négatifs dépasse le gain des bons |
| Suivre une mise après avoir vu la cote bouger contre soi sans re-tarifer | Le marché vous dit que vous avez tort |
| Utiliser la même banque pour plusieurs stratégies non corrélées suivies séparément | Exposition réelle non maîtrisée |

---

## 9. Cadre personnel

Le pari sportif comporte un risque réel de perte financière. Aucun système,
y compris celui-ci, ne l'élimine.

Signaux à prendre au sérieux, indépendamment des résultats : miser plus que
prévu, miser pour se refaire, dissimuler l'activité, y consacrer un temps
disproportionné, ressentir de la détresse après une perte.

En France : **Joueurs Info Service, 09 74 75 13 13** (appel non surtaxé,
7 j/7). Des dispositifs équivalents existent dans la plupart des pays.
