# 12 — DONNÉES : SOURCES, SCHÉMAS, QUALITÉ

Le modèle vaut ce que valent ses données. Cette page décrit ce qu'il faut
collecter, sous quelle forme, et comment vérifier que c'est exploitable.

---

## 1. Ce dont le système a besoin

| Priorité | Donnée | Usage | Sans elle |
|---|---|---|---|
| Indispensable | Date, équipes, score final | Ajustement du modèle | Rien ne fonctionne |
| Indispensable | Championnat / division | Priors, séparation des ajustements | Mélange de niveaux |
| Très utile | Cotes pré-match (1X2 ou asiatiques) | Ancrage, fusion, backtest | `w_marché` = 0 forcé |
| Très utile | Cotes de clôture | CLV — l'indicateur n° 1 | Aucune mesure d'avantage à court terme |
| Utile | xG domicile / extérieur | Convergence plus rapide des notes | Notes plus bruitées |
| Utile | Saison | Régression d'intersaison | Notes trop persistantes |
| Contextuel | Terrain neutre | Avantage du terrain correct | Biais sur les coupes |
| Contextuel | Compositions, absences | Ajustements de phase 3 | Ajustements impossibles |

**Volume minimal utilisable :** 2 saisons complètes du championnat visé.
**Confort :** 4 à 5 saisons. **Au-delà de 8 saisons**, les données anciennes ne
pèsent presque plus rien avec une demi-vie de 180 jours — inutile de les
charger.

> **Le conseil qui change le plus de choses : un seul fichier par pays,
> toutes divisions confondues.** Avec une colonne `Div` (ou `league`), le
> moteur ajuste les divisions **ensemble** et produit des notes comparables
> entre elles : un promu garde son historique, un match de coupe entre
> divisions se tarifie, et l'écart de niveau devient une sortie mesurée
> (`02_MOTEUR_QUANTITATIF.md` §5 bis). Sur une pyramide synthétique, la
> corrélation avec la vérité passe de 0,72 à 0,94.
>
> Condition : il doit exister un **chemin** entre les divisions — montées,
> descentes ou matchs de coupe. Sans lien, les échelles restent arbitraires.

---

## 2. Schéma CSV attendu

Le chargeur accepte **deux conventions** et détecte automatiquement les
colonnes.

### 2.1 Convention « football-data » (largement diffusée)

```
Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,PSH,PSD,PSA,PSCH,PSCD,PSCA
E0,12/08/2024,Arsenal,Wolves,2,0,1.45,4.60,7.20,1.42,4.75,7.50
```

Reconnu automatiquement : `Div`, `Date` (jj/mm/aaaa), `HomeTeam`, `AwayTeam`,
`FTHG`, `FTAG`, cotes `PSH/PSD/PSA` (pré-match) et `PSCH/PSCD/PSCA`
(clôture), avec repli sur `B365*` puis `Avg*`.

### 2.2 Convention générique

```
date,home,away,hg,ag,league,season,hxg,axg,odds_h,odds_d,odds_a,close_h,close_d,close_a,neutral
2024-08-12,Arsenal,Wolves,2,0,E0,2024-25,2.31,0.64,1.45,4.60,7.20,1.42,4.75,7.50,0
```

Les alias complets sont dans `COLUMN_ALIASES` (moteur, §13). Modèle vierge :
`data/matches_template.csv`.

```python
matches = fe.load_matches_csv("data/history/ligue2.csv")
```

---

## 3. Types de sources

| Type | Contenu | Remarques |
|---|---|---|
| Archives de résultats et cotes historiques | Scores + cotes de plusieurs opérateurs, par championnat et saison, en CSV | Le socle du backtest. `football-data.co.uk` est la référence gratuite historique pour l'Europe |
| Fédérations et ligues officielles | Calendriers, classements, feuilles de match | Source de vérité pour les noms d'équipes et les compositions |
| Fournisseurs de données statistiques | xG, tirs, possession, événements | Qualité variable ; vérifier la couverture réelle des D2 et du féminin |
| Agrégateurs de cotes | Cotes en direct multi-opérateurs | Repérage et relevé de clôture |
| Bourses d'échange | Prix et volumes | Meilleure vérité de marché quand la liquidité suffit |
| API d'opérateurs | Cotes en direct | Vérifier les conditions d'utilisation avant tout usage automatisé |

**Avertissements :**
- Respecter les conditions d'utilisation et le cadre légal de chaque source.
  Un aspirateur agressif fait bannir l'adresse et fausse la collecte.
- Ne **jamais mélanger deux fournisseurs de xG** dans un même historique :
  les écarts systématiques entre modèles créent une fausse tendance.
- La couverture du **football féminin** et des **divisions inférieures** est
  très inégale. Vérifier l'absence de trous avant d'ajuster : un trou de trois
  journées fausse la pondération temporelle.

---

## 4. Qualité : sept contrôles avant tout ajustement

```python
matches = fe.load_matches_csv("data/history/ligue2.csv")
print(len(matches), matches[0]["date"], matches[-1]["date"])
```

1. **Continuité temporelle** — aucun trou de plus de 45 jours hors trêve
   estivale. Un trou = données manquantes, pas une pause.
2. **Nombre de matchs par équipe** — cohérent avec le format du championnat.
   Une équipe à 31 matchs quand les autres en ont 38 signale une perte de
   lignes ou un renommage.
3. **Noms d'équipes** — voir §5. Le problème n° 1 en pratique.
4. **Scores aberrants** — au-delà de 8 buts pour une équipe, vérifier
   manuellement (forfait, erreur de saisie, match arrêté).
5. **Cotes** — toutes strictement supérieures à 1,01 ; marge entre 1 % et
   15 %. Hors de cette plage, la ligne est inexploitable.
6. **Doublons** — même date et mêmes équipes : supprimer.
7. **Cohérence des priors** — la moyenne de buts du fichier doit être proche
   du prior du championnat. Un écart de plus de 0,3 but signale un mélange de
   compétitions **non étiqueté** : avec une colonne `league` correcte, le
   mélange est voulu et le moteur le gère ; sans elle, il fausse tout.
8. **Ponts entre divisions** — si vous ajustez plusieurs divisions ensemble,
   vérifier qu'au moins quelques équipes changent de division sur la période,
   ou que des matchs de coupe les relient. Sans pont, `θ` est arbitraire.

---

## 5. Noms d'équipes : la difficulté sous-estimée

Un même club apparaît sous plusieurs graphies selon les sources. Chaque
variante non résolue crée une **équipe fantôme** sans historique, à laquelle
le modèle attribue la moyenne du championnat — donc un prix faux, sans aucune
alerte.

Cas classiques : « Paris SG » / « PSG » / « Paris Saint-Germain » ·
« Man United » / « Manchester Utd » · « Bayern Munich » / « Bayern München » ·
accents, tirets, suffixes « FC », « AS », « 1. ».

**Procédure :**
1. Après chargement, lister les équipes et leur nombre de matchs :
   ```python
   from collections import Counter
   c = Counter([m["home"] for m in matches] + [m["away"] for m in matches])
   for t, n in sorted(c.items()): print("%-30s %d" % (t, n))
   ```
2. Toute équipe au compte anormalement bas est suspecte.
3. Tenir un fichier de correspondance et l'appliquer **avant** l'ajustement.
4. Vérifier la table des forces : une équipe inconnue apparaît avec une note
   proche de 0 et un `eff_weight` faible.

**Pièges spécifiques :** équipes réserves (« B », « II », « U23 ») à ne jamais
confondre avec l'équipe première ; sections masculine et féminine du même club
homonymes ; clubs ayant changé de nom ou fusionné en cours d'historique.

---

## 6. Cadence de mise à jour

| Fréquence | Action |
|---|---|
| Après chaque journée | Ajouter les résultats, relever les cotes de clôture |
| Hebdomadaire | Réajuster le modèle (`/fit`) |
| Mensuelle | Vérifier que les hyperparamètres tiennent (`/tune` sur la fenêtre récente) |
| Mensuelle | Contrôles qualité §4, revue des noms d'équipes |
| Mercato d'hiver | Réduire la demi-vie, réexaminer les équipes les plus touchées |
| Intersaison | Refit complet, régression des notes, révision des priors et des paliers |

---

## 7. Organisation des fichiers

```
data/
  history/               # historiques (hors dépôt Git)
    france.csv           # D1 + D2 dans le MEME fichier, colonne Div
    angleterre.csv       # idem : Premier League + Championship + League One
    feminin_europe.csv   # ...
  live/                  # relevés de cotes de la journée
  league_priors.csv      # priors par championnat (versionné)
  matches_template.csv   # schéma vierge
  bets_log_template.csv  # schéma du journal de paris
  fixtures_template.json # calendrier restant pour /season
  standings_template.json# classement actuel pour /season
```

`data/history/` et `data/live/` sont exclus du dépôt : ces fichiers sont
volumineux et souvent soumis à des conditions de redistribution. Le journal de
paris est **personnel** : ne le publiez pas.
