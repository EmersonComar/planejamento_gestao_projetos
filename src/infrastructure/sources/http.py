"""Requisições HTTP com novas tentativas e download com cache local."""
from __future__ import annotations

import time
from pathlib import Path

import requests

USER_AGENT = "Mozilla/5.0 (compatible; dengue-sc-painel)"
TIMEOUT = 60


def get(url: str, params: dict | None = None, attempts: int = 3, timeout: int = TIMEOUT) -> requests.Response:
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == attempts:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError("inalcançável")


def get_json(url: str, params: dict | None = None, **kwargs):
    return get(url, params=params, **kwargs).json()


def download(url: str, destination: Path, force: bool = False, validate=None) -> Path:
    """Baixa ``url`` para ``destination`` se ainda não existir (ou se ``force``)."""
    destination = Path(destination)
    if destination.exists() and not force and (validate is None or validate(destination)):
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".parcial")
    with requests.get(url, stream=True, timeout=300, headers={"User-Agent": USER_AGENT}) as response:
        response.raise_for_status()
        with partial.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1 << 20):
                file.write(chunk)
    partial.replace(destination)
    if validate is not None and not validate(destination):
        raise ValueError(f"Arquivo baixado inválido: {destination}")
    return destination
