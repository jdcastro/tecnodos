"""
Utilities to extract Web Mercator XYZ tiles from GeoTIFF rasters.

This module provides:
- ``tile_bounds_3857``: Compute the EPSG:3857 bounding box of a given
  XYZ tile (z, x, y).
- ``to_uint8``: Stretch a numeric 2-D array to 8-bit (0–255) using
  robust percentiles (2–98).
- ``tile_from_geotiff``: Read a GeoTIFF-like object, reproject on the
  fly to EPSG:3857, window the tile bounds, resample to a square tile,
  and return PNG bytes (RGB).

The functions are intended to support "slippy map" tile servers (e.g.,
Leaflet/Mapbox). The implementation uses Rasterio's ``WarpedVRT`` to
perform reprojection on demand and reads up to three bands to form RGB.
If the source has fewer than three bands, the first band is replicated
so a valid RGB PNG is always produced.

Notes
-----
- Bounds are computed in meters in EPSG:3857 using the standard spherical
  Web Mercator formulas, consistent with the XYZ tiling scheme where
  y=0 is at the top.
- Per-tile percentile stretching can improve local contrast but may lead
  to apparent brightness changes between adjacent tiles. For consistent
  appearance across tiles, consider using global per-band min/max.
- Resampling uses bilinear interpolation; for categorical rasters,
  nearest-neighbor is usually more appropriate.

Examples
--------
>>> tile_bounds_3857(0, 0, 0)
(-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244)
"""

from __future__ import annotations

import io
import math
from typing import BinaryIO, Tuple

import numpy as np
from PIL import Image
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds

__all__ = ["WEBMERC_MAX", "tile_bounds_3857", "to_uint8", "tile_from_geotiff"]

# Maximum projected extent for spherical Web Mercator (EPSG:3857), in meters.
WEBMERC_MAX: float = 20037508.342789244


def tile_bounds_3857(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """
    Compute the EPSG:3857 bounding box for an XYZ tile.

    Parameters
    ----------
    z : int
        Zoom level (>= 0).
    x : int
        Tile column (0 <= x < 2**z).
    y : int
        Tile row (0 <= y < 2**z), with 0 at the top (XYZ scheme).

    Returns
    -------
    tuple[float, float, float, float]
        (left, bottom, right, top) in meters in EPSG:3857.

    Notes
    -----
    The computation converts the tile indices to geographic lon/lat
    using the standard XYZ formulas, then maps lon/lat to Web Mercator
    (spherical) using:
        x = lon * WEBMERC_MAX / 180
        y = ln(tan(pi/4 + lat*pi/360)) * WEBMERC_MAX / pi
    """
    n = 2 ** z

    lon1 = x / n * 360.0 - 180.0
    lon2 = (x + 1) / n * 360.0 - 180.0

    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lat2 = math.degrees(
        math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    )

    def lonlat_to_merc(lon: float, lat: float) -> Tuple[float, float]:
        rad = math.pi / 180.0
        xm = lon * WEBMERC_MAX / 180.0
        ym = math.log(math.tan((90.0 + lat) * rad / 2.0)) * WEBMERC_MAX / math.pi
        return xm, ym

    x1, y1 = lonlat_to_merc(lon1, lat1)
    x2, y2 = lonlat_to_merc(lon2, lat2)

    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def to_uint8(arr: np.ndarray) -> np.ndarray:
    """
    Stretch a numeric 2-D array to 8-bit (0–255) using robust percentiles.

    This function replaces NaNs with 0, computes the 2nd and 98th percentiles
    as low/high anchors, performs a linear stretch to [0, 1], clips, and
    converts to uint8.

    Parameters
    ----------
    arr : numpy.ndarray
        2-D numeric array. NaNs are replaced with 0.

    Returns
    -------
    numpy.ndarray
        2-D array of dtype ``uint8`` with values in [0, 255]. If the input
        is empty (``arr.size == 0``), a 256x256 zero tile is returned.

    Notes
    -----
    - Percentile-based stretching improves local contrast and is robust
      to outliers. The 2–98 range is a common heuristic for imagery.
    - Because stretching is done per-tile, adjacent tiles can exhibit
      slight brightness differences. Use fixed/global ranges for uniform
      appearance if needed.
    """
    arr = np.nan_to_num(arr, nan=0.0)

    if arr.size == 0:
        return np.zeros((256, 256), dtype=np.uint8)

    mn, mx = np.percentile(arr, 2), np.percentile(arr, 98)
    if mx <= mn:
        mx = mn + 1.0

    out = (arr - mn) / (mx - mn)
    out = np.clip(out, 0.0, 1.0)

    return (out * 255).astype(np.uint8)


def tile_from_geotiff(
    fileobj: BinaryIO, z: int, x: int, y: int, tile_size: int = 256
) -> bytes:
    """
    Render an XYZ PNG tile (RGB) from a GeoTIFF-like file object.

    The function reads the raster from a binary file-like object,
    reprojects on the fly to EPSG:3857 using a ``WarpedVRT``, selects the
    window corresponding to the (z, x, y) tile bounds, resamples to a
    ``tile_size`` square, and returns PNG bytes.

    Parameters
    ----------
    fileobj : typing.BinaryIO
        A binary file-like object supporting ``read()`` that yields the
        full GeoTIFF content (e.g., an open file handle or an in-memory
        buffer).
    z : int
        Zoom level.
    x : int
        Tile column in XYZ.
    y : int
        Tile row in XYZ (0 at the top).
    tile_size : int, default 256
        Output tile width and height in pixels.

    Returns
    -------
    bytes
        PNG-encoded RGB image bytes of shape (tile_size, tile_size).

    Behavior
    --------
    - Up to the first three bands are read. If only one band is present,
      it is replicated across R, G, and B. If two bands are present,
      the first two are used and the first band is repeated for the
      third channel to complete RGB.
    - Each band is independently stretched to uint8 using 2–98
      percentiles via ``to_uint8``.
    - Reading is ``boundless=True`` with ``fill_value=0`` so tiles that
      fall partially (or fully) outside the source extent return black
      pixels rather than erroring.

    Raises
    ------
    This function intentionally catches exceptions during the window
    read and returns a black tile. Errors opening the dataset itself
    would still propagate if they occur before the read attempt.

    Notes
    -----
    - Resampling uses bilinear interpolation which is appropriate for
      continuous imagery. For categorical rasters, consider changing to
      ``Resampling.nearest``.
    - Creating a new ``WarpedVRT`` per call is simple but adds overhead.
      For high-throughput servers, consider caching the dataset/VRT and
      enabling overviews.
    """
    with rasterio.MemoryFile(fileobj.read()) as mem:
        with mem.open() as src:
            with WarpedVRT(src, crs="EPSG:3857", resampling=Resampling.bilinear) as vrt:
                left, bottom, right, top = tile_bounds_3857(z, x, y)
                window = from_bounds(left, bottom, right, top, vrt.transform)

                try:
                    count = min(3, vrt.count)
                    out = vrt.read(
                        indexes=list(range(1, count + 1)),
                        window=window,
                        out_shape=(count, tile_size, tile_size),
                        resampling=Resampling.bilinear,
                        boundless=True,
                        fill_value=0,
                    )
                except Exception:
                    out = np.zeros((3, tile_size, tile_size), dtype=np.uint8)

                if out.ndim == 2:
                    out = np.stack([out, out, out], axis=0)

                bands = [to_uint8(out[i]) for i in range(out.shape[0])]
                while len(bands) < 3:
                    bands.append(bands[0])

                rgb = np.stack(bands[:3], axis=2)

                img = Image.fromarray(rgb, mode="RGB")
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                buf.seek(0)
                return buf.read()
