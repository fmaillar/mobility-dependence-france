from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "processed" / "communes_2022.csv"
REPORTS_DIR = ROOT / "reports"

BASE = (
    "log_density_centered + log_density_centered_sq + z_log_population + z_median_living_standard"
)
BASE_DISTANCE = f"{BASE} + z_distance_car"

COLUMNS = [
    "share_car",
    "density",
    "population",
    "distance_car",
    "median_living_standard",
    "has_station",
    "station_passengers_2022",
    "rail_stops_2022",
    "categorie_aire_attraction",
    "taille_aire_attraction",
    "dep_code",
]


def load_data() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_FILE,
        dtype={"code_com": "string", "dep_code": "string"}
    )[COLUMNS].dropna().copy()

    df = df.loc[
        df["density"].gt(0) & df["population"].gt(0) & df["median_living_standard"].gt(0)
    ].copy()

    df["log_density"] = np.log(df["density"])
    df["log_population"] = np.log(df["population"])
    df["log_density_centered"] = df["log_density"] - df["log_density"].mean()
    df["log_density_centered_sq"] = df["log_density_centered"] ** 2

    for column in ("log_population", "distance_car", "median_living_standard"):
        df[f"z_{column}"] = (df[column] - df[column].mean()) / df[column].std()

    df["log_station_passengers"] = np.log1p(df["station_passengers_2022"])
    df["log_station_passengers_per_capita"] = np.log1p(
        df["station_passengers_2022"] / df["population"]
    )
    df["log_rail_stops_2022"] = np.log1p(df["rail_stops_2022"])
    df["has_rail_service_2022"] = df["rail_stops_2022"].gt(0).astype("int64")

    return df


def fit_models(
    df: pd.DataFrame,
    formulas: dict[str, str],
    *,
    cov_type: str = "HC3",
    groups: pd.Series | None = None,
) -> dict[str, Any]:
    fit_kwargs: dict[str, Any] = {"cov_type": cov_type}

    if groups is not None:
        fit_kwargs["cov_kwds"] = {"groups": groups}

    return {
        title: smf.ols(formula=formula, data=df).fit(**fit_kwargs)
        for title, formula in formulas.items()
    }


def write_models_report(filename: str, models: dict[str, Any]) -> None:
    text = "\n\n".join(
        f"=== {title} ===\n{model.summary().as_text()}" for title, model in models.items()
    )
    (REPORTS_DIR / filename).write_text(text + "\n", encoding="utf-8")


def station_models(df: pd.DataFrame) -> None:
    formulas = {
        "Présence gare": f"share_car ~ {BASE_DISTANCE} + has_station",
        "Fréquentation gare": (
            f"share_car ~ {BASE_DISTANCE} + has_station + log_station_passengers"
        ),
        "Fréquentation par habitant": (
            f"share_car ~ {BASE_DISTANCE} + has_station + log_station_passengers_per_capita"
        ),
    }

    write_models_report(
        "regression_station.txt",
        fit_models(df, formulas),
    )


def rail_supply_models(df: pd.DataFrame) -> None:
    served = df.loc[df["rail_stops_2022"].gt(0)].copy()

    served["rail_supply_quartile"] = pd.qcut(
        served["rail_stops_2022"],
        4,
        labels=["Q1", "Q2", "Q3", "Q4"],
    )

    write_models_report(
        "regression_rail_supply.txt",
        {
            **fit_models(
                df,
                {
                    "Offre ferroviaire 2022": (
                        f"share_car ~ {BASE_DISTANCE} + has_rail_service_2022 + log_rail_stops_2022"
                    ),
                },
            ),
            **fit_models(
                served,
                {
                    "Communes desservies": (f"share_car ~ {BASE_DISTANCE} + log_rail_stops_2022"),
                    "Communes desservies — sans distance_car": (
                        f"share_car ~ {BASE} + log_rail_stops_2022"
                    ),
                    "Communes desservies — contrôle AAV": (
                        f"share_car ~ {BASE} + C(categorie_aire_attraction) + log_rail_stops_2022"
                    ),
                    "Communes desservies — quartiles": (
                        f"share_car ~ {BASE} + C(rail_supply_quartile)"
                    ),
                },
            ),
        },
    )

    write_models_report(
        "regression_rail_supply_cluster.txt",
        fit_models(
            served,
            {
                "Communes desservies — contrôle AAV — cluster département": (
                    f"share_car ~ {BASE} + C(categorie_aire_attraction) + log_rail_stops_2022"
                ),
            },
            cov_type="cluster",
            groups=served["dep_code"],
        ),
    )


def rail_supply_quartiles(df: pd.DataFrame) -> None:
    served = df.loc[df["rail_stops_2022"].gt(0)].copy()

    served["rail_supply_quartile"] = pd.qcut(
        served["rail_stops_2022"],
        4,
        labels=["Q1", "Q2", "Q3", "Q4"],
    )

    (
        served.groupby("rail_supply_quartile", observed=True)
        .agg(
            communes=("share_car", "size"),
            rail_stops_median=("rail_stops_2022", "median"),
            share_car_mean=("share_car", "mean"),
            share_car_median=("share_car", "median"),
        )
        .to_csv(REPORTS_DIR / "rail_supply_quartiles.csv")
    )


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    station_models(df)
    rail_supply_models(df)
    rail_supply_quartiles(df)

    print(f"Observations : {len(df):,}")
    print(f"Rapports     : {REPORTS_DIR}")


if __name__ == "__main__":
    main()
