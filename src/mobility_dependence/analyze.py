from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "processed" / "communes_2022.csv"


def main() -> None:
    df = pd.read_csv(
        DATA_FILE,
        dtype={"code_com": "string"},
    )

    # Communes sans population active exploitable.
    df = df.loc[df["share_car"].notna()].copy()

    print("=== Ensemble des communes ===")
    print(
        df.groupby("has_station")["share_car"]
        .agg(["count", "mean", "median"])
        .rename(index={0: "sans gare", 1: "avec gare"})
    )

    print()
    print("=== À densité comparable ===")

    df["density_quartile"] = pd.qcut(
        df["density"],
        q=4,
        labels=["Q1", "Q2", "Q3", "Q4"],
        duplicates="drop",
    )

    result = (
        df.groupby(
            ["density_quartile", "has_station"],
            observed=True,
        )["share_car"]
        .agg(["count", "mean", "median"])
        .reset_index()
    )

    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
