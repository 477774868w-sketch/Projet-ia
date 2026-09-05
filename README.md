# FootyEdge — système de pronostic football pour usage conversationnel

Système complet d'évaluation de probabilités et de valeur sur le football :
grands championnats, deuxièmes divisions (Ligue 2, LaLiga Hypermotion,
Serie B, 2. Bundesliga, Championship…) et football féminin.

Il est conçu pour être utilisé **en conversation avec une IA** : on dépose les
fichiers `sources/` comme connaissances d'un Projet, on colle les instructions,
et on discute. Le moteur de calcul fait le reste.

---

## Le principe : deux couches qui se renforcent

| Couche | Rôle | Fichiers |
|---|---|---|
| **Conversationnelle** | Protocole, jugement, garde-fous, format des réponses | `sources/` (14 documents) |
| **Calcul** | Probabilités exactes, retrait de marge, mise, backtest | `engine/footyedge.py` |

L'IA seule raconte ; le moteur seul ne juge pas. Ensemble, l'IA applique un
protocole strict et délègue chaque nombre à un calcul vérifiable.

**Le moteur n'a aucune dépendance externe** — stdlib Python uniquement. Il
tourne dans n'importe quel interpréteur, y compris l'outil d'exécution de code
d'un assistant. Aucune installation, aucun `pip`.

---

## Ce que fait le système

**Probabilités, pas pronostics.** Une seule distribution jointe des scores
engendre tous les marchés : 1X2, double chance, DNB, handicaps asiatiques
(lignes quarts comprises), totaux, totaux par équipe, BTTS, pair/impair,
multi-buts, marge de victoire, scores exacts, mi-temps et MT/FT. Aucun prix ne
peut en contredire un autre.

**Il lit le marché avant de le corriger.** Cinq méthodes de retrait de marge
(dont Shin), puis inversion des cotes — 1X2 ou lignes asiatiques — en
intensités de buts. On obtient l'avis du marché dans la même unité que le
modèle, et on peut alors tarifer les marchés dérivés que l'opérateur affiche
mal.

**Il sait ce qu'il ne sait pas.** Le moteur conserve l'information de Fisher
observée : l'incertitude d'estimation de chaque note est calculée, pas
devinée, puis propagée à la probabilité de chaque marché. Une équipe vue 6
fois est 2,4× plus incertaine qu'une équipe vue 72 fois — **et la mise
s'ajuste toute seule**, sans règle supplémentaire. S'y ajoutent la dispersion
inter-méthodes de devig et une pénalité automatique quand le modèle s'écarte
trop du marché.

**Il compare les divisions, pas seulement les équipes.** Chargez D1 et D2 dans
le même fichier : les notes deviennent globales, un promu garde son
historique, et un match de coupe entre divisions se tarifie. Sur une pyramide
synthétique, la corrélation avec la vérité passe de **0,72** (deux ajustements
séparés) à **0,94** (ajustement conjoint).

**Il règle ses propres paramètres.** `tune` balaie demi-vie × rétrécissement ×
poids du marché en validation temporelle et renvoie la configuration qui
minimise le RPS hors échantillon — au lieu de vous faire deviner.

**Il mise comme un gestionnaire de risque.** Kelly fractionnaire, variante
exacte pour les issues mutuellement exclusives (cas d'arbitrage compris),
décote de corrélation, plafonds par pari / par match / par journée / au total,
paliers de réduction en drawdown.

**Il se mesure, puis se corrige.** Backtest à fenêtre glissante sans fuite,
RPS comparé au marché, courbes de calibration et ECE, CLV, intervalles
bootstrap, taille d'échantillon requise, critères d'arrêt écrits à l'avance.
Et si la calibration est mauvaise, une recalibration (mise à l'échelle
vectorielle) ajustée **sur les seules prédictions passées** la corrige — le
rapport donne les métriques avant et après, pour que la décision soit mesurée.

**Il joue le meilleur prix.** Donnez plusieurs opérateurs par marché : le
moteur retient la meilleure cote, nomme l'opérateur et chiffre le gain par
rapport à la médiane. Et chaque pari retenu porte son **seuil de bascule** —
de combien le total du match doit bouger pour que l'avantage disparaisse.

**Il traite les compétitions négligées comme un sujet à part entière.** Les
deuxièmes divisions et le football féminin ont leurs propres réglages :
demi-vie, rétrécissement, sur-dispersion sur les grands écarts, seuils
d'avantage **plus élevés** malgré des marchés plus mous — parce que l'erreur
de modèle y est plus grande aussi.

---

## Mise en route (10 minutes)

Voir **[DEMARRAGE_RAPIDE.md](DEMARRAGE_RAPIDE.md)** pour la version détaillée.

### 1. Créer le Projet

1. Créez un Projet dans votre assistant.
2. Copiez le contenu de **`sources/00_INSTRUCTIONS_PROJET.md`** dans le champ
   *Instructions personnalisées*.
3. Déposez comme sources de connaissance : les **13 autres fichiers**
   `sources/`, plus `engine/footyedge.py` et `data/league_priors.csv`.

### 2. Vérifier le moteur

```bash
python3 engine/footyedge.py selftest     # 246 contrôles d'intégrité
python3 tests/test_footyedge.py          # 95 tests indépendants
python3 engine/footyedge.py demo         # démonstration guidée
```

### 3. Premier échange

> « /match Guingamp – Amiens, Ligue 2, samedi 20h.
>  Cotes opérateur R : 2,45 / 3,40 / 3,10. Plus/moins 2,5 : 1,98 / 1,92.
>  Absent côté Guingamp : le buteur n° 9, suspendu.
>  Banque 2 000 €. »

Le système applique les neuf phases, tarifie tous les marchés, compare, et
propose un plan de mise — ou vous explique pourquoi il n'y a rien à jouer.

---

## Usage direct du moteur

```bash
# Retirer la marge d'un jeu de cotes (5 méthodes comparées)
python3 engine/footyedge.py devig --odds 2.10 3.40 3.60

# Cotes -> intensités de buts -> tarif de tous les marchés dérivés
python3 engine/footyedge.py invert --ah -0.5 1.95 1.95 --ou 2.5 1.90 1.98

# Tarifer un match, fiche lisible
python3 engine/footyedge.py price --lh 1.55 --la 1.15 --market-1x2 2.20 3.40 3.30 \
    --offered data/offered_template.json --brief

# Ajuster un modèle (plusieurs divisions ensemble si la colonne league existe)
python3 engine/footyedge.py fit --csv data/history/france.csv --out model_fr.json
python3 engine/footyedge.py table --model model_fr.json    # niveau des divisions

# Régler demi-vie, rétrécissement et poids du marché par RPS hors échantillon
python3 engine/footyedge.py tune --csv data/history/ligue2.csv \
    --half-lives 90 150 240 360 --regs 0.5 1 2

# Tarifer un match du modèle
python3 engine/footyedge.py predict --model model_fr.json \
    --home Guingamp --away Amiens --market-1x2 2.45 3.30 3.10 --w 0.5 --brief

# Validation temporelle + simulation de mise
python3 engine/footyedge.py backtest --csv data/history/ligue2.csv \
    --min-train 300 --w 0.5 --calibrate --out audit.json --bets-out paris.csv

# Réévaluation en cours de match (63e minute, 1-0, rouge pour l'extérieur)
python3 engine/footyedge.py live --lh 1.60 --la 1.10 --minute 63 \
    --score 1 0 --red-away 1

# Audit du journal : CLV, calibration, ROI, segments, critères d'arrêt
python3 engine/footyedge.py calib --log data/journal.csv

# Probabilités de montée, barrages, descente
python3 engine/footyedge.py season --model model_l2.json \
    --fixtures data/fixtures_template.json --standings data/standings_template.json
```

---

## Structure du dépôt

```
sources/                      ← à déposer dans le Projet
  00_INSTRUCTIONS_PROJET.md   instructions à coller (le noyau)
  01_PROTOCOLE_OPERATOIRE.md  les neuf phases, pas à pas
  02_MOTEUR_QUANTITATIF.md    modèle, estimation, mode dégradé + tables
  03_MARCHE_DEVIG_CLV.md      microstructure, retrait de marge, CLV
  04_PRIORS_LIGUES.md         priors de 55 compétitions
  05_D2_ET_FEMININ.md         deuxièmes divisions et football féminin
  06_FACTEURS_CONTEXTUELS.md  barème d'ajustements plafonné
  07_STAKING_RISQUE.md        Kelly, portefeuille, drawdown
  08_CALIBRATION_AUDIT.md     métriques, seuils, critères d'arrêt
  09_MARCHES_FORMULES.md      dérivation de tous les marchés, corrélations
  10_CHECKLISTS_BIAIS.md      contrôles, signaux d'alerte, biais
  11_TEMPLATES_SORTIE.md      formats de réponse
  12_DONNEES_SOURCES.md       schémas CSV, qualité, cadence
  13_LEXIQUE.md               vocabulaire

engine/footyedge.py           moteur, zéro dépendance, ~4 000 lignes
engine/README.md              organisation du moteur, conventions, performances
tests/test_footyedge.py       95 tests indépendants
data/                         priors de 55 compétitions + modèles de fichiers
scripts/generate_priors.py    régénère data/league_priors.csv
scripts/generate_tables.py    régénère les tables chiffrées de sources/
scripts/audit.py              audit complet du dépôt (107 contrôles)
AUDIT.md                      rapport d'audit, limites, recommandations
```

## Vérifier l'ensemble

```bash
python3 scripts/audit.py
```

448 contrôles au total : intégrité mathématique du moteur, fonctionnement de
toutes les commandes, **conformité des tables de la documentation au code**,
exactitude des affirmations chiffrées, renvois entre fichiers, validité des
données, et un scénario complet de bout en bout.

Les tables chiffrées des documents `sources/` sont produites par le moteur et
revérifiées par l'audit : une divergence entre le code et la documentation est
une erreur détectable, pas un écart silencieux.

---

## Ce que ce système ne fait pas

- **Il ne promet aucun rendement.** Il produit des probabilités et une
  discipline. Le reste dépend de vos données, de votre accès au marché et de
  votre régularité.
- **Il ne remplace pas les données.** Sans historique et sans cotes, il ne
  peut que raisonner sur des priors — et il vous le dira.
- **Il ne collecte rien automatiquement.** La collecte reste à votre charge,
  dans le respect des conditions d'utilisation des sources.
- **Il ne garantit pas de battre le marché sur les grands championnats.** Le
  système est explicitement conçu pour vous dire quand il n'a pas d'avantage —
  c'est sa fonction la plus utile.

Le pari sportif comporte un risque réel de perte financière. Ce dépôt est un
outil d'analyse quantitative, pas un conseil en investissement.
En France : **Joueurs Info Service, 09 74 75 13 13**.
