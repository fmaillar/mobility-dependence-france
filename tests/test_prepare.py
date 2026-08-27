from pathlib import Path

import pandas as pd
import pytest

from mobility_dependence import prepare


def test_load_rail_supply_aggregates_by_commune(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "geofer.csv"

    pd.DataFrame(
        {
            "inseeCommune": ["67001", "67001", "67002"],
            "codeUic": ["A", "B", "C"],
            "arretsTer2022": [10, 20, 5],
            "arretsTgv2022": [2, 3, 0],
            "arretsIntercites2022": [1, 0, 4],
            "arretsCars2022": [5, 6, 7],
            "totalArrets2022": [18, 29, 16],
        }
    ).to_csv(path, index=False)

    monkeypatch.setattr(prepare, "GEOFER_FILE", path)

    result = prepare.load_rail_supply().set_index("code_com")

    assert result.loc["67001", "rail_stations_2022"] == 2
    assert result.loc["67001", "rail_stops_2022"] == 36
    assert result.loc["67001", "ter_stops_2022"] == 30
    assert result.loc["67001", "tgv_stops_2022"] == 5
    assert result.loc["67001", "intercites_stops_2022"] == 1

    assert result.loc["67002", "rail_stops_2022"] == 9


def test_load_rail_supply_treats_invalid_values_as_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "geofer.csv"

    pd.DataFrame(
        {
            "inseeCommune": ["67001"],
            "codeUic": ["A"],
            "arretsTer2022": ["10"],
            "arretsTgv2022": ["inconnu"],
            "arretsIntercites2022": [None],
            "arretsCars2022": [None],
            "totalArrets2022": ["10"],
        }
    ).to_csv(path, index=False)

    monkeypatch.setattr(prepare, "GEOFER_FILE", path)

    result = prepare.load_rail_supply()

    assert result.loc[0, "rail_stops_2022"] == 10


def test_load_living_standard_replaces_zero_with_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "living_standard.csv"

    pd.DataFrame(
        {
            "code_com": ["67001", "67002", "67003"],
            "annee": [2021, 2021, 2020],
            "valeur": [25_000, 0, 99_999],
        }
    ).to_csv(path, index=False)

    monkeypatch.setattr(prepare, "LIVING_STANDARD_FILE", path)

    result = prepare.load_living_standard().set_index("code_com")

    assert result.loc["67001", "median_living_standard"] == 25_000
    assert pd.isna(result.loc["67002", "median_living_standard"])
    assert "67003" not in result.index
