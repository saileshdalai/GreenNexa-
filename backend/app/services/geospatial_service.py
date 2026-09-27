"""
GreenNexa — Geospatial & Open-Data Context Service.

Provides regional climate, ambient weather proxies, and grid carbon emission
intensity factors. Transparently labeled as open-data benchmark proxies
to guarantee honesty and prevent ungrounded claims.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Regional benchmarks for grid carbon intensity (kg CO2 / kWh)
GRID_CARBON_FACTORS = {
    "default": 0.475,
    "north_america": 0.380,
    "europe": 0.230,
    "asia_pacific": 0.580,
    "india": 0.710,
    "uk": 0.190,
}


class GeospatialService:
    """
    Enriches facility telemetry with open-data environmental benchmarks.
    """

    def get_facility_context(
        self,
        organisation_id: str,
        facility_name: Optional[str] = None,
        region: str = "default",
    ) -> Dict[str, Any]:
        """
        Returns structured regional context, climate zone, and benchmark carbon factors.
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        month = now.month

        # Ambient diurnal proxy based on time of day
        ambient_temp = 24.0 + 7.0 * math.sin((hour - 9) * math.pi / 12.0)
        ambient_humidity = 65.0 - 15.0 * math.sin((hour - 9) * math.pi / 12.0)

        carbon_factor = GRID_CARBON_FACTORS.get(region.lower(), GRID_CARBON_FACTORS["default"])

        return {
            "organisation_id": organisation_id,
            "facility_name": facility_name or "Primary Facility Campus",
            "region": region,
            "climate_zone": "Subtropical / Humid",
            "data_classification": "open_data_benchmark_proxy",
            "disclaimer": "Weather and grid carbon factors are regional benchmark estimates for baseline contextualization.",
            "environmental_context": {
                "estimated_ambient_temperature_c": round(ambient_temp, 1),
                "estimated_ambient_humidity_pct": round(ambient_humidity, 1),
                "cooling_degree_demand": "HIGH" if ambient_temp > 28 else ("MODERATE" if ambient_temp > 22 else "LOW"),
                "grid_carbon_intensity_kg_per_kwh": carbon_factor,
            },
            "timestamp": now.isoformat(),
        }


geospatial_service = GeospatialService()
