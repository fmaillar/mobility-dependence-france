from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = (
    ROOT
    / "data"
    / "raw"
    / "territorial"
    / "Liste des communes de France 2026 et de leurs codes associés au format csv"
)
OUTPUT_FILE = ROOT / "data" / "processed" / "territorial_controls.csv"


def build_controls() -> pd.DataFrame:
    cols = [
        "code_insee",
        "dep_code",
        "code_aire_attraction",
        "categorie_aire_attraction",
        "taille_aire_attraction",
    ]

    df = pd.read_csv(
        RAW_FILE,
        usecols=cols,
        dtype="string",
    ).rename(columns={"code_insee": "code_com"})

    return df.drop_duplicates("code_com").sort_values("code_com").reset_index(drop=True)


def main() -> None:
    df = build_controls()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Communes : {len(df):,}")
    print(f"Fichier  : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
