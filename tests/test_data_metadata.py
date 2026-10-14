import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src.infrastructure.data.csv_repository import CsvDataRepository


def test_generation_time_requires_metadata_and_matching_csv(tmp_path, analytical_data):
    csv_path = tmp_path / 'base.csv'
    analytical_data.to_csv(csv_path, index=False)
    repo = CsvDataRepository(str(csv_path))
    assert repo.get_generation_time() is None
    metadata_path = csv_path.with_suffix('.metadata.json')
    metadata_path.write_text(json.dumps({
        'generated_at': '2026-10-13T15:30:00+00:00',
        'csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }))
    assert repo.get_generation_time() == pd.Timestamp('2026-10-13T12:30:00-03:00')
    csv_path.write_text(csv_path.read_text() + '\n')
    assert repo.get_generation_time() is None


@pytest.mark.parametrize('metadata', ['not json', '[]', '{}', '{"generated_at":"invalid"}'])
def test_invalid_metadata_does_not_break_dashboard(tmp_path, analytical_data, metadata):
    csv_path = tmp_path / 'base.csv'
    analytical_data.to_csv(csv_path, index=False)
    csv_path.with_suffix('.metadata.json').write_text(metadata)
    repo = CsvDataRepository(str(csv_path))
    assert repo.get_generation_time() is None
    assert len(repo.load()) == len(analytical_data)


def test_notebook_export_records_metadata_readable_by_app(tmp_path, analytical_data):
    notebook = json.loads((Path(__file__).resolve().parents[1] / 'notebooks/notebook_eda_dengue.ipynb').read_text())
    source = next(''.join(c.get('source', [])) for c in notebook['cells']
                  if 'df_analitica.to_csv(ARQ_BASE_ANALITICA, index=False)' in ''.join(c.get('source', [])))
    export = source[source.index('df_analitica.to_csv'):source.index('print(f"Base analítica final:')]
    csv_path = tmp_path / 'base.csv'
    before = pd.Timestamp.now(tz='UTC')
    exec(compile(export, 'notebook_metadata_export', 'exec'), {
        'df_analitica': analytical_data, 'ARQ_BASE_ANALITICA': str(csv_path),
    })
    generated_at = CsvDataRepository(str(csv_path)).get_generation_time()
    assert generated_at is not None
    assert before <= generated_at <= pd.Timestamp.now(tz='UTC')
