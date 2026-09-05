# 06 — FACTEURS CONTEXTUELS : BARÈME D'AJUSTEMENT

Cette page transforme l'information qualitative en multiplicateurs chiffrés.
Sans barème, l'ajustement contextuel devient un prétexte à justifier un pari
déjà décidé. Avec barème, c'est un outil.

---

## 1. Trois règles d'usage

1. **On ajuste `λ_modèle`, jamais `λ_marché`.** Le marché intègre déjà
   l'information publique. L'appliquer aux deux revient à compter deux fois.
2. **Plafonds absolus.** Produit de tous les ajustements borné à
   **[0,80 ; 1,25]** par équipe. Au-delà, ce n'est plus un ajustement : c'est
   un autre match, qu'il faut modéliser autrement ou ne pas jouer.
3. **Trois facteurs au maximum.** Au-delà, le bruit domine le signal. Retenir
   les trois plus importants et ignorer le reste.

Test de discipline, à s'appliquer avant chaque ajustement :

> *Aurais-je appliqué le même coefficient, du même signe, si le pari qui en
> découle allait dans l'autre sens ?* Si la réponse est non, l'ajustement est
> une rationalisation. On l'abandonne.

---

## 2. Absences

L'unité est le **multiplicateur sur l'intensité concernée** : `λ_attaque` de
l'équipe pour un joueur offensif, `λ_encaissé` pour un défenseur ou un gardien.

| Profil du joueur absent | Effet sur λ_attaque | Effet sur λ_encaissé |
|---|---|---|
| Attaquant décisif majeur (≥ 35 % des buts de l'équipe) | ×0,88 – 0,92 | — |
| Meneur / créateur principal | ×0,90 – 0,94 | — |
| Attaquant titulaire ordinaire | ×0,96 – 0,98 | — |
| Défenseur central titulaire cadre | — | ×1,04 – 1,08 |
| Gardien titulaire de haut niveau | — | ×1,06 – 1,12 |
| Latéral / milieu défensif titulaire | ×0,98 | ×1,02 – 1,04 |
| Remplaçant, rotation normale | ×1,00 | ×1,00 |

**Cumul.** Deux absences majeures ne se multiplient pas naïvement : un
effectif s'adapte. Appliquer le facteur le plus fort, puis **la moitié** de
l'écart à 1 pour chaque absence suivante.

*Exemple.* Absences du buteur (×0,90) et du meneur (×0,92) →
`0,90 × (1 − 0,08/2) = 0,90 × 0,96 = 0,864`.

**Majorations de contexte :**
- Football féminin et D2 : effectifs plus courts → effets **majorés de 50 %**
  (le buteur majeur passe à ×0,85).
- Grand club au banc profond : effets **réduits de moitié**.

**Le piège du gardien.** L'écart entre un gardien d'élite et son remplaçant se
situe autour de 0,08 à 0,12 but encaissé par match. C'est réel, mais très
inférieur à ce que la presse suggère, et c'est **presque toujours déjà dans la
cote** dès que l'information est publique.

---

## 3. Calendrier, rotation, fatigue

Compter en **jours de repos** depuis le dernier match compétitif.

| Jours de repos | Multiplicateur sur λ_attaque | Sur λ_encaissé |
|---|---|---|
| ≤ 2 | ×0,94 | ×1,04 |
| 3 | ×0,97 | ×1,02 |
| 4 – 5 | ×0,99 | ×1,01 |
| 6 – 8 | ×1,00 (référence) | ×1,00 |
| 9 – 14 | ×1,00 | ×1,00 |
| > 21 (reprise, trêve longue) | ×0,97 | ×1,02 |

**Correctifs cumulatifs :**
- Troisième match en huit jours : multiplier l'effet par 1,5.
- D2 et féminin (effectifs courts) : multiplier l'effet par 1,5.
- Match de coupe d'Europe à J−3 pour un club engagé : rotation attendue,
  ×0,92 sur λ_attaque **si** le match suivant est perçu comme prioritaire.

**Ce qui compte réellement**, ce n'est pas la fatigue : c'est la **rotation
anticipée**. Un entraîneur qui prévoit de faire tourner produit un effet bien
supérieur à la fatigue elle-même. Chercher les déclarations d'avant-match.

---

## 4. Déplacement, altitude, fuseaux horaires

| Situation | Effet |
|---|---|
| Déplacement national < 300 km | Nul (déjà dans l'avantage du terrain) |
| Déplacement > 1 000 km, même pays | λ_attaque ×0,98 |
| Vol international, retour à J−3 | λ_attaque ×0,96, λ_encaissé ×1,03 |
| Décalage ≥ 5 fuseaux, moins de 4 jours | λ_attaque ×0,94, λ_encaissé ×1,05 |
| Altitude > 2 000 m pour une équipe non habituée | λ_attaque ×0,90, λ_encaissé ×1,08 |
| Trêve internationale, nombreux internationaux lointains | λ_attaque ×0,96 |

L'altitude est le facteur physique le mieux documenté et le plus important.
En Amérique du Sud, il est en grande partie **déjà** dans l'avantage du
terrain du championnat — vérifier avant d'ajouter.

---

## 5. Météo et terrain

Ces facteurs agissent sur le **total**, pas sur la suprématie.

| Condition | Effet sur le total |
|---|---|
| Vent fort (> 40 km/h) | ×0,92 – 0,95 |
| Pluie forte, terrain lourd | ×0,95 – 0,98 |
| Chaleur > 32 °C | ×0,93 – 0,96 (rythme réduit) |
| Neige, terrain gelé | ×0,90 – 0,95 |
| Pelouse synthétique | ×1,00 – 1,03 |
| Conditions normales | ×1,00 |

**Erreur fréquente.** Surestimer l'effet de la pluie. Une pluie ordinaire n'a
pas d'effet mesurable ; seul le terrain réellement détrempé ou le vent violent
comptent. Vérifier la prévision **à l'heure du coup d'envoi**, pas celle de
la journée.

---

## 6. Arbitre

Effet réel mais faible sur le total de buts, réel et fort sur les marchés de
cartons et de penalties.

| Marché | Utiliser l'arbitre ? |
|---|---|
| Total de buts, 1X2, handicaps | Non — l'effet est sous le bruit |
| Cartons, corners | Oui — les écarts entre arbitres sont importants et persistants |
| Penalty accordé | Oui, avec prudence |

Si le profil de l'arbitre est utilisé, il faut **au moins 30 matchs** de
données sur lui pour que la tendance soit distinguable du hasard.

---

## 7. Enjeu et motivation

Facteur à fort effet, mais **il ne s'estime pas à l'intuition**. Procédure
obligatoire :

1. Lancer `/season` avec le classement et le calendrier restant.
2. Lire les probabilités de titre, montée, barrages, descente de chaque
   équipe.
3. Appliquer le barème ci-dessous à partir de ces probabilités.

| Situation (issue de la simulation) | Effet |
|---|---|
| Toutes les positions d'enjeu < 3 % et > 97 % (rien à jouer) | λ_attaque ×0,97, λ_encaissé ×1,03 |
| Enjeu vital (descente entre 15 % et 60 %) | λ_encaissé ×0,97, total ×0,96 |
| Barrages ou montée en jeu, dernière ligne droite | ×1,00 (l'intensité ne change pas, la prudence oui) |
| Match précédant une finale ou un barrage décisif | Rotation attendue : λ_attaque ×0,92 |
| Équipe déjà championne, journées restantes | λ_attaque ×0,95, λ_encaissé ×1,05 |

**Ne jamais** appliquer un ajustement de motivation sans avoir lancé la
simulation. « Cette équipe n'a plus rien à jouer » est faux dans la majorité
des cas où on l'affirme.

---

## 8. Changement d'entraîneur

| Depuis le changement | Traitement |
|---|---|
| 1 à 3 matchs | `w_marché` +0,15 ; aucun ajustement directionnel |
| 4 à 8 matchs | `w_marché` +0,08 ; demi-vie réduite à 90 jours |
| > 8 matchs | Traitement normal |

Le « rebond du nouvel entraîneur » est en grande partie un artefact
statistique : un entraîneur est renvoyé après une série anormalement mauvaise,
et la régression vers la moyenne fait le reste. **Ne pas le tarifer comme un
effet causal.**

---

## 9. Récapitulatif des plafonds

| Contrainte | Valeur |
|---|---|
| Produit des ajustements, par équipe | 0,80 – 1,25 |
| Nombre de facteurs simultanés | 3 maximum |
| Ajustement d'un facteur unique | ±12 % maximum |
| Ajustement sur `λ_marché` | interdit |
| Ajustement fondé sur une information non vérifiable | interdit |
| Ajustement après avoir vu la cote | à déclarer explicitement |

---

## 10. Anti-double-comptage

Avant d'appliquer un ajustement, poser deux questions :

1. **L'information est-elle publique ?** Si oui, elle est probablement déjà
   dans la cote. On n'ajuste que la part que le marché sous-réagit — jamais la
   totalité de l'effet.
2. **La cote a-t-elle bougé depuis la publication de l'information ?**
   - Cote bougée dans le sens attendu → **ne pas ajuster**, c'est fait.
   - Cote immobile → ajuster à **50 %** du barème ; le marché a peut-être une
     raison de ne pas bouger.
   - Cote bougée en sens inverse → **s'arrêter et enquêter**. Il manque une
     information.

Cas typique : l'absence du buteur vedette est annoncée trois jours avant le
match, la cote passe de 2,10 à 2,35. Appliquer en plus un ×0,90 sur λ_attaque
revient à compter l'information deux fois et à fabriquer un faux avantage.

---

## 11. Trace obligatoire

Tout ajustement figure dans la sortie sous cette forme :

```
Ajustements domicile : 0,90 (absence buteur, [FOURNI] 12/03) x 0,97 (3 j de repos, [FOURNI]) = 0,873
Ajustements exterieur : 1,00
Cote non consultee avant ajustement : oui
```

Un ajustement non tracé n'existe pas.
