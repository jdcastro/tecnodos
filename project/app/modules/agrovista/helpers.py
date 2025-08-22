from pathlib import Path
import tempfile
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

def compute_ndvi(src_path: Path) -> np.memmap:
    """Compute NDVI iterating over image blocks and store the result on disk.

    The returned object is a ``numpy.memmap`` backed by a temporary file so that
    very large rasters do not need to be fully loaded into RAM.
    """

    with rasterio.open(src_path) as src:
        shape = (src.height, src.width)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ndvi")
        ndvi = np.memmap(tmp.name, dtype="float32", mode="w+", shape=shape)

        nodata = src.nodata
        for _, window in src.block_windows(1):
            red = src.read(1, window=window).astype("float32")
            nir = src.read(4, window=window).astype("float32")
            if nodata is not None:
                red = np.ma.masked_equal(red, nodata)
                nir = np.ma.masked_equal(nir, nodata)
            with np.errstate(divide="ignore", invalid="ignore"):
                block = (nir - red) / (nir + red)
            if np.ma.isMaskedArray(block):
                block = block.filled(np.nan)
            r0, c0 = window.row_off, window.col_off
            ndvi[r0:r0 + window.height, c0:c0 + window.width] = np.round(block, 2)

        ndvi.flush()
        return ndvi

def save_png(ndvi: np.ndarray, out_path: Path) -> None:
    """Save a NDVI array (or memmap) as a PNG image."""

    if isinstance(ndvi, (str, Path)):
        ndvi = np.memmap(ndvi, dtype="float32", mode="r")

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
