# 13 — LEXIQUE

**Avantage (edge).** Espérance de gain par unité misée : `p × cote − 1`.
Un avantage de 5 % signifie qu'on attend 5 centimes de gain par euro misé,
en moyenne et à long terme.

**Backtest walk-forward.** Validation où le modèle est réajusté à chaque date
sur les seules données antérieures. La seule forme de backtest qui ne fuit
pas.

**Binomiale négative.** Loi de comptage à variance supérieure à sa moyenne
(`variance = μ + μ²/shape`). Utilisée quand Poisson sous-estime les queues.

**Bourse d'échange.** Place où les parieurs se font face directement,
l'opérateur prélevant une commission sur les gains. Les prix y sont
généralement les plus proches de la vérité.

**Brier.** Métrique de calibration : somme des écarts quadratiques entre
probabilités annoncées et résultat observé.

**BTTS.** *Both teams to score* : les deux équipes marquent.

**Calibration.** Propriété d'un système dont les probabilités annoncées
correspondent aux fréquences observées. Distincte de la rentabilité.

**CLV (Closing Line Value).** Écart entre la cote obtenue et la cote de
clôture déviguée. Indicateur n° 1 du système : il converge environ dix fois
plus vite que le ROI.

**Cote équitable (fair odds).** `1 / probabilité`. La cote sans marge.

**Devig (retrait de marge).** Transformation des cotes affichées en
probabilités sommant à 1. Cinq méthodes : multiplicative, additive,
puissance, odds-ratio, Shin.

**Dixon-Coles.** Modèle de 1997 corrigeant la dépendance des scores bas dans
le modèle de Poisson bivarié, via le paramètre `ρ`.

**DNB (draw no bet).** Pari remboursé en cas de nul. Équivaut au handicap
asiatique de ligne 0.

**Drawdown.** Baisse depuis le sommet historique de la banque, en pourcentage.

**ECE (Expected Calibration Error).** Écart moyen, pondéré par les effectifs,
entre probabilité annoncée et fréquence observée par bac.

**Entropie.** Incertitude d'une distribution, en bits. Maximum 1,58 pour un
1X2 (trois issues équiprobables). Un match à 1,55 bits est très ouvert.

**Handicap asiatique (AH).** Handicap en buts appliqué à une équipe, avec
remboursement possible sur les lignes entières et division de mise sur les
lignes quart.

**Kelly (critère de).** Mise maximisant la croissance logarithmique de la
banque : `f* = (p·cote − 1)/(cote − 1)`. Toujours utilisé en fraction.

**Ligne quart.** Ligne en x,25 ou x,75 : deux demi-mises sur les demi-lignes
adjacentes.

**Marge (overround, vig).** `Σ(1/cote) − 1`. La commission implicite de
l'opérateur.

**Palier d'efficience.** Classement d'un championnat de 1 (marché très
efficient) à 4 (marché mou). Détermine `w_marché`, l'avantage minimal et la
fraction de Kelly.

**Pooling log-linéaire.** Fusion de distributions par moyenne géométrique
pondérée, puis renormalisation. Préserve les rapports de cotes.

**RPS (Ranked Probability Score).** Métrique de référence du 1X2, tenant
compte de l'ordre des issues.

**Shin (modèle de).** Méthode de retrait de marge fondée sur l'hypothèse que
la marge rémunère le risque face à des parieurs informés. Référence pour 2 et
3 issues.

**Sur-dispersion.** Situation où la variance observée dépasse celle prévue par
Poisson. Traitée par la binomiale négative (`shape`).

**Suprématie.** `λ_domicile − λ_extérieur`. Encode l'avantage attendu ; c'est
la dimension que fixe la ligne de handicap.

**Total.** `λ_domicile + λ_extérieur`. Buts attendus du match.

**τ (tau).** Facteur correctif de Dixon-Coles sur les quatre scores bas.

**w_marché.** Poids accordé au marché dans la fusion. 0 = modèle pur,
1 = marché pur.

**xG (buts attendus).** Somme des probabilités de but des tirs d'une équipe.
Estimateur moins bruité que les buts pour mesurer une force.

**z (d'un pari).** `avantage / (σ × cote)`. Nombre d'écarts-types séparant
l'avantage estimé de zéro. Critère de tri prioritaire sur l'avantage brut.

**σ (sigma).** Écart-type de la probabilité estimée. Combine désaccord
modèle/marché, dispersion de devig et bruit d'estimation.

**λ (lambda).** Intensité de buts attendue d'une équipe sur le match.
