from pathlib import Path
import numpy as np
import rasterio
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
import matplotlib
matplotlib.use("Agg")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {".tif", ".tiff", ".jp2"}

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTS

def compute_ndvi(src_path: Path) -> np.ndarray:
    with rasterio.open(src_path) as src:
        red = src.read(1).astype("float32")
        nir = src.read(4).astype("float32")
        nodata = src.nodata
        if nodata is not None:
            red = np.ma.masked_equal(red, nodata)
            nir = np.ma.masked_equal(nir, nodata)
        np.seterr(divide="ignore", invalid="ignore")
        ndvi = (nir - red) / (nir + red)
        return np.round(ndvi.filled(np.nan), 2)

def save_png(ndvi: np.ndarray, out_path: Path) -> None:
    norm = Normalize(vmin=-1, vmax=1)
    cmap = plt.get_cmap("RdYlGn")
    rgba = (cmap(norm(ndvi)) * 255).astype("uint8")
    plt.imsave(out_path, rgba)

def ndvi_to_protein(value: float) -> float:
    if value <= 0.0: return 0.0
    if value <= 0.33: return 6.0
    if value <= 0.66: return 12.0
    if value <= 1.0: return 18.0
    return np.nan

def polygon_mask(shape: tuple[int, int], vertices: list[list[float]]) -> np.ndarray:
    from matplotlib.path import Path as MplPath
    y_idx, x_idx = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]), indexing="ij")
    coords = np.column_stack((x_idx.ravel() + 0.5, y_idx.ravel() + 0.5))
    return MplPath(vertices).contains_points(coords).reshape(shape)

def average_protein(ndvi: np.ndarray, mask: np.ndarray) -> float:
    vals = ndvi[mask]
    vals = vals[~np.isnan(vals)]
    if vals.size == 0:
        return float("nan")
    proteins = [ndvi_to_protein(float(v)) for v in vals]
    proteins = [p for p in proteins if not np.isnan(p)]
    return float(np.mean(proteins)) if proteins else float("nan")
