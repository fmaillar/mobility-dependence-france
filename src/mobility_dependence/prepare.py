from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

MODAL_SHARE_FILE = DATA_RAW / "modal_share" / "part-actifs-modes-transport_com"
COMMUTE_DISTANCE_FILE = DATA_RAW / "commute_distance" / "distance-moyenne-dom-trav_com"
POPULATION_DENSITY_FILE = DATA_RAW / "population_density" / "densite-population_com"
LIVING_STANDARD_FILE = DATA_RAW / "living_standard" / "mediane-niveau-vie_com"
POVERTY_FILE = DATA_RAW / "poverty" / "taux-pauvrete_com"
GEOFER_FILE = DATA_RAW / "geofer" / "geofer_gares.csv"

OUTPUT_FILE = DATA_PROCESSED / "communes_2022.csv"
TERRITORIAL_CONTROLS_FILE = DATA_PROCESSED / "territorial_controls.csv"

MODE_NAMES = {
    "Voiture": "car",
    "Transports en commun": "public_transport",
    "Vélo": "bike",
    "Vélo (depuis 2017)": "bike",
    "Marche": "walk",
    "Deux-roues motorisé": "motorbike",
    "Deux-roues motorisé (depuis 2017)": "motorbike",
    "Pas de transport": "no_transport",
}


STATIONS_FILE = DATA_RAW / "stations" / "gares-de-voyageurs.csv"

STATION_USAGE_FILE = DATA_RAW / "station_usage" / "frequentation-gares.csv"


def load_territorial_controls() -> pd.DataFrame:
    return pd.read_csv(
        TERRITORIAL_CONTROLS_FILE,
        dtype={
            "code_com": "string",
            "code_aire_attraction": "string",
            "categorie_aire_attraction": "string",
            "taille_aire_attraction": "string",
        },
    )


def load_modal_share() -> pd.DataFrame:
    df = pd.read_csv(
        MODAL_SHARE_FILE,
        dtype={"code_com": "string"},
    )

    df = df.loc[df["annee"].eq(2022)].copy()
    df = df.loc[df["valeur"].notna()].copy()

    df = df.loc[df["mode_transport"].ne("Deux-roues (jusqu'à 2016)")].copy()

    df["mode"] = df["mode_transport"].map(MODE_NAMES)

    if df["mode"].isna().any():
        unknown = sorted(df.loc[df["mode"].isna(), "mode_transport"].unique())
        raise ValueError(f"Modes inconnus dans modal_share : {unknown}")

    result = df.pivot(
        index=["code_com", "nom_territoire"],
        columns="mode",
        values="valeur",
    )

    result = result.add_prefix("share_").reset_index()

    return result


def load_commute_distance() -> pd.DataFrame:
    df = pd.read_csv(
        COMMUTE_DISTANCE_FILE,
        dtype={"code_com": "string"},
    )

    df = df.loc[df["annee"].eq(2022)].copy()

    df["mode"] = df["mode_transport"].map(MODE_NAMES)

    if df["mode"].isna().any():
        unknown = sorted(df.loc[df["mode"].isna(), "mode_transport"].unique())
        raise ValueError(f"Modes inconnus dans commute_distance : {unknown}")

    result = df.pivot(
        index=["code_com", "nom_territoire"],
        columns="mode",
        values="valeur",
    )

    result = result.add_prefix("distance_").reset_index()

    return result


def load_population_density() -> pd.DataFrame:
    df = pd.read_csv(
        POPULATION_DENSITY_FILE,
        dtype={"code_com": "string"},
    )

    df = df.loc[df["annee"].eq(2022)].copy()

    return df[
        [
            "code_com",
            "nom_territoire",
            "valeur",
            "numerateur",
        ]
    ].rename(
        columns={
            "valeur": "density",
            "numerateur": "population",
        }
    )


def load_living_standard() -> pd.DataFrame:
    df = pd.read_csv(
        LIVING_STANDARD_FILE,
        dtype={"code_com": "string"},
    )

    df = df.loc[df["annee"].eq(2021)].copy()

    # Zero denotes unavailable FiLoSoFi data for some overseas communes.
    df.loc[df["valeur"].eq(0), "valeur"] = pd.NA

    return df[["code_com", "valeur"]].rename(columns={"valeur": "median_living_standard"})


def load_poverty() -> pd.DataFrame:
    df = pd.read_csv(
        POVERTY_FILE,
        dtype={"code_com": "string"},
    )

    df = df.loc[df["annee"].eq(2021)].copy()

    return df[["code_com", "valeur"]].rename(columns={"valeur": "poverty_rate"})


def load_station_usage() -> pd.DataFrame:
    stations = pd.read_csv(
        STATIONS_FILE,
        sep=";",
        dtype={
            "Code commune": "string",
            "Code_UIC": "string",
            "Id_Gare": "string",
        },
    )

    usage = pd.read_csv(
        STATION_USAGE_FILE,
        sep=";",
        dtype={"Code UIC": "string"},
    )

    # Une gare SNCF peut être associée à plusieurs codes UIC.
    stations = stations.assign(Code_UIC=stations["Code_UIC"].str.split(";")).explode("Code_UIC")

    usage = usage[
        [
            "Code UIC",
            "Total Voyageurs 2022",
        ]
    ].rename(
        columns={
            "Code UIC": "Code_UIC",
            "Total Voyageurs 2022": "passengers_2022",
        }
    )

    joined = stations.merge(
        usage,
        on="Code_UIC",
        how="left",
        validate="many_to_one",
    )

    # Reconstitue une fréquentation unique par gare.
    by_station = joined.groupby(
        [
            "Id_Gare",
            "Nom_Gare",
            "Code commune",
        ],
        as_index=False,
        dropna=False,
    ).agg(
        matched_uic=("passengers_2022", "count"),
        passengers_2022=("passengers_2022", "sum"),
    )

    # sum() retourne 0 même si toutes les valeurs sont manquantes.
    # On rétablit explicitement NaN dans ce cas.
    by_station.loc[
        by_station["matched_uic"].eq(0),
        "passengers_2022",
    ] = pd.NA

    by_commune = (
        by_station.groupby(
            "Code commune",
            as_index=False,
        )
        .agg(
            station_count=("Id_Gare", "nunique"),
            stations_with_usage=("matched_uic", lambda s: s.gt(0).sum()),
            station_passengers_2022=("passengers_2022", "sum"),
        )
        .rename(columns={"Code commune": "code_com"})
    )

    # Si toutes les gares d'une commune sont sans donnée de fréquentation,
    # la somme doit rester inconnue et non égale à zéro.
    by_commune.loc[
        by_commune["stations_with_usage"].eq(0),
        "station_passengers_2022",
    ] = pd.NA

    by_commune["has_station"] = 1

    return by_commune[
        [
            "code_com",
            "has_station",
            "station_count",
            "station_passengers_2022",
        ]
    ]


def load_rail_supply() -> pd.DataFrame:
    df = pd.read_csv(
        GEOFER_FILE,
        dtype={
            "inseeCommune": "string",
            "codeUic": "string",
        },
    )

    cols = [
        "arretsCars2022",
        "arretsTer2022",
        "arretsTgv2022",
        "arretsIntercites2022",
        "totalArrets2022",
    ]

    for column in cols:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["rail_stops_2022"] = df["arretsTer2022"] + df["arretsTgv2022"] + df["arretsIntercites2022"]

    by_commune = (
        df.groupby("inseeCommune", as_index=False)
        .agg(
            rail_stations_2022=("codeUic", "nunique"),
            rail_stops_2022=("rail_stops_2022", "sum"),
            ter_stops_2022=("arretsTer2022", "sum"),
            tgv_stops_2022=("arretsTgv2022", "sum"),
            intercites_stops_2022=("arretsIntercites2022", "sum"),
            coach_stops_2022=("arretsCars2022", "sum"),
            total_stops_2022=("totalArrets2022", "sum"),
        )
        .rename(columns={"inseeCommune": "code_com"})
    )

    return by_commune


def build_dataset() -> pd.DataFrame:
    modal_share = load_modal_share()
    commute_distance = load_commute_distance()
    population_density = load_population_density()
    living_standard = load_living_standard()
    poverty = load_poverty()
    station_usage = load_station_usage()
    rail_supply = load_rail_supply()
    territorial_controls = load_territorial_controls()

    df = modal_share.merge(
        commute_distance.drop(columns="nom_territoire"),
        on="code_com",
        how="inner",
        validate="one_to_one",
    )

    df = df.merge(
        population_density.drop(columns="nom_territoire"),
        on="code_com",
        how="inner",
        validate="one_to_one",
    )

    df = df.merge(
        living_standard,
        on="code_com",
        how="left",
        validate="one_to_one",
    )

    df = df.merge(
        poverty,
        on="code_com",
        how="left",
        validate="one_to_one",
    )

    df = df.merge(
        station_usage,
        on="code_com",
        how="left",
        validate="one_to_one",
    )

    no_station = df["has_station"].isna()

    df.loc[no_station, "has_station"] = 0
    df.loc[no_station, "station_count"] = 0
    df.loc[no_station, "station_passengers_2022"] = 0

    df["has_station"] = df["has_station"].astype("int64")
    df["station_count"] = df["station_count"].astype("int64")

    df = df.merge(
        rail_supply,
        on="code_com",
        how="left",
        validate="one_to_one",
    )

    rail_cols = [
        "rail_stations_2022",
        "rail_stops_2022",
        "ter_stops_2022",
        "tgv_stops_2022",
        "intercites_stops_2022",
        "coach_stops_2022",
        "total_stops_2022",
    ]

    df[rail_cols] = df[rail_cols].fillna(0)
    df["rail_stations_2022"] = df["rail_stations_2022"].astype("int64")

    df = df.merge(
        territorial_controls,
        on="code_com",
        how="left",
        validate="one_to_one",
    )

    return df.sort_values("code_com").reset_index(drop=True)


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    df = build_dataset()
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Communes : {len(df):,}")
    print(f"Colonnes : {len(df.columns)}")
    print(f"Fichier  : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
