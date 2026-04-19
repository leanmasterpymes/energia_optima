from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def load_generadores(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or DATA_DIR / "generadores.csv")
    df["es_renovable"] = df["es_renovable"].astype(bool)
    df["es_heredado"] = df["es_heredado"].astype(bool)
    return df


def load_demanda(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or DATA_DIR / "demanda.csv")


def load_precios_spot(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or DATA_DIR / "precios_spot.csv")
