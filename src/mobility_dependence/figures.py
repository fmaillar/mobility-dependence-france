from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "processed" / "communes_2022.csv"
FIGURES_DIR = ROOT / "reports" / "figures"

BASE = (
    "log_density_centered + log_density_centered_sq + "
    "z_log_population + z_median_living_standard"
)
BASE_DISTANCE = f"{BASE} + z_distance_car"

COLUMNS = [
    "share_car",
    "density",
    "population",
    "distance_car",
    "median_living_standard",
    "rail_stops_2022",
    "categorie_aire_attraction",
    "dep_code",
]


def load_data() -> pd.DataFrame:
    df = (
        pd.read_csv(
            DATA_FILE,
            dtype={
                "code_com": "string",
                "dep_code": "string",
                "categorie_aire_attraction": "string",
            },
        )[COLUMNS]
        .dropna()
        .copy()
    )

    df = df.loc[
        df["density"].gt(0)
        & df["population"].gt(0)
        & df["median_living_standard"].gt(0)
    ].copy()

    df["log_density"] = np.log(df["density"])
    df["log_population"] = np.log(df["population"])
    df["log_density_centered"] = df["log_density"] - df["log_density"].mean()
    df["log_density_centered_sq"] = df["log_density_centered"] ** 2

    for column in ("log_population", "distance_car", "median_living_standard"):
        df[f"z_{column}"] = (df[column] - df[column].mean()) / df[column].std()

    df["log_rail_stops_2022"] = np.log1p(df["rail_stops_2022"])
    return df


def fit(df: pd.DataFrame, formula: str, *, cluster: bool = False) -> Any:
    model = smf.ols(formula=formula, data=df)
    if cluster:
        return model.fit(
            cov_type="cluster",
            cov_kwds={"groups": df["dep_code"]},
        )
    return model.fit(cov_type="HC3")


def save_figure(fig: plt.Figure, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def rail_supply_distribution(served: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(served["log_rail_stops_2022"], bins=35)
    ax.set(
        xlabel="log(1 + nombre d'arrêts ferroviaires)",
        ylabel="Nombre de communes",
        title="Distribution de l'offre ferroviaire en 2022",
    )
    fig.tight_layout()
    ax.set_axisbelow(True)
    ax.grid(True, which="major", axis="both", alpha=0.3, linewidth=0.5)
    save_figure(fig, "rail_supply_distribution")


def adjusted_quartiles(served: pd.DataFrame) -> None:
    data = served.copy()
    data["rail_supply_quartile"] = pd.qcut(
        data["rail_stops_2022"],
        4,
        labels=["Q1", "Q2", "Q3", "Q4"],
    )

    model = fit(
        data,
        f"share_car ~ {BASE} + C(rail_supply_quartile)",
    )

    labels = ["Q1", "Q2", "Q3", "Q4"]
    estimates = [0.0]
    lower = [0.0]
    upper = [0.0]

    for quartile in labels[1:]:
        key = f"C(rail_supply_quartile)[T.{quartile}]"
        ci = model.conf_int().loc[key]
        estimates.append(float(model.params[key]))
        lower.append(float(ci.iloc[0]))
        upper.append(float(ci.iloc[1]))

    estimates_array = np.asarray(estimates)
    errors = np.vstack(
        [
            estimates_array - np.asarray(lower),
            np.asarray(upper) - estimates_array,
        ]
    )

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.errorbar(
        labels,
        estimates_array,
        yerr=errors,
        fmt="o",
        capsize=4,
    )
    ax.axhline(0, linewidth=1)
    ax.set(
        xlabel="Quartile de desserte ferroviaire",
        ylabel="Écart ajusté de part automobile (points)",
        title="Part automobile ajustée selon le niveau de desserte",
    )
    ax.set_axisbelow(True)
    ax.grid(True, which="major", axis="both", alpha=0.3, linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, "rail_supply_quartiles_adjusted")


def adjusted_rail_effect(served: pd.DataFrame) -> None:
    formula = (
        f"share_car ~ {BASE} + "
        "C(categorie_aire_attraction) + log_rail_stops_2022"
    )
    model = fit(served, formula)

    low, high = served["rail_stops_2022"].quantile([0.01, 0.99])
    stops = np.geomspace(max(1.0, low), high, 120)
    reference_aav = sorted(served["categorie_aire_attraction"].unique())[0]

    grid = pd.DataFrame(
        {
            "log_density_centered": 0.0,
            "log_density_centered_sq": 0.0,
            "z_log_population": 0.0,
            "z_median_living_standard": 0.0,
            "categorie_aire_attraction": reference_aav,
            "log_rail_stops_2022": np.log1p(stops),
        }
    )

    prediction = model.get_prediction(grid).summary_frame(alpha=0.05)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(stops, prediction["mean"])
    ax.fill_between(
        stops,
        prediction["mean_ci_lower"],
        prediction["mean_ci_upper"],
        alpha=0.3,
    )
    ax.set_xscale("log")
    ax.set(
        xlabel="Nombre d'arrêts ferroviaires en 2022",
        ylabel="Part automobile prédite (%)",
        title="Association ajustée entre desserte ferroviaire et part automobile",
    )
    ax.set_axisbelow(True)
    ax.grid(True, which="major", axis="both", alpha=0.3, linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, "adjusted_rail_effect")


def robustness_coefficients(served: pd.DataFrame) -> None:
    specifications = [
        (
            "Contrôles initiaux",
            fit(
                served,
                f"share_car ~ {BASE_DISTANCE} + log_rail_stops_2022",
            ),
        ),
        (
            "Sans distance voiture",
            fit(
                served,
                f"share_car ~ {BASE} + log_rail_stops_2022",
            ),
        ),
        (
            "Contrôle AAV",
            fit(
                served,
                (
                    f"share_car ~ {BASE} + "
                    "C(categorie_aire_attraction) + log_rail_stops_2022"
                ),
            ),
        ),
        (
            "AAV + cluster département",
            fit(
                served,
                (
                    f"share_car ~ {BASE} + "
                    "C(categorie_aire_attraction) + log_rail_stops_2022"
                ),
                cluster=True,
            ),
        ),
    ]

    labels = []
    estimates = []
    lower = []
    upper = []

    for label, model in specifications:
        ci = model.conf_int().loc["log_rail_stops_2022"]
        labels.append(label)
        estimates.append(float(model.params["log_rail_stops_2022"]))
        lower.append(float(ci.iloc[0]))
        upper.append(float(ci.iloc[1]))

    estimates_array = np.asarray(estimates)
    errors = np.vstack(
        [
            estimates_array - np.asarray(lower),
            np.asarray(upper) - estimates_array,
        ]
    )
    y = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(
        estimates_array,
        y,
        xerr=errors,
        fmt="o",
        capsize=4,
    )
    ax.axvline(0, linewidth=1)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set(
        xlabel="Coefficient de log(1 + arrêts ferroviaires), IC95 %",
        title="Robustesse de l'association entre offre ferroviaire et part automobile",
    )
    ax.set_axisbelow(True)
    ax.grid(True, which="major", axis="both", alpha=0.3, linewidth=0.5)
    fig.tight_layout()
    save_figure(fig, "robustness_coefficients")


def main() -> None:
    df = load_data()
    served = df.loc[df["rail_stops_2022"].gt(0)].copy()

    rail_supply_distribution(served)
    adjusted_quartiles(served)
    adjusted_rail_effect(served)
    robustness_coefficients(served)

    print(f"Figures : {FIGURES_DIR}")


if __name__ == "__main__":
    main()
