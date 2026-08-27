# Mobility Dependence France

Analyse territoriale de la dépendance automobile et des alternatives de mobilité en France, à partir de données ouvertes.

Le projet étudie en particulier la relation entre **l'intensité de la desserte ferroviaire** et **la part modale automobile** à l'échelle communale.

## Question de recherche

> À caractéristiques territoriales comparables, les communes bénéficiant d'une offre ferroviaire plus importante présentent-elles une part modale automobile plus faible ?

L'analyse principale porte sur les communes françaises effectivement desservies par le rail en 2022. Les modèles contrôlent notamment la densité, la population, le niveau de vie médian et la position de la commune dans l'aire d'attraction des villes.

Les résultats doivent être interprétés comme des **associations statistiques**, et non comme des effets causaux.

## Résultat principal

Sur les communes desservies par le rail et disposant de l'ensemble des variables de contrôle, une offre ferroviaire plus importante est associée à une part modale automobile plus faible.

Dans le modèle principal avec contrôle AAV :

- coefficient de `log(1 + rail_stops_2022)` : **-1,787** ;
- un doublement de l'offre ferroviaire est associé à environ **1,24 point de part automobile en moins** ;
- le résultat reste significatif avec des erreurs-types clusterisées par département.

Le manuscrit complet détaille les hypothèses, les modèles, les tests de robustesse et les limites.

## Manuscrit

- Source Org : `article_offre_ferroviaire_dependance_automobile_pdflatex_png.org`
- Version PDF : `article_offre_ferroviaire_dependance_automobile_pdflatex_png.pdf`
- Bibliographie : `references.bib`

## Données

Les données sources proviennent principalement de data.gouv.fr et sont identifiées par leurs IDs afin de rendre l'analyse reproductible.

### Repérage des jeux de données

Le projet [`datagouv-toolkit`](https://github.com/fmaillar/datagouv-toolkit) a été utilisé lors de la phase exploratoire pour rechercher des jeux de données sur data.gouv.fr, inspecter leurs métadonnées et leurs ressources, puis sélectionner les sources pertinentes pour l'analyse.

Les transformations statistiques et la construction du jeu analytique final sont ensuite réalisées dans ce dépôt.

### Jeux principaux

| Jeu de données | ID data.gouv.fr | Millésime |
|---|---|---:|
| Part d'actifs selon le mode de transport principalement utilisé pour aller travailler | `69b987f0c23eb0dd77b7ef87` | 2022 |
| Densité de population | `69b98949748e7142f7dbfbe9` | 2022 |
| Niveau de vie médian | `69b9895e1bf5eccb0bd6c7af` | 2021 |
| Géofer : données de potentiel territorial des gares ferroviaires | `6a4f9d36ecbf25ed35d214bb` | desserte 2022 |
| Communes et villes de France : codes, géographie et zonages | `6745d9ae4524d845d2138193` | ressource 2026, AAV 2020 |

### Jeux complémentaires

| Jeu de données | ID data.gouv.fr |
|---|---|
| Distance moyenne selon le mode de transport principal | `69b987fe289c75351a937a1c` |
| SNCF — Gares de voyageurs | `65d81858179dc96581d981db` |
| SNCF — Fréquentation en gares | `5959364ba3a7291dcf9c8295` |

Les données publiées sur data.gouv.fr ne sont pas modifiées. Les transformations sont effectuées localement dans `data/processed/`.

Les données brutes ne sont pas nécessairement versionnées dans le dépôt.

## Structure du projet

```text
.
|-- article_offre_ferroviaire_dependance_automobile_pdflatex_png.org
|-- article_offre_ferroviaire_dependance_automobile_pdflatex_png.pdf
|-- references.bib
|-- pyproject.toml
|-- data/
|   |-- raw/
|   `-- processed/
|-- reports/
|   `-- figures/
|-- src/
|   `-- mobility_dependence/
|       |-- datasets.py
|       |-- prepare.py
|       |-- territorial_controls.py
|       |-- analyze.py
|       |-- regression.py
|       `-- figures.py
`-- tests/
```

## Installation

Le projet nécessite Python 3.11 ou supérieur.

```bash
git clone https://github.com/fmaillar/mobility-dependence-france.git
cd mobility-dependence-france

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

Pour installer aussi les outils de développement :

```bash
pip install -e '.[dev]'
```

Les dépendances principales sont :

- pandas ;
- statsmodels ;
- matplotlib.

## Reproduction de l'analyse

Une fois les données brutes placées dans les sous-répertoires attendus de `data/raw/`, la chaîne principale est :

```bash
python -m mobility_dependence.territorial_controls
python -m mobility_dependence.prepare
python -m mobility_dependence.regression
python -m mobility_dependence.figures
```

### Fichiers produits

Le traitement territorial génère notamment :

```text
data/processed/territorial_controls.csv
```

La préparation principale génère :

```text
data/processed/communes_2022.csv
```

Les régressions produisent notamment :

```text
reports/regression_station.txt
reports/regression_rail_supply.txt
reports/regression_rail_supply_cluster.txt
reports/rail_supply_quartiles.csv
```

Les figures sont générées en PDF vectoriel et en PNG :

```text
reports/figures/
|-- rail_supply_distribution.pdf
|-- rail_supply_distribution.png
|-- adjusted_rail_effect.pdf
|-- adjusted_rail_effect.png
|-- rail_supply_quartiles_adjusted.pdf
|-- rail_supply_quartiles_adjusted.png
|-- robustness_coefficients.pdf
`-- robustness_coefficients.png
```

## Figures

Les quatre figures principales présentent :

1. la distribution de l'offre ferroviaire ;
2. l'association ajustée entre offre ferroviaire et part automobile ;
3. les écarts ajustés selon les quartiles de desserte ;
4. la robustesse du coefficient ferroviaire selon plusieurs spécifications.

## Contrôle qualité

Les outils de développement sont déclarés dans `pyproject.toml`.

```bash
ruff format --check .
ruff check .
mypy .
pytest -q
bandit -q -r src
```

## Génération du PDF

Le manuscrit est rédigé en Org mode et exporté vers LaTeX/PDF.

Depuis Emacs :

```text
C-c C-e l p
```

Le document utilise notamment `biblatex`/Biber pour la bibliographie et `pdflatex` pour la compilation.

Les figures incluses dans le manuscrit sont les versions PNG présentes dans `reports/figures/`.

## Reproductibilité et limites

Le dépôt contient le code de préparation, les modèles statistiques, les figures, la bibliographie et le manuscrit.

L'analyse actuelle est transversale et observationnelle. Elle ne permet pas d'établir un effet causal de l'offre ferroviaire sur la part automobile. Une extension envisagée consiste à exploiter la dimension temporelle de Géofer afin d'estimer des modèles longitudinaux à effets fixes communaux.

## Licence

Le code du projet est distribué sous licence **GNU General Public License v3.0 only (GPL-3.0-only)**.

Les jeux de données conservent leurs licences propres, telles qu'indiquées par leurs producteurs respectifs.
