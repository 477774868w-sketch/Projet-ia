# DÉMARRAGE RAPIDE — 10 minutes

---

## Étape 1 — Vérifier le moteur (1 min)

```bash
python3 engine/footyedge.py selftest
```

Attendu : `Resultat : 218/218 tests reussis`. Aucune installation nécessaire :
le moteur n'utilise que la bibliothèque standard de Python 3.8+.

```bash
python3 engine/footyedge.py demo
```

---

## Étape 2 — Créer le Projet (3 min)

1. **Créer un Projet** dans votre assistant.

2. **Instructions personnalisées** : copier-coller l'intégralité de
   `sources/00_INSTRUCTIONS_PROJET.md`.

3. **Sources de connaissance** : déposer ces 15 fichiers.

   | Fichier | Pourquoi |
   |---|---|
   | `sources/01` → `sources/13` (13 fichiers) | Protocole, mathématiques, barèmes, formats |
   | `engine/footyedge.py` | Le moteur, que l'assistant peut exécuter |
   | `data/league_priors.csv` | Priors de 55 compétitions |

4. **Test de bon fonctionnement** — poser exactement :

   > « /aide — puis déviguise 2,10 / 3,40 / 3,60 et donne-moi les intensités
   > de buts implicites. »

   Réponse correcte attendue : marge ≈ 4,6 %, probabilités Shin ≈ 45,9 % /
   27,9 % / 26,3 %, intensités ≈ 1,41 − 1,00. Si les chiffres diffèrent
   nettement, les sources n'ont pas été prises en compte.

---

## Étape 3 — Première analyse (2 min)

Sans historique, avec les seules cotes :

> « /match Guingamp – Amiens, Ligue 2, samedi 20h.
>  Cotes opérateur R : 2,45 / 3,40 / 3,10 · Plus/moins 2,5 : 1,98 / 1,92 ·
>  BTTS : 1,85 / 1,95.
>  Absent côté Guingamp : le buteur n° 9 (suspendu, source club).
>  Banque 2 000 €. »

Ce que vous devez recevoir : le bloc DONNÉES étiqueté, trois lignes
d'intensités (modèle / marché / retenu), les prix justes de tous les marchés,
un tableau de confrontation avec avantage et `z`, un plan de mise chiffré, et
2 à 4 éléments qui invalideraient l'analyse.

**Si le système répond « aucun pari retenu », c'est un bon signe** : cela
signifie qu'il applique ses seuils au lieu de fabriquer de la valeur.

---

## Étape 4 — Ajouter vos données (4 min)

C'est ici que le système passe de « lecteur de marché » à « modèle ».

### 4.1 Constituer l'historique

Format attendu : `data/matches_template.csv`, ou un export au format
`Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,PSH,PSD,PSA,PSCH,PSCD,PSCA`
(reconnu automatiquement). Voir `sources/12_DONNEES_SOURCES.md` §3.

Minimum : 2 saisons du championnat visé. Confort : 4 à 5.

```bash
mkdir -p data/history
# deposer par exemple data/history/ligue2.csv
```

### 4.2 Ajuster le modèle

```bash
python3 engine/footyedge.py fit --csv data/history/ligue2.csv \
    --out model_l2.json --half-life 180 --reg 1.0 --top 20
```

Contrôler la sortie avec `sources/02_MOTEUR_QUANTITATIF.md` §9 :
`home_adv` entre 0,15 et 0,30 · `rho` entre −0,15 et 0 · étendue des notes
inférieure à 2,0. Hors de ces plages, il y a un problème de données.

### 4.3 Valider avant de miser

```bash
python3 engine/footyedge.py backtest --csv data/history/ligue2.csv \
    --min-train 300 --refit 21 --w 0.5 --min-edge 0.04 \
    --out audit_l2.json --bets-out paris_l2.csv
```

**La seule ligne qui compte d'abord :** `rps_edge_vs_market`.

| Valeur | Décision |
|---|---|
| > +0,003 | Le modèle apporte de l'information. Continuer. |
| 0 à +0,003 | Marginal. Augmenter `w_marché`, ne parier que les dérivés. |
| < 0 | Le modèle n'améliore pas le marché. **Ne pas parier le 1X2.** |

Ne regarder le ROI qu'après. Sur moins de 1 000 paris, il n'est pas
informatif — voir `sources/08_CALIBRATION_AUDIT.md` §5.

### 4.4 Utiliser le modèle en conversation

Déposez `model_l2.json` comme source du Projet, puis :

> « /match Guingamp – Amiens avec model_l2.json, cotes 2,45 / 3,40 / 3,10,
> `w_marché` 0,50, banque 2 000 €. »

---

## Réglages par type de compétition

| | Grands championnats | D2 masculine | Féminin élite |
|---|---|---|---|
| `half_life_days` | 180 | 120 – 180 | 270 – 365 |
| `reg` | 0,5 – 1,0 | 1,0 | 2,0 |
| `w_market` | 0,65 – 0,80 | 0,40 – 0,55 | 0,25 – 0,45 |
| Avantage minimal | 2,5 % | 4,0 % | 5,5 % |
| Fraction de Kelly | 0,25 | 0,18 | 0,13 |
| Sur-dispersion | aucune | `shape=14` si suprématie > 1,5 | `shape=10` si suprématie > 1,5 |

Détails et justifications : `sources/05_D2_ET_FEMININ.md`.

---

## Routine hebdomadaire

| Quand | Quoi |
|---|---|
| Lundi | Saisir résultats et cotes de clôture · réajuster (`/fit`) |
| Jeudi | `/slate` sur la journée à venir |
| J−0, H−1 | Réévaluer après compositions officielles, puis miser |
| Après la journée | Compléter le journal (CLV, résultats) |
| Toutes les 50 lignes | `/calib` (`footyedge.py calib --log …`) |
| Toutes les 200 lignes | `/audit` + décision écrite |

---

## Les cinq erreurs à ne pas commettre

1. **Comparer une cote brute à une probabilité.** Toujours retirer la marge
   d'abord.
2. **Miser avant d'avoir mesuré.** Faire tourner le backtest avant le premier
   euro.
3. **Ignorer le journal.** Sans journal, aucun audit — donc aucun système.
4. **Juger sur trois mois de ROI.** C'est du bruit. Regarder le CLV.
5. **Forcer un pari.** « Aucun pari retenu » est la réponse la plus fréquente
   d'un système correct.

---

## Où trouver quoi

| Question | Fichier |
|---|---|
| Comment l'IA doit se comporter | `sources/00` |
| Que faire, dans quel ordre | `sources/01` |
| Les mathématiques | `sources/02` |
| Comment lire le marché | `sources/03` |
| Chiffres de référence par championnat | `sources/04` + `data/league_priors.csv` |
| Ligue 2, Serie B, féminin | `sources/05` |
| Blessures, calendrier, météo, motivation | `sources/06` |
| Combien miser | `sources/07` |
| Est-ce que ça marche ? | `sources/08` |
| Formules d'un marché précis | `sources/09` |
| Listes de contrôle | `sources/10` |
| Format des réponses | `sources/11` |
| Données et fichiers | `sources/12` |
| Vocabulaire | `sources/13` |
| État de santé du système | `AUDIT.md` |
