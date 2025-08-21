"""Image processing utilities for Agrovista.

This module adapts the :class:`OrthoPhotoProcessor` from
``project/ejemplo/project/processor.py`` providing a small set of
vegetation indices and a qualitative assessment of nutrient status.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import cv2
import numpy as np
import rasterio


class ProcessorError(Exception):
    """Error raised when an image cannot be processed."""


class VegetationIndex:
    """Base class for vegetation index calculators."""

    NAME = "BASE"
    REQUIRES_NIR = False

    def compute(self, bands: Dict[str, np.ndarray]) -> np.ndarray:
        """Compute the index from the given bands."""
        raise NotImplementedError

    def _check_bands(self, bands: Dict[str, np.ndarray], required: List[str]) -> None:
        shape = None
        for key in required:
            if key not in bands:
                raise KeyError(f"Band '{key}' is required for {self.NAME}")
            if shape is None:
                shape = bands[key].shape
            elif bands[key].shape != shape:
                raise ValueError("Band dimensions do not match")


class VI_Impl(VegetationIndex):
    """Visible index: ``G / R``."""

    NAME = "VI"

    def compute(self, bands: Dict[str, np.ndarray]) -> np.ndarray:
        self._check_bands(bands, ["g", "r"])
        g, r = bands["g"], bands["r"]
        return np.divide(g, r, out=np.zeros_like(g, dtype=np.float64), where=r != 0, dtype=np.float64)


class GLI_Impl(VegetationIndex):
    """Green leaf index."""

    NAME = "GLI"

    def compute(self, bands: Dict[str, np.ndarray]) -> np.ndarray:
        self._check_bands(bands, ["g", "r", "b"])
        g, r, b = bands["g"], bands["r"], bands["b"]
        num = 2 * g - r - b
        den = 2 * g + r + b + 1e-10
        return np.divide(num, den, out=np.zeros_like(g, dtype=np.float64), where=den != 0, dtype=np.float64)


class VARI_Impl(VegetationIndex):
    """Visible atmospherically resistant index."""

    NAME = "VARI"

    def compute(self, bands: Dict[str, np.ndarray]) -> np.ndarray:
        self._check_bands(bands, ["g", "r", "b"])
        g, r, b = bands["g"], bands["r"], bands["b"]
        num = g - r
        den = g + r - b + 1e-10
        return np.divide(num, den, out=np.zeros_like(g, dtype=np.float64), where=den != 0, dtype=np.float64)


class VegetationIndexFactory:
    """Factory for vegetation index calculators."""

    _calculators: Dict[str, Type[VegetationIndex]] = {
        cls.NAME: cls for cls in (VI_Impl, GLI_Impl, VARI_Impl)
    }

    @staticmethod
    def get_calculator(name: str) -> Optional[VegetationIndex]:
        cls = VegetationIndexFactory._calculators.get(name.upper())
        return cls() if cls else None

    @staticmethod
    def get_available_indices() -> List[str]:
        return list(VegetationIndexFactory._calculators.keys())


@dataclass
class OrthoPhotoProcessor:
    """Compute vegetation indices from an orthophoto."""

    image_path: str
    processed_folder: Optional[str] = None

    def __post_init__(self) -> None:
        self.bands: Dict[str, np.ndarray] = {}
        self.calculated_indices: Dict[str, np.ndarray] = {}
        self._load_bands()
        self._compute_indices()

    # ------------------------------------------------------------------
    # Loading and computing
    def _load_bands(self) -> None:
        """Load RGB (and optionally NIR) bands from ``image_path``."""
        try:
            with rasterio.open(self.image_path) as src:
                self.bands["r"] = src.read(1).astype(np.float64)
                self.bands["g"] = src.read(2).astype(np.float64)
                self.bands["b"] = src.read(3).astype(np.float64)
                if src.count >= 4:
                    self.bands["nir"] = src.read(4).astype(np.float64)
        except Exception:
            image = cv2.imread(self.image_path, cv2.IMREAD_COLOR)
            if image is None:
                raise ProcessorError("unable to load image")
            b, g, r = cv2.split(image.astype(np.float64))
            self.bands.update({"b": b, "g": g, "r": r})

    def _compute_indices(self) -> None:
        for name in VegetationIndexFactory.get_available_indices():
            calc = VegetationIndexFactory.get_calculator(name)
            if calc and (not calc.REQUIRES_NIR or "nir" in self.bands):
                try:
                    self.calculated_indices[name] = calc.compute(self.bands)
                except Exception:
                    continue

    # ------------------------------------------------------------------
    # Utility methods
    def _normalize_for_display(self, data: np.ndarray) -> np.ndarray:
        norm_data = data.astype(np.float32)
        min_val = float(np.nanmin(norm_data))
        max_val = float(np.nanmax(norm_data))
        if np.isclose(max_val, min_val):
            return np.full(data.shape, 128, dtype=np.uint8)
        norm_data = (norm_data - min_val) / (max_val - min_val)
        norm_data = np.clip(norm_data, 0, 1)
        return (norm_data * 255).astype(np.uint8)

    def save_processed_image(self, data: np.ndarray, filename: str) -> str:
        """Save ``data`` as an image under ``filename``."""

        if not self.processed_folder:
            raise ProcessorError("processed folder not configured")
        output_path = os.path.join(self.processed_folder, filename)
        img = self._normalize_for_display(data)
        if not cv2.imwrite(output_path, img):
            raise ProcessorError(f"could not save {output_path}")
        return output_path

    def save_all_processed_images(self, photo_id: str) -> Dict[str, str]:
        """Save all computed indices as PNG images."""

        files: Dict[str, str] = {}
        for name, data in self.calculated_indices.items():
            filename = f"{name.lower()}_{photo_id}.png"
            path = self.save_processed_image(data, filename)
            files[name] = path
        return files

    def get_detailed_statistics(self) -> Dict[str, Dict[str, float]]:
        stats: Dict[str, Dict[str, float]] = {}
        for name, data in self.calculated_indices.items():
            valid = data[~np.isnan(data)]
            if valid.size == 0:
                continue
            stats[name] = {
                "min": float(np.min(valid)),
                "max": float(np.max(valid)),
                "mean": float(np.mean(valid)),
                "std": float(np.std(valid)),
            }
        return stats

    def assess_potential_nutrient_status(self) -> Dict[str, Any]:
        """Return a qualitative nutrient status assessment."""
        stats = self.get_detailed_statistics()
        avg_gli = stats.get("GLI", {}).get("mean", 0.0)
        avg_vari = stats.get("VARI", {}).get("mean", 0.0)
        overall = "Normal"
        issues: List[str] = []
        if avg_gli < 0.1 or avg_vari < 0.0:
            overall = "Potencialmente Deficiente"
            issues.append("Bajo vigor")
        return {
            "overall": overall,
            "statistics": stats,
            "potential_issues": issues,
        }

    def save_assessment(self, photo_id: str) -> str:
        """Persist assessment as a JSON file and return its path."""
        if not self.processed_folder:
            raise ProcessorError("processed folder not configured")
        path = os.path.join(self.processed_folder, f"{photo_id}_summary.json")
        data = self.assess_potential_nutrient_status()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path
