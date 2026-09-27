"""
GreenNexa — ML Model Registry Service.

Provides persistence, versioning, metadata logging, and runtime caching
for scikit-learn anomaly detection and forecasting models using joblib.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib

logger = logging.getLogger(__name__)

REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "registry"


class ModelRegistry:
    """
    Manages saving, loading, metadata persistence, and in-memory caching
    for trained Machine Learning models in GreenNexa.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.registry_dir = base_dir or REGISTRY_DIR
        self._ensure_dir()
        self._memory_cache: Dict[str, Tuple[Any, Dict[str, Any]]] = {}

    def _ensure_dir(self) -> None:
        try:
            self.registry_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Could not create model registry directory %s: %s", self.registry_dir, e)

    def _get_model_path(self, model_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in model_id)
        return self.registry_dir / f"{safe_id}.joblib"

    def _get_meta_path(self, model_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in model_id)
        return self.registry_dir / f"{safe_id}.meta.json"

    def save_model(
        self,
        model: Any,
        model_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save a trained model and its associated metadata.
        """
        self._ensure_dir()
        meta = metadata.copy() if metadata else {}
        meta["model_id"] = model_id
        meta["saved_at"] = datetime.now(timezone.utc).isoformat()

        model_path = self._get_model_path(model_id)
        meta_path = self._get_meta_path(model_id)

        try:
            joblib.dump(model, model_path)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, default=str)

            self._memory_cache[model_id] = (model, meta)
            logger.info("Successfully persisted ML model %s to %s", model_id, model_path)
            return True
        except Exception as e:
            logger.error("Failed to persist model %s: %s", model_id, e, exc_info=True)
            return False

    def load_model(self, model_id: str) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """
        Load a trained model and its metadata by model_id.
        Uses in-memory cache if available.
        """
        if model_id in self._memory_cache:
            return self._memory_cache[model_id]

        model_path = self._get_model_path(model_id)
        meta_path = self._get_meta_path(model_id)

        if not model_path.exists():
            return None, None

        try:
            model = joblib.load(model_path)
            meta: Dict[str, Any] = {}
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

            self._memory_cache[model_id] = (model, meta)
            return model, meta
        except Exception as e:
            logger.warning("Error loading model %s: %s", model_id, e)
            return None, None

    def list_models(self, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered models and their metadata.
        """
        self._ensure_dir()
        models = []
        try:
            for meta_file in self.registry_dir.glob("*.meta.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if filter_type and meta.get("model_type") != filter_type:
                        continue
                    models.append(meta)
                except Exception as file_err:
                    logger.debug("Failed to read meta file %s: %s", meta_file, file_err)
        except Exception as e:
            logger.warning("Failed listing models in registry: %s", e)

        return sorted(models, key=lambda x: x.get("saved_at", ""), reverse=True)

    def delete_model(self, model_id: str) -> bool:
        """
        Remove a model and its metadata from the registry.
        """
        self._memory_cache.pop(model_id, None)
        model_path = self._get_model_path(model_id)
        meta_path = self._get_meta_path(model_id)
        deleted = False
        try:
            if model_path.exists():
                model_path.unlink()
                deleted = True
            if meta_path.exists():
                meta_path.unlink()
                deleted = True
        except Exception as e:
            logger.error("Error deleting model %s: %s", model_id, e)
        return deleted


model_registry = ModelRegistry()
