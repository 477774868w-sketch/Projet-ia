# 05 — DEUXIÈMES DIVISIONS ET FOOTBALL FÉMININ

C'est ici que se trouve l'essentiel de l'avantage accessible — et l'essentiel
du risque. Ces compétitions ne se traitent **pas** avec les réglages des
grands championnats.

---

## 1. Le compromis fondamental

| | Grands championnats | D2 / Féminin |
|---|---|---|
| Efficience du marché | Très élevée | Faible à moyenne |
| Marge de l'opérateur | 2 – 3 % | 5 – 12 % |
| Limites de mise | Élevées | Basses |
| Qualité des données | Excellente | Inégale |
| Volatilité des effectifs | Faible | Élevée |
| Erreur de modèle | Faible | Élevée |

**La conclusion contre-intuitive** : le marché est plus mou, mais votre modèle
l'est aussi. Les deux erreurs ne se compensent pas — elles s'additionnent dans
σ. C'est pourquoi les seuils d'avantage minimal sont **plus élevés** en D2 et
en féminin, alors que le marché y est plus faible.

> Avantage minimal : 2,5 % en palier 1 → **4,0 %** en palier 3 →
> **5,5 %** en palier 4. Fraction de Kelly : 0,25 → 0,18 → 0,13.

---

## 2. Deuxièmes divisions : ce qui change

### 2.1 Volatilité des effectifs

- **Prêts** : un club de D2 peut perdre trois titulaires au 31 janvier. Le
  modèle ajusté sur l'automne devient faux du jour au lendemain.
  → Demi-vie plus courte (**120 jours**) sur la seconde moitié de saison.
- **Rotation d'entraîneurs** : nettement plus fréquente qu'en D1. Un
  changement récent invalide partiellement l'historique.
  → Après un changement d'entraîneur : `w_marché` +0,15 pendant 5 journées.

### 2.2 Calendrier

Beaucoup de D2 jouent 38 à 42 journées, avec des séries de trois matchs en
huit jours. La fatigue y a un effet mesurable, amplifié par des effectifs
courts.
→ Appliquer le barème de rotation de `06_FACTEURS_CONTEXTUELS.md` §3 avec les
coefficients **majorés de 50 %** par rapport à la D1.

### 2.3 Motivation de fin de saison

C'est **le** facteur exploitable spécifique à la D2, et le marché le tarife
mal parce qu'il exige une simulation, pas une intuition.

Situations à identifier à partir de la journée 30 :
- équipe mathématiquement sauvée et hors course : baisse d'intensité réelle ;
- équipe en course pour les barrages contre une équipe sans enjeu ;
- équipe déjà promue avec un match de barrage à préparer.

Procédure obligatoire : lancer `/season` **avant** de juger. Une équipe que
l'intuition dit « sans enjeu » a souvent encore 12 % de chances de barrages.

```bash
python3 engine/footyedge.py season --model model_l2.json \
  --fixtures data/fixtures_l2.json --standings data/standings_l2.json \
  --sims 20000 --promo 2 --playoff 3 6 --releg 3
```

### 2.4 Le saut de niveau entre divisions

Pour les promus, les relégués et les matchs de coupe inter-divisions :

**La bonne méthode : ajuster les deux divisions ensemble.** Chargez un
historique contenant les deux divisions avec un champ `league`, et le moteur
estime des notes d'équipes **globales** plus un décalage de niveau de buts par
championnat (`02_MOTEUR_QUANTITATIF.md` §5 bis). Le promu conserve alors son
historique de D2, et l'écart entre divisions devient une sortie mesurée au
lieu d'un prior saisi à la main.

L'apport est mesurable :

Pyramide synthétique : 2 divisions × 14 équipes, 4 saisons, montées et descentes réelles (1456 matchs).

| Approche | Corrélation des notes avec la vérité, **toutes divisions confondues** |
|---|---|
| Un ajustement par championnat, notes concaténées | **0.720** |
| Ajustement conjoint, notes globales | **0.939** |

Deux ajustements séparés produisent deux échelles arbitraires : concaténer
leurs notes donne 0,72 de corrélation avec la vérité. L'ajustement conjoint
donne **0,94**. C'est toute la différence entre « je sais classer les équipes
de ma division » et « je sais tarifer un promu et un match de coupe ».

```bash
python3 engine/footyedge.py fit --csv data/history/france_d1_d2.csv --out fr.json
python3 engine/footyedge.py table --model fr.json     # niveau des 2 divisions
```

**Repli, si vous n'avez qu'une division.** Une équipe moyenne de D2 vaut
environ **−0,20 à −0,30 en log d'attaque** et **+0,20 à +0,30 en log de
faiblesse défensive** par rapport à une équipe moyenne de D1 du même pays,
soit une suprématie de **0,45 à 0,70 but** entre équipes moyennes des deux
divisions sur terrain neutre. L'écart est plus faible entre D2 et D3
(≈ 0,15 en log) et plus important dans les pays à forte concentration
financière.

Dans ce cas, conserver l'historique de D2 en appliquant la pénalité reste
nettement préférable à une remise à la moyenne — surtout sur les six premières
journées, où le marché lui-même est incertain.

### 2.5 Où se trouve la valeur en D2

Par ordre décroissant :
1. Probabilités de saison (montée, barrages, descente) — rarement retarifées.
2. Totaux par équipe et handicaps de mi-temps — dérivés naïvement.
3. Totaux du match sur les championnats à faible total (Ligue 2, Segunda,
   Brasileirão B) : les opérateurs y appliquent souvent des lignes de 2,5
   là où le prix juste est proche de 2,25.
4. 1X2 après composition officielle.

---

## 3. Football féminin : ce qui change

### 3.1 Dispersion des niveaux

C'est la différence structurelle numéro un. Dans plusieurs championnats
d'élite, un ou deux clubs concentrent l'essentiel des moyens. Les
suprématies de 2 à 3 buts sont courantes, là où elles sont exceptionnelles
en masculin.

Conséquences directes :
- Le **taux de nuls est nettement plus bas** : 14 % à 22 % contre 22 % à 30 %
  en masculin. Un modèle calibré sur du masculin sur-tarifie systématiquement
  le nul.
- Les marchés de **handicap élevé** (−2,5, −3,5) sont fréquents et mal
  tarifés.
- L'avantage du terrain est **plus faible** (0,15 – 0,25 but).

### 3.2 Le piège des grands écarts : la sur-dispersion

Sur les fortes disparités, la loi de Poisson sous-estime les queues. Une
équipe surclassée gagne « impossiblement » plus souvent que le modèle ne le
dit — carton rouge, gardienne inspirée, terrain lourd, absence de la
buteuse vedette.

Effet mesuré sur une affiche à λ = 3,40 − 0,55 :

| Marché | Poisson | Bin. nég. `shape=10` | Écart |
|---|---|---|---|
| Plus de 3,5 buts | 55.7% | 53.2% | -2.5 pt |
| Plus de 5,5 buts | 20.7% | 22.5% | +1.8 pt |
| Domicile marque 5 buts ou plus | 25.6% | 26.9% | +1.3 pt |
| Handicap -3,5 domicile | 34.8% | 34.8% | -0.0 pt |
| Nul | 7.8% | 9.7% | +1.8 pt |
| Extérieur gagne | 2.9% | 4.0% | +1.1 pt |
| Clean sheet domicile | 57.7% | 58.6% | +0.9 pt |

**Lecture.** La victoire de l'outsider passe de 2,9 % à 4,0 % : la cote juste
tombe de 34,5 à 25,0. Un opérateur qui affiche 26,0 est **cher** en Poisson et
**correct** en binomiale négative. Sur ce type de marché, le choix de la loi
n'est pas un raffinement, c'est la décision entière.

> Règle : dès qu'une suprématie dépasse **1,50 but**, activer `shape=10`
> (féminin) ou `shape=14` (D2 masculine). Ne jamais tarifer un handicap
> supérieur à ±2,5 en Poisson pur.

### 3.3 Taille des échantillons

Beaucoup de championnats féminins d'élite jouent 20 à 30 journées. Un modèle
ajusté sur une demi-saison dispose de 10 à 15 matchs par équipe.

- Demi-vie **plus longue** (270 à 365 jours) : il faut du signal, et les
  effectifs changent moins vite que le nombre de matchs ne le suggère.
  À confirmer par `tune` dès que vous avez deux saisons.
- Rétrécissement **plus fort** : `reg = 2,0`.
- Conserver les données de la saison précédente, avec une régression
  d'intersaison de 30 %.

### 3.4 Qualité des données

- Les modèles de **buts attendus** sont majoritairement calibrés sur du
  football masculin. Les profils de tir et de conversion diffèrent ;
  les valeurs xG en féminin sont moins fiables.
  → `xg_weight` réduit à **0,4** au maximum, ou `target="goals"`.
- Les **compositions** sont publiées plus tardivement et moins
  systématiquement. Une absence non annoncée est fréquente.
- Les **feuilles de match** de certains championnats ne sont pas toujours
  disponibles en temps réel.

### 3.5 Facteurs à fort effet, spécifiques

| Facteur | Effet | Ampleur typique |
|---------|-------|-----------------|
| Absence d'une joueuse cadre | Bien supérieur au masculin (effectifs plus courts) | jusqu'à −15 % sur λ |
| Trêve internationale | Déplacements longs, retours tardifs | −5 à −10 % sur λ |
| Double confrontation coupe d'Europe | Rotation massive en championnat | −10 à −20 % sur λ |
| Terrain et créneau | Terrains annexes, horaires atypiques | total −5 % |
| Fin de saison sans enjeu | Écarts plus marqués qu'en masculin | via `/season` |

### 3.6 Où se trouve la valeur en féminin

1. **Handicaps élevés et totaux d'équipe** sur les affiches déséquilibrées,
   avec la loi sur-dispersée.
2. **Totaux** : les opérateurs appliquent souvent des lignes calquées sur le
   masculin (2,5) alors que le prior est à 3,2 – 3,4.
3. **Marchés de mi-temps** sur les affiches déséquilibrées : la répartition
   des buts entre les mi-temps y est plus asymétrique.
4. **Pas le 1X2 des affiches serrées** : c'est là que votre erreur de modèle
   est maximale et l'avantage minimal.

---

## 4. Réglages recommandés — récapitulatif

| Paramètre | Grands championnats | D2 masculine | Féminin élite |
|-----------|---------------------|--------------|---------------|
| `half_life_days` | 180 | 120 – 180 | 270 – 365 |
| `reg` | 0,5 – 1,0 | 1,0 | 2,0 |
| `w_market` | 0,65 – 0,80 | 0,40 – 0,55 | 0,25 – 0,45 |
| `min_edge` | 2,5 % | 4,0 % | 5,5 % |
| `kelly_fraction` | 0,25 | 0,18 | 0,13 |
| `shape` | aucune | 14 si suprématie > 1,5 | 10 si suprématie > 1,5 |
| `xg_weight` | 0,6 | 0,5 | 0,4 max |
| Matchs minimum par équipe | 8 | 10 | 12 |

---

## 5. Contrôle avant de miser sur ces compétitions

- [ ] Le championnat est-il dans `league_priors.csv` ? Sinon, palier estimé
      par la marge observée.
- [ ] Ai-je au moins 10 matchs (D2) ou 12 (féminin) sur **chacune** des deux
      équipes ? L'écart-type sur log(λ) le dit sans compter :
      `model.lambda_uncertainty(dom, ext)` — au-delà de 0,25, s'abstenir.
- [ ] Les deux divisions sont-elles ajustées **ensemble** (champ `league`) ?
- [ ] Y a-t-il eu un mercato, un changement d'entraîneur ou une trêve
      internationale depuis la dernière donnée ?
- [ ] La composition est-elle connue ? Sinon, σ élargi et Kelly divisé par 2.
- [ ] Si la suprématie dépasse 1,5 but, la sur-dispersion est-elle activée ?
- [ ] Le prix vient-il d'un opérateur unique ? Alors ce n'est pas un marché :
      c'est un avis. Traiter en conséquence.
- [ ] En fin de saison : `/season` a-t-il été lancé avant de juger la
      motivation ?
