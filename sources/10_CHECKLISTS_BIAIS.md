# 10 — LISTES DE CONTRÔLE, SIGNAUX D'ALERTE, BIAIS

---

## 1. Contrôle avant tarification

- [ ] Les deux équipes sont identifiées sans ambiguïté (homonymes, équipes B,
      catégories d'âge, section masculine / féminine).
- [ ] La compétition et le palier d'efficience sont établis.
- [ ] Le lieu est confirmé (terrain neutre ? inversion domicile / extérieur ?
      huis clos ? stade de substitution ?).
- [ ] La date et l'heure du coup d'envoi sont connues.
- [ ] Les cotes proviennent d'un opérateur identifié, et sont horodatées.
- [ ] Le modèle dispose du minimum de matchs requis pour le palier.
- [ ] Aucun événement structurel non intégré depuis la dernière donnée
      (mercato, changement d'entraîneur, sanction administrative, retrait).

## 2. Contrôle avant mise

- [ ] L'avantage dépasse le seuil du palier, **et** `z ≥ 1,0`.
- [ ] La cote a été revérifiée à l'instant de la mise (elle a pu bouger).
- [ ] La mise respecte : plafond par pari, exposition par match, exposition
      par journée, exposition totale.
- [ ] Les paris corrélés du même match sont traités en groupe.
- [ ] La ligne de journal est écrite **avant** la validation du pari.
- [ ] Deux ou trois éléments d'invalidation ont été formulés explicitement.
- [ ] Aucun ajustement n'a été ajouté *après* avoir vu la cote.

## 3. Contrôle après match

- [ ] Cote de clôture relevée et déviguée.
- [ ] CLV calculé et consigné.
- [ ] Résultat et gain consignés.
- [ ] Si le pari a perdu : la décision était-elle bonne ? (question distincte)
- [ ] Si le pari a gagné : la décision était-elle bonne ? (même question)

---

## 4. Signaux d'alerte — arrêt immédiat de l'analyse

Chacun de ces signaux signifie qu'il manque une information. On ne mise pas
avant de l'avoir trouvée.

| Signal | Hypothèse la plus probable |
|---|---|
| Avantage annoncé > 15 % sur un marché principal | Erreur de saisie, de sens, ou d'unité |
| Un seul opérateur très décalé du reste du marché | Erreur de l'opérateur, ou information qu'il détient |
| La cote a bougé fortement contre vous depuis votre analyse | Le marché sait quelque chose |
| Marge du marché > 12 % | Marché non formé ; aucun ancrage fiable |
| Suprématie du modèle > 2,5 buts | Vérifier les données ; suspecter une équipe mal identifiée |
| Total du modèle hors de la plage [1,5 ; 4,5] | Erreur de paramétrage |
| Une équipe n'a pas joué depuis plus de 45 jours | Trêve, sanction, ou données manquantes |
| Cote proposée > 1,25 × votre cote juste | Vérifier les règles de règlement du marché |
| L'avantage disparaît si on change de méthode de devig | Ce n'était pas un avantage |

---

## 5. Biais cognitifs et parades opérationnelles

| Biais | Manifestation typique | Parade intégrée au système |
|---|---|---|
| **Confirmation** | Chercher les statistiques qui valident le pari envisagé | Calculer avant de lire la cote ; ordre des phases imposé |
| **Récence** | Sur-pondérer les trois derniers matchs | Pondération temporelle explicite, demi-vie choisie par backtest |
| **Résultat** | Juger la décision au résultat | Post-mortem sur la décision ; CLV comme juge |
| **Narratif** | « Ils sont en confiance », « ils n'ont plus rien à jouer » | Ajustements plafonnés et chiffrés ; motivation par simulation |
| **Ancrage** | Partir de la cote affichée puis « ajuster » | Estimation modèle produite avant la confrontation |
| **Excès de confiance** | Miser plus après une bonne série | Fraction de Kelly fixe, plafonds absolus |
| **Aversion à la perte** | Chasser les pertes en fin de journée | Plan de mise arrêté à l'avance, paliers de réduction |
| **Coût irrécupérable** | Rester sur un championnat non rentable par habitude | Critères d'arrêt écrits à l'avance |
| **Sélection** | Ne retenir que les championnats qui ont marché | Audit sur **tous** les championnats testés |
| **Illusion de contrôle** | Multiplier les analyses pour se rassurer | Recevabilité en phase 0 ; s'abstenir est une sortie normale |

**Le biais le plus coûteux** n'est aucun de ceux-ci : c'est de **fabriquer un
pari parce qu'on a passé une heure à analyser un match**. Le temps investi est
irrécupérable ; il n'entre pas dans la décision.

---

## 6. Pré-mortem — à faire avant de miser

Se projeter six mois plus tard, la banque a perdu 30 %. Qu'est-ce qui a
échoué ? Réponses les plus fréquentes, dans l'ordre :

1. Les probabilités étaient mal calibrées et le CLV négatif dès le départ —
   personne n'a regardé.
2. Le modèle a été ajusté et testé sur les mêmes données.
3. Les mises ont dépassé les plafonds sur quelques « convictions ».
4. La méthode de devig gonflait artificiellement l'avantage sur les grosses
   cotes.
5. Le journal n'a pas été tenu, donc rien n'était mesurable.
6. Le championnat choisi n'avait plus la même structure (règlement, format,
   mercato massif).
7. Une série de pertes normale a été interprétée comme un échec du système,
   et les règles ont été changées au pire moment.

Chacune de ces causes est évitable par une règle déjà écrite dans ce système.
Le seul risque résiduel est de **ne pas les appliquer**.

---

## 7. Les dix erreurs qui distinguent l'amateur du professionnel

1. Comparer une cote brute à une probabilité, sans retirer la marge.
2. Utiliser la normalisation multiplicative sur des cotes élevées.
3. Ancrer sur un opérateur généraliste au lieu d'un marché à faible marge.
4. Traiter le nul comme un résidu au lieu de le modéliser (correction ρ).
5. Miser un pourcentage fixe, sans lien avec l'avantage.
6. Combiner deux sélections corrélées du même match sans les simuler.
7. Ajuster le modèle sur toute la saison, puis « backtester » dessus.
8. Juger un système sur trois mois de ROI.
9. Ignorer le CLV.
10. Continuer à parier un championnat après avoir cessé de le mesurer.

---

## 8. Format de la question d'invalidation

Chaque analyse se termine par : **« qu'est-ce qui prouverait que j'ai tort ? »**
Deux à quatre éléments, concrets et vérifiables avant le coup d'envoi.

Exemples corrects :
- « Si la composition officielle montre l'absence de X et Y, la suprématie
  passe sous 0,25 et le pari disparaît. »
- « Si la cote de l'opérateur de référence descend sous 2,05, mon avantage
  est déjà consommé. »
- « Si la pluie annoncée tombe effectivement, le total passe sous 2,4 et le
  pari "plus de 2,5" n'a plus de valeur. »

Exemples incorrects (non vérifiables, non falsifiables) :
- « S'ils ne sont pas dans un bon jour. »
- « Si l'arbitre est défavorable. »
- « Si la chance tourne. »
