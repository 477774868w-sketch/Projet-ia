# 03 — MARCHÉ, RETRAIT DE MARGE, CLV

Le marché n'est pas l'adversaire : c'est la meilleure source d'information
disponible gratuitement. Le battre suppose d'abord de savoir **le lire**.

---

## 1. Anatomie d'une cote

Une cote affichée contient trois choses :

```
cote affichée  =  probabilité réelle  +  marge de l'opérateur  +  biais de position
```

- **Marge** (*overround*, *vig*) : `Σ(1/cote) − 1`. Sur du 1X2 : 2 à 3 % chez
  les opérateurs les plus serrés, 5 à 8 % chez les généralistes, 10 %+ sur les
  marchés exotiques et le football féminin de second rang.
- **Biais de position** : l'opérateur déplace la ligne pour équilibrer son
  exposition. Sur les gros événements, c'est marginal ; sur une D2 le jour où
  un influenceur a poussé un pari, c'est massif.

**Conséquence pratique.** Une cote brute n'est jamais comparable à votre
probabilité. Il faut d'abord retirer la marge.

---

## 2. Retirer la marge : cinq méthodes

| Méthode | Hypothèse | Défaut |
|---------|-----------|--------|
| **Multiplicatif** | Marge proportionnelle à la probabilité | Surestime les outsiders |
| **Additif** | Marge répartie à parts égales | Peut produire des probabilités négatives |
| **Puissance** | `Σ q_i^k = 1` | Bon compromis empirique, sans fondement théorique |
| **Odds-ratio** | Transformation du rapport de cotes | Proche de Shin, plus simple |
| **Shin** | La marge rémunère le risque de parieurs informés | Référence sur 2–3 issues |

**Le choix compte-t-il ?** Oui, et de façon très inégale :

**Match équilibré, marge serrée** — cotes 2.60 / 3.30 / 2.80, marge **4.29 %**

| Méthode | P(1) | P(X) | P(2) | Cote juste 1 | Cote juste 2 |
|---|---|---|---|---|---|
| Multiplicatif | 36.81% | 29.00% | 34.18% | 2.716 | 2.925 |
| Additif | 36.97% | 28.81% | 34.22% | 2.705 | 2.922 |
| Puissance | 36.96% | 28.83% | 34.21% | 2.706 | 2.923 |
| Odds-ratio | 36.89% | 28.91% | 34.20% | 2.711 | 2.924 |
| **Shin** | 36.93% | 28.86% | 34.21% | 2.708 | 2.923 |

Écart max entre méthodes : **0.19 point de %** (z de Shin = 0.0224)

**Gros favori (biais maximal)** — cotes 1.18 / 7.50 / 15.00, marge **4.53 %**

| Méthode | P(1) | P(X) | P(2) | Cote juste 1 | Cote juste 2 |
|---|---|---|---|---|---|
| Multiplicatif | 80.91% | 12.73% | 6.36% | 1.236 | 15.712 |
| Additif | 83.16% | 11.75% | 5.08% | 1.202 | 19.667 |
| Puissance | 83.54% | 11.19% | 5.27% | 1.197 | 18.976 |
| Odds-ratio | 82.61% | 11.63% | 5.76% | 1.210 | 17.368 |
| **Shin** | 82.59% | 11.97% | 5.44% | 1.211 | 18.386 |

Écart max entre méthodes : **2.63 point de %** (z de Shin = 0.0250)

**Marché mou, marge 9 %** — cotes 2.30 / 3.30 / 3.05, marge **6.16 %**

| Méthode | P(1) | P(X) | P(2) | Cote juste 1 | Cote juste 2 |
|---|---|---|---|---|---|
| Multiplicatif | 40.80% | 28.44% | 30.77% | 2.451 | 3.250 |
| Additif | 41.29% | 28.11% | 30.60% | 2.422 | 3.268 |
| Puissance | 41.28% | 28.13% | 30.59% | 2.422 | 3.269 |
| Odds-ratio | 41.08% | 28.27% | 30.66% | 2.434 | 3.262 |
| **Shin** | 41.16% | 28.20% | 30.64% | 2.429 | 3.264 |

Écart max entre méthodes : **0.49 point de %** (z de Shin = 0.0329)

**Lecture décisive.** Sur un match équilibré, les cinq méthodes donnent le
même résultat à 0,2 point près : le choix n'a aucune importance. Sur un gros
favori, l'écart atteint **2,6 points de pourcentage** — soit davantage que
l'avantage typique d'un pari. Sur ce type de match, la méthode de devig n'est
pas un détail technique, **c'est la décision**.

Règle du système : Shin par défaut sur 2 et 3 issues ; puissance au-delà ;
et **la dispersion inter-méthodes entre directement dans σ** (`devig_spread`).
Quand les méthodes ne s'accordent pas, on mise moins.

---

## 3. Le biais favori / outsider

Les grosses cotes sont systématiquement trop courtes : les parieurs paient une
prime pour la possibilité d'un gain élevé, et l'opérateur charge sa marge à
cet endroit. L'effet est mesurable et robuste sur des décennies.

Conséquences opérationnelles :

- Un « avantage » détecté sur une cote > 8,0 est le plus souvent un artefact
  de devig multiplicatif. Recalculer avec Shin avant toute conclusion.
- Symétriquement, les favoris courts (< 1,35) sont souvent **légèrement**
  sous-évalués, mais le rendement par unité de risque y est faible et le
  drawdown en cas de série noire, brutal.
- La zone la plus saine pour un modèle est **1,60 – 4,50**.

---

## 4. Hiérarchie des sources de prix

| Rang | Type | Rôle dans le système |
|------|------|----------------------|
| 1 | **Bourses d'échange** (Betfair, Smarkets, Matchbook) — prix après commission | Vérité de marché ; ancrage préféré si liquidité suffisante |
| 2 | **Opérateurs à faible marge et hautes limites** (type Pinnacle) | Ancrage nominal ; leur clôture est la référence de CLV |
| 3 | **Marchés asiatiques** (handicap + total, hautes limites) | Meilleure information sur suprématie et total |
| 4 | **Généralistes / opérateurs de détail** | Là où se trouve la valeur, pas l'information |
| 5 | **Agrégateurs de cotes** | Repérage, jamais ancrage |

**Principe directeur.** On *s'informe* au rang 1–3, on *parie* au rang 4.
Utiliser un opérateur de détail comme ancrage est l'erreur méthodologique la
plus fréquente : on finit par mesurer sa propre marge.

**Liquidité minimale.** Sur une bourse d'échange, un prix soutenu par moins de
quelques centaines d'euros de volume n'est pas une information de marché.
Vérifier la profondeur avant d'ancrer.

---

## 5. La Closing Line Value (CLV)

**Définition.** Écart entre la cote obtenue et la cote de clôture débarrassée
de sa marge, sur le même pari.

```
CLV = cote_prise / cote_de_clôture_déviguée − 1
```

**Pourquoi c'est le juge de paix.** La cote de clôture est la prévision la
plus précise qui existe sur un événement sportif : elle agrège tout l'argent
informé jusqu'au coup d'envoi. Battre la clôture régulièrement est la seule
preuve, à court terme, que votre processus contient de l'information.

**Vitesse de convergence.** Pour établir un avantage de 3 % à 95 % de
confiance :

| Indicateur | Nombre de paris nécessaires |
|------------|-----------------------------|
| ROI | ≈ 1 000 – 2 000 |
| CLV | ≈ 100 – 200 |

Un ordre de grandeur : le CLV converge **environ dix fois plus vite** parce
qu'il élimine la variance du résultat sportif. C'est la raison pour laquelle
il est l'indicateur numéro un du système.

**Barème d'interprétation** (sur ≥ 100 paris, clôture d'un opérateur à faible
marge) :

| CLV moyen | Diagnostic |
|-----------|------------|
| > +2,0 % | Avantage réel et exploitable |
| +0,5 à +2,0 % | Avantage probable, marge de sécurité faible |
| −0,5 à +0,5 % | Aucun avantage démontré — vous payez la marge |
| < −0,5 % | Vous êtes du mauvais côté ; arrêter et diagnostiquer |

**Piège.** Un CLV positif obtenu uniquement sur des cotes prises très tôt
(J−5) peut refléter la seule volatilité du prix, pas de l'information.
Séparez toujours le CLV par **fenêtre temporelle de prise**.

---

## 6. Quand parier

| Fenêtre | Avantage | Inconvénient | Palier adapté |
|---------|----------|--------------|---------------|
| J−5 à J−2 | Cotes les plus larges, marché non formé | Compositions inconnues, risque de nouvelle | 3–4 (marchés mous) |
| J−1 | Bon compromis | — | 2–3 |
| H−2 à H−1 | Compositions officielles connues | Marché déjà ajusté, limites basses | 1–2 |
| H−0 | Prix le plus juste | Aucune valeur résiduelle | jamais |

**Règle du système.** Plus le marché est efficient, plus il faut parier tard
(l'information des compositions est votre seul avantage possible). Plus il est
mou, plus il faut parier tôt (le prix se corrige à mesure que les opérateurs
se copient).

**Compositions officielles.** Elles tombent généralement une heure avant le
coup d'envoi. C'est le moment de plus forte asymétrie d'information sur les
championnats peu suivis : les opérateurs de détail mettent parfois plusieurs
minutes à ajuster.

---

## 7. Lire un mouvement de ligne

| Observation | Interprétation la plus probable |
|-------------|--------------------------------|
| Dérive chez l'opérateur de référence, suivie par les autres | Argent informé — respecter |
| Dérive chez les généralistes, référence immobile | Argent public — souvent une opportunité inverse |
| Total qui baisse fortement sans nouvelle | Météo, terrain, ou absence offensive |
| Handicap qui bouge, total figé | Information sur une équipe, pas sur le match |
| Ouverture très tardive, marge élevée | L'opérateur ne sait pas tarifer — méfiance et opportunité |

**À ne pas faire.** Suivre un mouvement de ligne *après* qu'il a eu lieu :
l'information est déjà dans le prix, et vous prenez la cote du perdant. Le
mouvement s'utilise pour **valider ou invalider** votre propre analyse, pas
comme signal autonome.

---

## 8. Où se trouve réellement la valeur

Classement par avantage résiduel accessible, du plus au moins favorable :

1. **Marchés dérivés sur championnats peu suivis** — totaux par équipe,
   handicaps de mi-temps, marges de victoire en D2 et en féminin. L'opérateur
   les dérive d'un modèle sommaire de son marché principal ; votre grille est
   plus fine que la sienne.
2. **Totaux et handicaps de mi-temps** — souvent obtenus par une règle de
   trois naïve à partir du temps plein.
3. **Marchés de saison** (montée, descente, barrages) — rarement retarifés,
   très sensibles à la simulation Monte-Carlo.
4. **1X2 après composition officielle** sur championnats de palier 3–4.
5. **1X2 des grands championnats** — le plus dur. N'y aller qu'avec un
   avantage mesuré et un CLV historique positif.

---

## 9. Comparer les opérateurs, correctement

Un professionnel ne joue jamais une cote moyenne : il joue **la meilleure
disponible**. Le moteur accepte donc, pour chaque marché, un dictionnaire
`{opérateur: cote}` au lieu d'un nombre :

```python
offered = {"1x2": {"home": {"BookA": 2.42, "BookB": 2.55, "BookC": 2.38},
                   "draw": 3.40, "away": 3.10}}
```

Il retient la meilleure, indique l'opérateur, et calcule le **gain de
comparaison** par rapport à la cote médiane. Sur l'exemple ci-dessus,
2,55 contre une médiane de 2,42 : +5,4 % de cote, soit environ 5 points
d'espérance ajoutés sans rien changer au modèle. Comparer les prix est le
seul avantage disponible sans aucune compétence de modélisation — et c'est
souvent le plus gros.

**Deux lectures de la dispersion entre opérateurs :**

| Observation | Interprétation |
|---|---|
| Écart modéré, meilleur prix chez un opérateur de détail | Opportunité normale, jouer |
| Un opérateur très au-dessus de tous les autres | Erreur de saisie ou information manquante — vérifier avant de miser |
| Dispersion qui s'effondre à l'approche du coup d'envoi | Le marché converge : votre fenêtre se referme |

**Consensus, jamais moyenne de cotes.** Pour agréger plusieurs opérateurs de
référence, il faut déviguer **chacun séparément**, puis mettre en commun les
probabilités :

```python
c = fe.consensus_probs([[2.10, 3.40, 3.60], [2.05, 3.50, 3.70]])
c["probs"]        # pooling log-lineaire des probabilites deviguees
c["max_spread"]   # desaccord entre operateurs -> entre dans sigma
```

Moyenner les **cotes brutes** serait une faute : la marge de chaque opérateur
se retrouverait dans le résultat, et l'agrégat serait plus cher que chacune
de ses composantes.

---

## 10. Contraintes de compte

Factuel, sans stratégie de contournement :

- Les opérateurs de détail limitent les comptes rentables : c'est une réalité
  structurelle à intégrer dans le dimensionnement, pas un obstacle à
  contourner.
- Les opérateurs à faible marge et les bourses d'échange acceptent des mises
  élevées mais offrent moins de valeur : c'est le compromis normal.
- Conséquence sur le système : **la taille de banque exploitable est bornée
  par l'accès au marché**, pas par le modèle. Dimensionnez vos objectifs en
  conséquence, et mesurez votre performance en % de banque, jamais en euros.
- Respectez les conditions générales des opérateurs et le cadre légal de votre
  juridiction.
