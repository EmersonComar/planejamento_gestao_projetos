import io
import zipfile

import pandas as pd
import pytest

from src.infrastructure.sources import dive, ibge, inmet

INFORME = """
           TABELA 1: Casos notificados de dengue, segundo classificação final. Santa Catarina, 2025*.
  29 a 31/12/2024        36 (0.2%)              1 (0.4%)                0 (0%)            554 (0.5%)          73 (1.3%)            4 (0.2%)
           1                    599 (3.3%)             13 (4.7%)               2 (9.5%)          9.976 (9.2%)       370 (6.4%)           7 (0.4%)
           2                    721 (4.0%)             15 (5.5%)                0 (0%)           11.490 (11%)        509 (8.8%)          6 (0.3%)
  Até o momento, 237 municípios registraram casos prováveis de dengue.
"""


def test_dive_table_sums_probable_cases_and_skips_previous_year_days():
    table = dive.parse_monthly_table(INFORME).set_index("mes")
    assert list(table.index) == [1, 2]
    assert table.loc[1, "casos_provaveis"] == 599 + 13 + 2 + 370 + 7
    assert table.loc[1, "notificacoes"] == 599 + 13 + 2 + 9976 + 370 + 7
    assert table.loc[2, "descartados"] == 11490


def test_population_uses_census_and_interpolates_missing_year(monkeypatch):
    def fake_series(table, variable, year):
        values = {2021: 1000, 2022: 1100, 2024: 1210}
        if year not in values or (year == 2022) != (table == ibge.CENSUS_2022):
            return pd.Series(dtype="float64")
        return pd.Series({4200051: float(values[year])})

    monkeypatch.setattr(ibge, "_series", fake_series)
    population = ibge.population(2021, 2025).set_index("ano")
    assert population.loc[2022, "origem"] == "Censo 2022"
    assert population.loc[2023, "populacao"] == 1154  # média geométrica entre 1100 e 1210
    assert population.loc[2023, "origem"] == "Interpolada"
    assert population.loc[2025, "populacao"] == 1210 and population.loc[2025, "origem"] == "Repetida"


def _inmet_zip(header_station_key: str) -> io.BytesIO:
    header = "\n".join([
        "REGIAO:;S", "UF:;SC", f"{header_station_key};CHAPECO", "CODIGO (WMO):;A895",
        "LATITUDE:;-27,08", "LONGITUDE:;-52,63", "ALTITUDE:;679", "DATA DE FUNDACAO:;2019-01-01",
    ])
    rows = ["Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"]
    rows += [f"2019/01/{day:02d};{hour:02d}00 UTC;0,5" for day in range(1, 32) for hour in range(24)]
    rows += [f"2019/02/{day:02d};{hour:02d}00 UTC;-9999" for day in range(1, 29) for hour in range(24)]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("INMET_S_SC_A895_CHAPECO_01-01-2019_A_31-12-2019.CSV",
                         (header + "\n" + "\n".join(rows)).encode("latin-1"))
    buffer.seek(0)
    return buffer


@pytest.mark.parametrize("key", ["ESTAÇÃO:", "ESTACAO:", "ESTAC?O:"])
def test_inmet_reads_station_and_counts_measured_hours(tmp_path, key):
    path = tmp_path / "2019.zip"
    path.write_bytes(_inmet_zip(key).read())
    monthly, stations = inmet.read_year(path)
    assert stations.iloc[0][["codigo_estacao", "nome_estacao"]].tolist() == ["A895", "CHAPECO"]
    assert stations.iloc[0]["lat"] == pytest.approx(-27.08)
    by_month = monthly.set_index("ano_mes")
    assert by_month.loc[pd.Period("2019-01"), "horas_medidas"] == 31 * 24
    assert by_month.loc[pd.Period("2019-01"), "precipitacao_total"] == pytest.approx(31 * 24 * 0.5)
    assert by_month.loc[pd.Period("2019-02"), "horas_medidas"] == 0
