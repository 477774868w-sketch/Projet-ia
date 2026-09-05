# 11 — MODÈLES DE SORTIE

Formats de réponse standard. Ils garantissent que rien d'essentiel n'est omis
et rendent les analyses comparables entre elles.

---

## 1. `/match` — évaluation d'une rencontre

```
══════════════════════════════════════════════════════════════════
Guingamp — Amiens          Ligue 2 · J24 · sam. 20:00 · Roudourou
══════════════════════════════════════════════════════════════════
DONNÉES
  Modèle      [CALCULÉ]  ajusté le 12/03 sur 418 matchs, demi-vie 150 j
  Marché      [FOURNI]   Opérateur R, relevé à 14:32
  Compositions [INCONNU]  publication attendue 19:00
  Absences    [FOURNI]   Guingamp : n° 9 suspendu (source club, 11/03)

INTENSITÉS
  modèle    1,42 − 1,08    total 2,50   suprématie +0,34
  ajusté    1,29 − 1,08    total 2,37   suprématie +0,21   (×0,91 absence)
  marché    1,35 − 1,01    total 2,36   suprématie +0,34
  RETENU    1,32 − 1,04    total 2,36   suprématie +0,28   [w_marché 0,50]
  écarts    suprématie −0,13 · total +0,01 → accord raisonnable

PRIX JUSTES
  1X2       1 42,1 % (2,38)   X 28,4 % (3,52)   2 29,5 % (3,39)
  O/U 2,5   over 41,3 % (2,42)   under 58,7 % (1,70)
  BTTS      oui 46,8 % (2,14)   non 53,2 % (1,88)
  AH −0,25  dom 50,2 % (1,99)   ext 49,8 % (2,01)
  Scores    1-1 12,4 %  1-0 11,8 %  0-0 9,6 %  2-1 8,2 %  0-1 8,1 %
  Entropie  1,56 bits (match très incertain)

CONFRONTATION
  pari                    cote   juste     edge      z   opérateur
  O/U 2,5 under           1,80    1,70   +5,66%   2,31   BookB (+2,3% vs médiane)  ← retenu
  1X2 domicile            2,45    2,38   +3,15%   1,12   BookA                     ← retenu
  BTTS non                1,85    1,88   −1,60%  −0,58
  1X2 extérieur           3,20    3,39   −5,60%  −1,94

SEUIL DE BASCULE (ce qui annule l'avantage)
  O/U 2,5 under    s'annule si le total du match monte de 0,21 but
  1X2 domicile     s'annule si le total du match baisse de 0,14 but

PLAN DE MISE — banque 2 000 €, Kelly ×0,18
  O/U 2,5 under                       24,60 €   (1,23 %)
  1X2 domicile                        11,20 €   (0,56 %)
  exposition totale 1,79 %   ·   croissance log attendue +0,081 %

CE QUI INVALIDERAIT L'ANALYSE
  1. Composition : si le n° 10 est également absent, la suprématie tombe
     sous +0,10 et le pari 1X2 disparaît.
  2. Si la cote « under » descend sous 1,72, l'avantage est consommé.
  3. Pluie forte annoncée : renforcerait le pari « under », ne l'invalide pas.

JOURNAL
  2026-03-14,FRA2,Guingamp-Amiens,OU2.5,under,1.80,OpérateurR,0.587,0.556,
  0.0566,0.019,0.0123,24.60,2000,0.50,"×0.91 absence n°9",""
══════════════════════════════════════════════════════════════════
```

**Obligatoire dans toute sortie `/match` :** le bloc DONNÉES avec les
étiquettes, les trois lignes d'intensités, le drapeau d'écart, les quatre
nombres par pari, l'exposition totale, l'invalidation, la ligne de journal.

**Le seuil de bascule** répond de façon chiffrée à l'exigence d'invalidation :
il indique de combien les intensités doivent bouger pour que l'avantage
disparaisse. « Ce pari meurt si le total baisse de 0,14 but » est vérifiable ;
« s'ils ne sont pas dans un bon jour » ne l'est pas. Quand plusieurs
opérateurs sont fournis, la colonne indique lequel offre le meilleur prix et
combien cela rapporte par rapport à la médiane.

---

## 2. `/slate` — journée complète

```
LIGUE 2 · JOURNÉE 24 · 10 matchs analysés
Paramètres : w_marché 0,50 · avantage min. 4,0 % · Kelly ×0,18 · banque 2 000 €

RETENUS (3)
  #  match                     pari              cote  juste   edge     z   mise
  1  Guingamp–Amiens           under 2,5         1,80   1,70  +5,7%  2,31  24,60
  2  Bastia–Grenoble           AH +0,25 Bastia   1,95   1,82  +7,1%  1,84  19,40
  3  Laval–Pau                 domicile          2,60   2,42  +7,4%  1,41  12,80

exposition totale 2,84 % · croissance log attendue +0,17 %
aucun pari corrélé : les 3 matchs sont indépendants

ÉCARTÉS (7)  — motif principal
  Rodez–Annecy         avantage 2,1 % < seuil 4,0 %
  Caen–Metz            z = 0,6 (incertitude trop forte)
  Clermont–Red Star    composition inconnue, écart modèle/marché 0,7 but
  Ajaccio–Dunkerque    marge de l'opérateur 9,4 %, ancrage non fiable
  Paris FC–Troyes      aucun avantage sur les 14 marchés examinés
  Martigues–Lorient    équipe promue, moins de 10 matchs exploitables
  Guingamp B–…         compétition hors périmètre

CONTRÔLE : exposition journée 2,84 % < plafond 5 % ✓
```

Le bloc **ÉCARTÉS** est aussi important que le bloc **RETENUS** : il prouve
que la sélection résulte d'un critère et non d'une recherche de paris.

---

## 3. `/audit`

```
AUDIT — 214 paris · 12/09/2025 → 04/03/2026

INTÉGRITÉ
  lignes complètes 214/214 · clôtures renseignées 209/214 (97,7 %)
  modifications rétroactives détectées : 0

CLV  (indicateur n° 1)
  global            +1,84 %   (n=209)   IC95 [+0,71 % ; +2,95 %]
  taux battu-clôture  61,2 %
  par fenêtre : J−3 +0,4 % (n=48) · J−1 +1,7 % (n=96) · H−1 +3,1 % (n=65)
  par palier  : P2 +2,4 % (n=71) · P3 +1,9 % (n=102) · P4 −0,3 % (n=36)
  → le palier 4 ne produit pas de CLV : suspendre en attendant 100 paris de plus

CALIBRATION
  ECE 0,031  (correct)
  défaut : bac 0,60–0,70 → observé 0,545 sur 38 paris (sur-confiance modérée)

PRÉVISION
  RPS  modèle 0,2094 · marché 0,2071 · fusion 0,2038
  gain de la fusion sur le marché : +0,0033  ✓

RÉSULTAT
  ROI +3,1 % · IC95 [−2,4 % ; +8,7 %] · t = 1,12  → NON SIGNIFICATIF
  banque ×1,09 · drawdown max 11,4 %
  ROI attendu par le modèle : +4,2 % → l'écart est du bruit, pas une dérive

MISE
  aucun dépassement de plafond · exposition max atteinte 4,1 % (plafond 6 %)

DÉCISION
  Continuer paliers 2 et 3, réglages inchangés.
  Suspendre le palier 4 jusqu'à 100 paris supplémentaires en simulation.
  Corriger la sur-confiance : `reg` 1,0 → 1,4 au prochain ajustement.
  Prochain audit à 400 lignes.
```

---

## 4. `/postmortem`

Trois questions, dans cet ordre. **Le résultat n'apparaît qu'en dernier.**

```
1. L'INFORMATION  — que savais-je, qu'aurais-je pu savoir ?
   Connu : cotes, forme, absence du n° 9.
   Accessible et non consulté : la composition officielle (publiée 19:00,
   pari passé à 18:40). → erreur de processus, corrigeable.
   Inaccessible : l'état de la pelouse.

2. LA DÉCISION — referais-je ce pari avec la même information ?
   Oui. Avantage 5,7 %, z 2,3, mise conforme, tous les contrôles passés.

3. LE RÉSULTAT — 2-2, pari perdu.
   Sans lien avec la qualité de la décision. CLV +2,1 % : la clôture est
   descendue à 1,76, donc le marché a confirmé l'analyse.

CONCLUSION : bonne décision, mauvais résultat. Aucun changement de règle.
Une seule correction de processus : attendre systématiquement la composition
officielle sur les paris de type « under ».
```

---

## 5. Règles de forme

- Français, phrases courtes, pas de superlatif ni de vocabulaire commercial.
- Probabilités à une décimale, cotes à deux, mises à deux.
- Toute donnée porte son étiquette : `[FOURNI]` `[PRIOR]` `[CALCULÉ]`
  `[ESTIMÉ]` `[INCONNU]`.
- Aucun pari sans les quatre nombres (probabilité, cote juste, avantage, mise).
- « Aucun pari retenu » est une sortie complète et légitime : elle liste tout
  de même les prix justes et les motifs d'écartement.
- Le mode dégradé (sans exécution de code) est annoncé en tête de réponse.
