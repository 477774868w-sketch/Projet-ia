# AUDIT DU SYSTÈME

Rapport d'audit du dépôt FootyEdge 1.0.0.
**Rejouable à tout moment** : `python3 scripts/audit.py`

---

## 1. Résultat

| Suite | Contrôles | Résultat |
|---|---|---|
| Auto-test du moteur (`footyedge.py selftest`) | 246 | **246 / 246** |
| Suite de tests indépendante (`tests/test_footyedge.py`) | 95 | **95 / 95** |
| Audit du système (`scripts/audit.py`) | 107 | **107 / 107** |
| **Total** | **448** | **448 / 448** |

Durée : moteur ≈ 30 s · tests ≈ 60 s · audit ≈ 5 min. Aucune dépendance
externe : bibliothèque standard de Python uniquement.

---

## 2. Ce qui a été vérifié

### 2.1 Intégrité mathématique du moteur (246 contrôles)

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

### 2.2 Commandes de la ligne de commande (14 contrôles)

Les quatorze sous-commandes (`selftest`, `demo`, `devig`, `invert` en deux
variantes, `price`, `fit`, `table`, `predict`, `tune`, `calib`, `live`,
`season`, `backtest`) sont exécutées et leur sortie contrôlée sur le fond, pas
seulement sur le code de retour.

### 2.3 Conformité de la documentation au code (25 contrôles)

C'est le point le plus important de cet audit. **Toutes les tables chiffrées
des documents sont produites par le moteur** (`scripts/generate_tables.py`) et
l'audit les régénère puis vérifie qu'elles figurent telles quelles dans les
fichiers `sources/`. Une divergence entre le code et la documentation devient
donc une erreur détectable, pas un écart silencieux.

Douze tables sont ainsi vérifiées : conversion (total, suprématie) → 1X2,
totaux, BTTS, lignes de handicap équitables, comparaison des cinq méthodes de
retrait de marge, effet de la sur-dispersion sur les grands écarts, profils de
drawdown par fraction de Kelly, corrélations dans les combinés, réévaluation
en direct, ajustement conjoint contre ajustements séparés, décroissance de
l'incertitude d'estimation, et cas témoins de recalibration.

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

### 2.6 Ajustement conjoint, incertitude, réglage, prix (23 contrôles)

Les six capacités ajoutées après le premier audit sont contrôlées sur le fond,
pas seulement sur leur exécution :

- **Multi-championnats** : les notes restent comparables d'une division à
  l'autre (corrélation > 0,85 sur pyramide synthétique) ; le décalage de
  niveau de buts a le bon signe ; changer de division ne modifie **pas** la
  force relative de deux équipes ; et un seul championnat redonne exactement
  le modèle simple.
- **Incertitude d'estimation** : σ dans une plage plausible, décroissante avec
  les données, exactement proportionnelle à (1 − w) après fusion, et `None`
  — jamais une fausse certitude — sur un modèle rechargé depuis un JSON.
- **Recalibration** : la sur-confiance est détectée, la log-perte s'améliore,
  un modèle déjà calibré est laissé tranquille, un échantillon insuffisant
  renvoie l'identité, et la documentation porte bien l'arbitrage.
- **Comparaison des opérateurs** : meilleure cote et opérateur retenus,
  consensus obtenu par mise en commun de probabilités déviguées.
- **Seuil de bascule** : le déplacement calculé annule effectivement
  l'avantage (vérifié numériquement) et va dans le bon sens.
- **Réglage automatique** : `w = 1` redonne le RPS du marché à 0,002 près,
  la grille est triée, et le réglage refuse de fonctionner sans cotes.

### 2.7 Cohérence du dépôt (19 contrôles)

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

### 2.8 Chaîne complète (14 contrôles)

Ajustement sur 1 140 matchs → tarification d'un match à venir → détection de
valeur → plan de mise sous plafonds → fiche lisible → backtest à fenêtre
glissante → calibration → CLV → simulation de saison.

Résultats de ce scénario de référence (données synthétiques, 920 matchs
tarifés) : RPS modèle 0,2085 · marché 0,2074 · **fusion 0,2059** · ECE 0,0229.

---

## 3. Défauts trouvés et corrigés pendant la construction

L'audit a mis au jour **trois** défauts réels, tous dans le moteur.

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

**3. Incertitude du modèle non réduite par la fusion avec le marché.** Après
fusion, `log λ = (1−w)·log λ_modèle + w·log λ_marché` : seule la fraction
(1−w) porte l'incertitude d'estimation. Le moteur appliquait la variance
entière, ce qui gonflait σ d'un facteur 1/(1−w) — à `w = 0,55`, presque le
double — et faisait rejeter des paris valables par le critère `z`. Détecté
par le contrôle de bout en bout de cet audit, qui a cessé de détecter un prix
généreux après le passage à la σ de Fisher. Corrigé : à `w = 1` (marché pur)
l'incertitude du modèle disparaît, ce qui est exact.

Cinq défauts ont par ailleurs été trouvés **dans les tests eux-mêmes** :
une hypothèse fausse sur le Kelly exclusif (il mise davantage au total, pas
moins, car les issues se couvrent mutuellement) ; un point frontière réalisable
(Σf = 1) exclu à tort ; une confusion entre `overround` et `margin_pct` ; une
règle de trois linéaire supposée à tort sur-estimer les buts restants, alors
qu'elle les sous-estime à chaque minute ; et l'hypothèse que le rapport des
intensités serait conservé d'une division à l'autre, alors que l'avantage du
terrain propre au championnat le modifie exactement d'un facteur
exp(δ_A − δ_B).

Un **faux positif** mérite aussi d'être consigné : une première validation de
la méthode delta contre un bootstrap donnait un écart de 89 %, ce qui laissait
craindre une erreur grave. Le bootstrap était faux — il échantillonnait un
sous-bloc de la matrice de covariance en ignorant les corrélations croisées
qui se compensent. Refait sur la loi complète, l'accord est de ±1,1 %.

Ils sont documentés ici parce qu'ils illustrent le principal risque de ce genre
de système : **un test qui encode une intuition fausse est plus dangereux
qu'une absence de test**, et un contrôle qui échoue doit être suspecté avant le
code qu'il contrôle.

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

### 4.5 La recalibration n'est pas gratuite

Sur cas témoins, la recalibration fait exactement ce qu'on lui demande :
température 1,175 sur un modèle sur-confiant, 0,976 sur un modèle déjà
calibré, 0,923 sur un modèle sous-confiant, avec un ECE ramené à ~0 dans les
trois cas.

Mais appliquée à un modèle **déjà proche de la calibration**, elle améliore
l'ECE tout en dégradant légèrement la finesse : sur nos données synthétiques,
ECE 0,025 → 0,014 mais log-perte **dégradée** de 0,003 et RPS de 0,0004.
Aplatir les probabilités réduit la perte des cas mal classés et augmente celle
des cas bien classés.

Elle est donc **désactivée par défaut**. Ne l'activer que si l'ECE dépasse
0,04, et ne la conserver que si la log-perte hors échantillon s'améliore
aussi. Le backtest donne les deux chiffres ; la décision est mesurée, pas
dogmatique.

### 4.6 Le réglage automatique ne crée pas d'avantage

`tune` trouve la meilleure configuration **parmi celles qu'on lui propose**,
sur les données qu'on lui donne. Trois précautions :

- Une grille trop fine sur un historique court revient à sur-ajuster les
  hyperparamètres : préférer 3 à 4 valeurs par axe.
- Le RPS retenu est optimiste du fait même de la sélection. Pour une
  estimation honnête du gain, réserver une saison entière jamais utilisée
  pendant le réglage.
- Si le minimum est atteint en `w_marché = 1`, la conclusion n'est pas qu'il
  faut régler autrement : c'est que le modèle n'apporte rien sur ce
  championnat.

### 4.7 Ce que l'ajustement conjoint suppose

Les notes ne deviennent comparables entre divisions que s'il existe un
**chemin** entre elles dans les données : équipes qui montent ou descendent,
matchs de coupe. Sur deux championnats de pays différents sans aucune
rencontre commune, les échelles restent arbitraires — le modèle ne le signale
pas par une erreur, seulement par un `θ` mal déterminé. Vérifiez qu'un pont
existe avant de comparer deux championnats.

### 4.8 Performance

Python pur, un seul cœur. Le poste dominant est l'inversion du marché
(≈ 28 ms par match), pas l'ajustement du modèle. Un backtest de
1 520 matchs prend une trentaine de secondes. Suffisant pour un usage
quotidien ; à revoir pour un balayage systématique de dizaines de
championnats.

### 4.9 Ce que le système ne peut pas garantir

Il ne garantit ni rendement, ni avantage sur un marché donné, ni accès durable
à des limites de mise exploitables. Sa fonction la plus utile est de dire
« aucun pari retenu » — et il le dira souvent.

---

## 5. Recommandations, par ordre de priorité

1. **Charger deux à cinq saisons réelles**, toutes divisions d'un même pays
   dans le même fichier (colonne `Div` ou `league`), puis lancer `tune`. Lire
   le verdict et `rps_edge_vs_market` avant tout le reste.
2. **Recalibrer les priors** du championnat à partir de la sortie de `fit`
   (`mu`, `home_adv`, `rho`) et mettre à jour `league_priors.csv`.
3. **Laisser `tune` choisir** demi-vie, rétrécissement et poids du marché,
   puis vérifier la forme de la courbe : un minimum intérieur confirme que le
   modèle apporte de l'information.
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
| Moteur `engine/footyedge.py` | ≈ 4 000 lignes, 0 dépendance |
| Base de connaissances `sources/` | 14 documents, ≈ 3 200 lignes |
| Tests indépendants | 95 |
| Contrôles internes du moteur | 246 |
| Contrôles d'audit système | 107 |
| Priors de compétitions | 55 |
| Sous-commandes de la ligne de commande | 14 |
| Marchés tarifés depuis une seule grille | 16 familles |
| Tables de la documentation produites par le moteur | 12 |
| Modes de tarification | pré-match et en direct |
| Méthodes de retrait de marge | 5 |

---

*Le pari sportif comporte un risque réel de perte financière. Ce dépôt est un
outil d'analyse quantitative, pas un conseil en investissement.
En France : Joueurs Info Service, 09 74 75 13 13.*
