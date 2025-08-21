from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np

from .helpers import get_storage_and_path
from .services.indices import (
    compute_vari,
    load_rgb_from_bytes,
    mask_and_normalize_uint8,
    vari_to_protein_vector,
)


def compute_from_source(
    source: str,
    bbox: Optional[Sequence[int]] = None,
) -> Dict:
    storage, path = get_storage_and_path(source)
    data = storage.read_bytes(path)
    red, green, blue, nodata = load_rgb_from_bytes(data)
    red_n, green_n, blue_n = mask_and_normalize_uint8(red, green, blue, nodata)
    vari = compute_vari(green_n, red_n, blue_n)

    if bbox:
        xmin, ymin, xmax, ymax = [int(x) for x in bbox]
        xmin = max(0, xmin)
        ymin = max(0, ymin)
        xmax = min(vari.shape[1], max(xmin + 1, xmax))
        ymax = min(vari.shape[0], max(ymin + 1, ymax))
        vari = vari[ymin:ymax, xmin:xmax]

    subset = np.ma.masked_invalid(vari).compressed()
    if subset.size == 0:
        return {"count": 0, "mean_protein": None, "vari_stats": None}

    protein = vari_to_protein_vector(subset)
    protein = protein[~np.isnan(protein)]
    mean_protein = float(np.mean(protein)) if protein.size else None

    return {
        "count": int(subset.size),
        "mean_protein": mean_protein,
        "vari_stats": {
            "min": float(np.min(subset)),
            "max": float(np.max(subset)),
            "mean": float(np.mean(subset)),
        },
        "shape": (
            [int(vari.shape[0]), int(vari.shape[1])] if hasattr(vari, "shape") else None
        ),
    }
