from pathlib import Path
import json
import numpy as np
import rasterio
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
import matplotlib
matplotlib.use("Agg")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_FILE = DATA_DIR / "indices.json"
RESULTS: dict[str, object] = {}


def _save_results() -> None:
    with RESULTS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh)


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
        # Avoid divide-by-zero and invalid warnings during the NDVI calculation
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = (nir - red) / (nir + red)

        # ``ndvi`` is a plain ``ndarray`` when the source image has no nodata
        # values. Calling ``filled`` on such arrays raises ``AttributeError``
        # which previously bubbled up and resulted in a 500 error during file
        # uploads. Handle both masked and unmasked arrays gracefully.
        if np.ma.isMaskedArray(ndvi):
            ndvi = ndvi.filled(np.nan)

        return np.round(ndvi, 2)

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


def calculate_vi() -> list[float]:
    """Estimate the Vegetation Index (VI) from multispectral data.

    A production version would use the green and red bands of an image and
    compute ``(green - red) / (green + red)`` for each pixel.

    Returns:
        list[float]: Example VI values.
    """

    vi_values = [0.21, 0.48, 0.65]
    RESULTS["vi"] = vi_values
    _save_results()
    return vi_values


def calculate_gli() -> list[float]:
    """Calculate the Green Leaf Index (GLI) from RGB bands.

    GLI is typically ``(2 * G - R - B) / (2 * G + R + B)`` and highlights
    vegetation vigor from true-color imagery.

    Returns:
        list[float]: Example GLI values.
    """

    gli_values = [0.10, 0.37, 0.58]
    RESULTS["gli"] = gli_values
    _save_results()
    return gli_values


def calculate_vari() -> list[float]:
    """Derive the Visible Atmospherically Resistant Index (VARI).

    VARI is computed as ``(G - R) / (G + R - B)`` to reduce atmospheric
    influence when using RGB images.

    Returns:
        list[float]: Example VARI values.
    """

    vari_values = [0.05, 0.22, 0.41]
    RESULTS["vari"] = vari_values
    _save_results()
    return vari_values


def generate_deficiency_report() -> dict:
    """Generate a nutrient deficiency report from vegetation indices.

    In a real scenario, thresholds on VI, GLI and VARI would be analysed to
    detect possible nutrient issues (e.g. nitrogen or potassium shortages).

    Returns:
        dict: Example report of nutrient statuses.
    """

    report = {
        "nitrogen": "low",
        "phosphorus": "adequate",
        "potassium": "high",
    }
    RESULTS["deficiency_report"] = report
    _save_results()
    return report
