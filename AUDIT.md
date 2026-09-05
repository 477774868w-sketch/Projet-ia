# AUDIT DU SYSTÈME

Rapport d'audit du dépôt FootyEdge 1.0.0.
**Rejouable à tout moment** : `python3 scripts/audit.py`

---

## 1. Résultat

| Suite | Contrôles | Résultat |
|---|---|---|
| Auto-test du moteur (`footyedge.py selftest`) | 218 | **218 / 218** |
| Suite de tests indépendante (`tests/test_footyedge.py`) | 69 | **69 / 69** |
| Audit du système (`scripts/audit.py`) | 79 | **79 / 79** |
| **Total** | **366** | **366 / 366** |

Durée : moteur 7 s · tests 7 s · audit ≈ 60 s. Aucune dépendance externe.

---

## 2. Ce qui a été vérifié

### 2.1 Intégrité mathématique du moteur (218 contrôles)

- La grille de scores est une distribution de probabilité pour toute
  combinaison d'intensités et de ρ, y compris aux valeurs extrêmes
  (λ = 0,01 ; λ = 9,0) et pour un ρ absurde, automatiquement borné.
- Sans correction Dixon-Coles, les marginales redonnent exactement les
  intensités, et le total suit exactement une loi de Poisson.
- **Cohérence des deux camps d'un handicap asiatique**, vérifiée sur quinze
  lignes : `gain_dom = perte_ext`, remboursements égaux, et
  `1/cote_juste_dom + 1/cote_juste_ext = 1` à 10⁻⁹ près.
- Les lignes quarts valent exactement la moyenne des deux demi-lignes.
- Les cinq méthodes de retrait de marge produisent des distributions valides,
  préservent l'ordre des issues, et Shin escompte davantage les grosses cotes
  que la normalisation multiplicative.
- L'inversion du marché fait un aller-retour exact : partir d'intensités,
  produire un 1X2 ou des lignes asiatiques, réinverser, retrouver les mêmes
  intensités à 10⁻⁶ près.
- Le Kelly multi-issues exclusives est vérifié **numériquement optimal** :
  aucune perturbation de ±0,001 à ±0,05 n'améliore la croissance
  logarithmique, sur trois jeux de paramètres, cas d'arbitrage compris.
- L'estimateur des forces d'équipe est **consistant** : la corrélation avec la
  vérité terrain synthétique passe de 0,865 (2 saisons) à 0,967 (8 saisons).
- Le backtest ne fuit pas : le modèle est réajusté à chaque date sur les
  seules données antérieures, colonnes de cotes pré-match et de clôture
  strictement séparées.

### 2.2 Commandes de la ligne de commande (13 contrôles)

Les treize sous-commandes (`selftest`, `demo`, `devig`, `invert` en deux
variantes, `price`, `fit`, `table`, `predict`, `calib`, `live`, `season`,
`backtest`) sont exécutées et leur sortie contrôlée sur le fond, pas seulement
sur le code de retour.

### 2.3 Conformité de la documentation au code (22 contrôles)

C'est le point le plus important de cet audit. **Toutes les tables chiffrées
des documents sont produites par le moteur** (`scripts/generate_tables.py`) et
l'audit les régénère puis vérifie qu'elles figurent telles quelles dans les
fichiers `sources/`. Une divergence entre le code et la documentation devient
donc une erreur détectable, pas un écart silencieux.

Sont ainsi vérifiées : la table de conversion (total, suprématie) → 1X2, la
table des totaux, la table BTTS, la table des lignes de handicap équitables,
la comparaison des cinq méthodes de retrait de marge, l'effet de la
sur-dispersion sur les grands écarts, les profils de drawdown par fraction de
Kelly, et les effets de corrélation sur les combinés.

Les affirmations numériques du texte sont vérifiées séparément :
marge de 4,59 % et intensités 1,41 − 1,00 du guide de démarrage · formules
fermées du mode dégradé (plus de 2,5 buts, BTTS, clean sheet) · cote juste de
l'outsider passant de 34,5 à 25,0 sous sur-dispersion · sous-estimation de
61 % du combiné « nul + moins de 2,5 buts » · écart de 2,6 points entre
méthodes de devig sur un gros favori.

### 2.4 Réévaluation en direct (5 contrôles)

La part de buts restante dépasse la part de temps restante à chaque minute ;
au coup d'envoi sur 0-0 la grille en direct redonne exactement la grille
pré-match ; aucun score final inférieur au score déjà acquis ne reçoit de
probabilité ; la distribution somme à 1 ; et la documentation porte bien la
restriction d'usage.

### 2.5 Audit du journal de paris (5 contrôles)

Les seuils codés dans le moteur (bandes de CLV, bandes d'ECE) sont comparés au
barème écrit dans `sources/08_CALIBRATION_AUDIT.md` : le code et la doctrine ne
peuvent pas diverger. Le modèle de journal livré est effectivement lisible, et
les critères d'arrêt se déclenchent bien sur un journal à CLV négatif.

### 2.6 Cohérence du dépôt (19 contrôles)

- Les 14 documents `sources/` sont présents ; aucun renvoi croisé ne pointe
  vers un fichier inexistant ; toutes les fonctions citées dans la
  documentation existent réellement dans le moteur.
- `league_priors.csv` : les 55 lignes sont **recalculées par le moteur** et
  comparées ; les réglages sont homogènes à l'intérieur de chaque palier ;
  le seuil d'avantage croît et la fraction de Kelly décroît bien avec le
  palier d'efficience.
- Le modèle de journal sépare les champs de décision des champs de résultat.
- Enfin, l'audit vérifie **ses propres chiffres** : les nombres de tests
  annoncés dans `AUDIT.md` et `README.md` sont comparés à ceux réellement
  mesurés, les sous-sections de ce rapport doivent être numérotées à la suite,
  et leurs effectifs doivent redonner le total de l'audit. Un compteur périmé
  dans la documentation est un échec d'audit.

### 2.7 Chaîne complète (13 contrôles)

Ajustement sur 1 140 matchs → tarification d'un match à venir → détection de
valeur → plan de mise sous plafonds → fiche lisible → backtest à fenêtre
glissante → calibration → CLV → simulation de saison.

Résultats de ce scénario de référence (données synthétiques, 920 matchs
tarifés) : RPS modèle 0,2085 · marché 0,2074 · **fusion 0,2059** · ECE 0,0229.

---

## 3. Défauts trouvés et corrigés pendant la construction

L'audit a mis au jour deux défauts réels, tous deux dans le moteur.

**1. Handicap asiatique — mauvais seuil côté extérieur.** Le camp extérieur
était évalué au seuil `line` au lieu de `−line`. Sur une ligne −0,5, le prix
extérieur sortait à 0,738 au lieu de 0,510 : les deux camps ne formaient plus
un marché cohérent, sans que rien ne le signale. Détecté par le test
d'invariant `gain_dom = perte_ext`. Corrigé, puis couvert par quinze lignes de
test au lieu d'une.

**2. Kelly multi-issues — cas d'arbitrage non traité.** Lorsque la somme des
inverses de cotes est inférieure à 1, l'algorithme de Smoczynski-Tomkins
dégénère (taux de réserve nul) et renvoyait une allocation nettement
sous-optimale. Détecté par un test d'optimalité numérique, pas par un test de
valeur attendue — un test qui aurait simplement comparé à une valeur codée en
dur n'aurait rien vu. Corrigé par le traitement explicite du cas exhaustif.

Trois défauts ont par ailleurs été trouvés **dans les tests eux-mêmes** :
une hypothèse fausse sur le Kelly exclusif (il mise davantage au total, pas
moins, car les issues se couvrent mutuellement), un point frontière réalisable
(Σf = 1) exclu à tort, et une confusion entre `overround` et `margin_pct` dans
le script d'audit. Ils sont documentés ici parce qu'ils illustrent le principal
risque de ce genre de système : **un test qui encode une intuition fausse est
plus dangereux qu'une absence de test.**

---

## 4. Limites — à lire avant de miser

### 4.1 La validation est synthétique, pas empirique

**C'est la limite principale.** Aucune donnée historique réelle n'a été
utilisée : cet environnement n'y a pas accès. Tout ce qui a été vérifié
concerne la **machinerie** — exactitude des formules, absence de fuite,
consistance de l'estimateur, respect des plafonds. Rien ne démontre que ce
système dégage un avantage sur un marché réel.

De plus, le marché synthétique est construit comme « vérité + bruit ». La
conséquence est instructive et doit être comprise :

| Configuration | Gain de RPS de la fusion sur le marché |
|---|---|
| 20 équipes, 4 saisons, bruit de marché 0,16 | **+0,0022** |
| 20 équipes, 4 saisons, bruit 0,11 | +0,0008 |
| 18 équipes, 3 saisons, bruit 0,11 | **−0,0009** (le marché gagne) |

Autrement dit : le modèle bat le marché synthétique uniquement quand son
erreur d'estimation est inférieure au bruit du marché. C'est exactement la
question réelle — et elle ne se tranche que sur **vos** données, avec le
backtest. Le système fournit l'instrument de mesure et le critère d'arrêt
(`sources/08_CALIBRATION_AUDIT.md` §6) ; il ne fournit pas la réponse.

**Première chose à faire avec de vraies données** : lancer le backtest et lire
`rps_edge_vs_market`. S'il est négatif, ne pas parier le 1X2 — le système est
conçu pour vous le dire.

### 4.2 Les priors sont saisis à la main

`data/league_priors.csv` contient des **ordres de grandeur pluriannuels**
saisis manuellement pour le couple (total, suprématie) de 55 compétitions.
Les colonnes 1X2, plus de 2,5 buts et BTTS en sont déduites par le moteur —
elles sont donc cohérentes avec lui, mais elles ne sont pas des comptages
historiques. Ils ne doivent jamais être cités comme des statistiques, et
doivent être remplacés par vos propres estimations dès que possible.

### 4.3 Les barèmes sont raisonnés, pas ajustés

Les coefficients d'ajustement contextuel (absences, repos, météo, altitude,
motivation) de `sources/06` sont des valeurs par défaut plausibles et
plafonnées, **pas des coefficients estimés sur données**. Leur principale
vertu est de discipliner le jugement, pas d'être exacts. Il en va de même des
paliers `w_marché`, avantage minimal et fraction de Kelly : ce sont des choix
de conception à recalibrer.

La part de buts en première mi-temps (0,455) est également un prior.

### 4.4 Périmètre du modèle

Ne sont **pas** couverts : les cartons et corners (lois différentes, modèle
dédié nécessaire), les buteurs (méthode approchée seulement, `sources/09` §6),
la collecte automatique de données.

Le **jeu en direct** (`live_grid`, `sources/09` §8) est couvert, mais de façon
délibérément sommaire : temps restant non linéaire, cartons rouges et effet du
score sont des priors d'ordre de grandeur, pas des coefficients estimés. Le
modèle ne voit que (minute, score, cartons) là où un trader voit le match.
Cette fonction sert à **encadrer** un prix affiché, jamais à le remplacer, et
la documentation impose Kelly divisé par deux sur tout pari en direct.

La correction Dixon-Coles traite la dépendance des scores bas ; elle ne traite
ni les cartons rouges, ni les effets de style de jeu spécifiques à une
confrontation.

### 4.5 Performance

Python pur, un seul cœur. Le poste dominant est l'inversion du marché
(≈ 28 ms par match), pas l'ajustement du modèle. Un backtest de
1 520 matchs prend une trentaine de secondes. Suffisant pour un usage
quotidien ; à revoir pour un balayage systématique de dizaines de
championnats.

### 4.6 Ce que le système ne peut pas garantir

Il ne garantit ni rendement, ni avantage sur un marché donné, ni accès durable
à des limites de mise exploitables. Sa fonction la plus utile est de dire
« aucun pari retenu » — et il le dira souvent.

---

## 5. Recommandations, par ordre de priorité

1. **Charger deux à cinq saisons réelles** du championnat visé et lancer
   `backtest`. Lire `rps_edge_vs_market` avant tout le reste.
2. **Recalibrer les priors** du championnat à partir de la sortie de `fit`
   (`mu`, `home_adv`, `rho`) et mettre à jour `league_priors.csv`.
3. **Choisir la demi-vie par backtest**, pas à l'intuition : tester
   90 / 120 / 180 / 270 et retenir le minimum du RPS hors échantillon.
4. **Tenir le journal dès le premier pari.** Sans journal, aucun audit — donc
   aucun système.
5. **Commencer en simulation** sur 100 à 200 paris, et ne passer en réel que
   si le CLV est positif.
6. **Démarrer sur les paliers 2 et 3** (Championship, Serie B, Ligue 2,
   Segunda) : marchés assez liquides pour ancrer, assez mous pour laisser un
   avantage. Le palier 4 (féminin, divisions inférieures) demande davantage de
   discipline pour un gain plus incertain.
7. **Réexécuter `scripts/audit.py` après toute modification** du moteur ou de
   la documentation.

---

## 6. Inventaire

| Élément | Volume |
|---|---|
| Moteur `engine/footyedge.py` | ≈ 2 700 lignes, 0 dépendance |
| Base de connaissances `sources/` | 14 documents, ≈ 2 800 lignes |
| Tests indépendants | 69 |
| Contrôles internes du moteur | 218 |
| Contrôles d'audit système | 79 |
| Priors de compétitions | 55 |
| Marchés tarifés depuis une seule grille | 16 familles |
| Modes de tarification | pré-match et en direct |
| Méthodes de retrait de marge | 5 |

---

*Le pari sportif comporte un risque réel de perte financière. Ce dépôt est un
outil d'analyse quantitative, pas un conseil en investissement.
En France : Joueurs Info Service, 09 74 75 13 13.*
