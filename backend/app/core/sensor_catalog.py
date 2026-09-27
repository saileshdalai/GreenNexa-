"""
GreenNexa — Centralized Master Sensor Catalog & Default Type Mappings.

Single Source of Truth for sensor definitions, default thresholds,
and organisation/facility type-specific recommended sensors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Master Sensor Catalog
# ---------------------------------------------------------------------------
MASTER_SENSOR_CATALOG: List[Dict[str, Any]] = [
    # CORE
    {
        "id": "energy",
        "name": "Energy",
        "category": "CORE",
        "metric": "Active Electrical Power",
        "unit": "kWh",
        "default_baseline": 1000.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (800.0, 1500.0),
        "anomaly_range": (1800.0, 2500.0),
        "description": "Total facility electrical power draw and cumulative energy consumption.",
    },
    {
        "id": "water",
        "name": "Water",
        "category": "CORE",
        "metric": "Water Consumption",
        "unit": "L",
        "default_baseline": 400.0,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (200.0, 600.0),
        "anomaly_range": (800.0, 1200.0),
        "description": "Mains potable water usage and cumulative fluid volume.",
    },
    {
        "id": "temperature",
        "name": "Temperature",
        "category": "CORE",
        "metric": "Ambient Temperature",
        "unit": "°C",
        "default_baseline": 24.0,
        "default_warn": 10.0,
        "default_crit": 20.0,
        "normal_range": (18.0, 32.0),
        "anomaly_range": (35.0, 45.0),
        "description": "Ambient dry-bulb environmental room and zone temperature.",
    },
    {
        "id": "humidity",
        "name": "Humidity",
        "category": "CORE",
        "metric": "Relative Humidity",
        "unit": "%",
        "default_baseline": 55.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (45.0, 70.0),
        "anomaly_range": (85.0, 98.0),
        "description": "Indoor air relative humidity percentage.",
    },
    {
        "id": "co2",
        "name": "CO2",
        "category": "CORE",
        "metric": "Carbon Dioxide Concentration",
        "unit": "ppm",
        "default_baseline": 600.0,
        "default_warn": 25.0,
        "default_crit": 50.0,
        "normal_range": (400.0, 900.0),
        "anomaly_range": (1400.0, 2200.0),
        "description": "Indoor air quality CO2 parts-per-million concentration.",
    },
    {
        "id": "waste",
        "name": "Waste",
        "category": "CORE",
        "metric": "Container Fill Level",
        "unit": "%",
        "default_baseline": 40.0,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (15.0, 75.0),
        "anomaly_range": (90.0, 100.0),
        "description": "Smart bin solid waste fill level percentage.",
    },

    # MUNICIPALITY / OUTDOOR
    {
        "id": "air_quality",
        "name": "Air Quality",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Air Quality Index (AQI)",
        "unit": "AQI",
        "default_baseline": 50.0,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (30.0, 80.0),
        "anomaly_range": (160.0, 320.0),
        "description": "Composite outdoor/indoor Air Quality Index rating.",
    },
    {
        "id": "traffic",
        "name": "Traffic",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Traffic Flow Volume",
        "unit": "veh/h",
        "default_baseline": 150.0,
        "default_warn": 25.0,
        "default_crit": 50.0,
        "normal_range": (80.0, 220.0),
        "anomaly_range": (350.0, 600.0),
        "description": "Corridor traffic throughput and congestion monitoring.",
    },
    {
        "id": "parking",
        "name": "Parking",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Parking Space Occupancy",
        "unit": "%",
        "default_baseline": 70.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (40.0, 85.0),
        "anomaly_range": (95.0, 100.0),
        "description": "Civic parking bay utilization and occupancy percentage.",
    },
    {
        "id": "water_flow",
        "name": "Water Flow",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Pipeline Flow Rate",
        "unit": "L/min",
        "default_baseline": 120.0,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (80.0, 160.0),
        "anomaly_range": (220.0, 350.0),
        "description": "Water main distribution flow rate.",
    },
    {
        "id": "water_level",
        "name": "Water Level",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Reservoir / Tank Level",
        "unit": "%",
        "default_baseline": 75.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (60.0, 90.0),
        "anomaly_range": (20.0, 35.0),
        "description": "Water overhead tank and distribution sump level percentage.",
    },
    {
        "id": "sewage_level",
        "name": "Sewage / Drainage Level",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Drainage Sump Level",
        "unit": "%",
        "default_baseline": 35.0,
        "default_warn": 25.0,
        "default_crit": 50.0,
        "normal_range": (20.0, 55.0),
        "anomaly_range": (85.0, 100.0),
        "description": "Stormwater drain and sewage sump fill level percentage.",
    },
    {
        "id": "rainfall",
        "name": "Rainfall",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Precipitation Rate",
        "unit": "mm",
        "default_baseline": 5.0,
        "default_warn": 50.0,
        "default_crit": 100.0,
        "normal_range": (0.0, 12.0),
        "anomaly_range": (45.0, 120.0),
        "description": "Precipitation gauge depth per hour.",
    },
    {
        "id": "street_lighting",
        "name": "Street Lighting",
        "category": "MUNICIPALITY / CIVIC",
        "metric": "Street Light Energy Consumption",
        "unit": "kWh",
        "default_baseline": 400.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (200.0, 900.0),
        "anomaly_range": (1200.0, 1800.0),
        "description": "Civic street light network energy draw across municipal zones.",
    },
    {
        "id": "roads",
        "name": "Roads",
        "category": "MUNICIPALITY / CIVIC",
        "metric": "Road Condition Index",
        "unit": "%",
        "default_baseline": 85.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (65.0, 98.0),
        "anomaly_range": (30.0, 60.0),
        "description": "Road surface health and maintenance condition index for municipal corridors.",
    },
    {
        "id": "parks",
        "name": "Parks",
        "category": "MUNICIPALITY / CIVIC",
        "metric": "Park Utilization / Health",
        "unit": "%",
        "default_baseline": 60.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (40.0, 90.0),
        "anomaly_range": (95.0, 100.0),
        "description": "Playground and community park health, cleanliness and utilization level.",
    },
    {
        "id": "sewage",
        "name": "Sewage",
        "category": "MUNICIPALITY / CIVIC",
        "metric": "Sewage & Drainage Network Level",
        "unit": "%",
        "default_baseline": 40.0,
        "default_warn": 25.0,
        "default_crit": 50.0,
        "normal_range": (20.0, 60.0),
        "anomaly_range": (85.0, 100.0),
        "description": "Civic sewage and drainage network fill pressure/level.",
    },

    # ASSET / UTILISATION
    {
        "id": "equipment_asset",
        "name": "Equipment / Asset",
        "category": "ASSET / UTILISATION",
        "metric": "Asset Health Score",
        "unit": "%",
        "default_baseline": 95.0,
        "default_warn": 10.0,
        "default_crit": 20.0,
        "normal_range": (88.0, 100.0),
        "anomaly_range": (50.0, 75.0),
        "description": "Operational health, availability, and uptime efficiency of machinery.",
    },
    {
        "id": "occupancy",
        "name": "Occupancy",
        "category": "ASSET / UTILISATION",
        "metric": "Space Utilization Rate",
        "unit": "%",
        "default_baseline": 65.0,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (35.0, 80.0),
        "anomaly_range": (95.0, 100.0),
        "description": "Footfall counter and space capacity utilization percentage.",
    },

    # INDUSTRIAL
    {
        "id": "vibration",
        "name": "Vibration",
        "category": "INDUSTRIAL",
        "metric": "RMS Vibration Velocity",
        "unit": "mm/s",
        "default_baseline": 2.5,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (1.2, 3.5),
        "anomaly_range": (5.5, 9.8),
        "description": "Motor and pump rotational vibration velocity.",
    },
    {
        "id": "pressure",
        "name": "Pressure",
        "category": "INDUSTRIAL",
        "metric": "System Fluid Pressure",
        "unit": "bar",
        "default_baseline": 6.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (4.5, 7.5),
        "anomaly_range": (9.0, 13.5),
        "description": "Hydraulic or pneumatic line gauge pressure.",
    },
    {
        "id": "flow",
        "name": "Flow",
        "category": "INDUSTRIAL",
        "metric": "Process Flow Rate",
        "unit": "L/min",
        "default_baseline": 100.0,
        "default_warn": 20.0,
        "default_crit": 40.0,
        "normal_range": (70.0, 130.0),
        "anomaly_range": (180.0, 260.0),
        "description": "Industrial coolant or chemical dosing line flow.",
    },
    {
        "id": "current_voltage",
        "name": "Current / Voltage",
        "category": "INDUSTRIAL",
        "metric": "Phase Voltage / Current",
        "unit": "A",
        "default_baseline": 415.0,
        "default_warn": 10.0,
        "default_crit": 20.0,
        "normal_range": (380.0, 440.0),
        "anomaly_range": (470.0, 520.0),
        "description": "Three-phase electric feeder line voltage and phase current.",
    },
    {
        "id": "rpm",
        "name": "RPM",
        "category": "INDUSTRIAL",
        "metric": "Rotational Speed",
        "unit": "RPM",
        "default_baseline": 1450.0,
        "default_warn": 10.0,
        "default_crit": 25.0,
        "normal_range": (1380.0, 1520.0),
        "anomaly_range": (1680.0, 1950.0),
        "description": "Shaft tachometer revolutions per minute.",
    },
    {
        "id": "machine_temperature",
        "name": "Machine Temperature",
        "category": "INDUSTRIAL",
        "metric": "Bearing Temperature",
        "unit": "°C",
        "default_baseline": 65.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (50.0, 75.0),
        "anomaly_range": (90.0, 125.0),
        "description": "Equipment motor casing and bearing temperature.",
    },
    {
        "id": "runtime_hours",
        "name": "Runtime / Operating Hours",
        "category": "INDUSTRIAL",
        "metric": "Operating Hours Counter",
        "unit": "hrs",
        "default_baseline": 16.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (8.0, 20.0),
        "anomaly_range": (23.5, 24.0),
        "description": "Cumulative continuous machine duty hours per cycle.",
    },
    {
        "id": "acoustic_sound",
        "name": "Acoustic / Sound",
        "category": "INDUSTRIAL",
        "metric": "Acoustic Sound Pressure",
        "unit": "dB",
        "default_baseline": 68.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (55.0, 78.0),
        "anomaly_range": (92.0, 115.0),
        "description": "Decibel sound intensity and bearing noise monitor.",
    },
    {
        "id": "gas",
        "name": "Gas",
        "category": "INDUSTRIAL",
        "metric": "Hazardous Gas Level",
        "unit": "ppm",
        "default_baseline": 10.0,
        "default_warn": 30.0,
        "default_crit": 60.0,
        "normal_range": (2.0, 15.0),
        "anomaly_range": (35.0, 80.0),
        "description": "Toxic gas / methane / VOC concentration ppm.",
    },
    {
        "id": "dust_pm",
        "name": "Dust / PM",
        "category": "INDUSTRIAL",
        "metric": "Particulate Matter PM10",
        "unit": "µg/m³",
        "default_baseline": 45.0,
        "default_warn": 25.0,
        "default_crit": 50.0,
        "normal_range": (20.0, 60.0),
        "anomaly_range": (120.0, 250.0),
        "description": "Industrial workshop dust and suspended particulate monitor.",
    },
    {
        "id": "fire_smoke",
        "name": "Fire / Smoke",
        "category": "INDUSTRIAL",
        "metric": "Optical Smoke Obscuration",
        "unit": "idx",
        "default_baseline": 2.0,
        "default_warn": 50.0,
        "default_crit": 100.0,
        "normal_range": (0.0, 4.0),
        "anomaly_range": (15.0, 40.0),
        "description": "Early detection optical obscuration index.",
    },
    {
        "id": "oil_fluid_level",
        "name": "Oil / Fluid Level",
        "category": "INDUSTRIAL",
        "metric": "Lube Oil Reservoir Level",
        "unit": "%",
        "default_baseline": 85.0,
        "default_warn": 15.0,
        "default_crit": 30.0,
        "normal_range": (70.0, 95.0),
        "anomaly_range": (25.0, 45.0),
        "description": "Hydraulic / lubricant sump level percentage.",
    },

    # Legacy compatibility sensors
    {
        "id": "assets",
        "name": "Assets (Legacy)",
        "category": "ASSET / UTILISATION",
        "metric": "Asset Availability",
        "unit": "%",
        "default_baseline": 95.0,
        "default_warn": 10.0,
        "default_crit": 20.0,
        "normal_range": (85.0, 100.0),
        "anomaly_range": (50.0, 70.0),
        "description": "Legacy asset tracking module.",
    },
    {
        "id": "safety",
        "name": "Safety",
        "category": "CORE",
        "metric": "Safety Compliance Index",
        "unit": "%",
        "default_baseline": 98.0,
        "default_warn": 5.0,
        "default_crit": 10.0,
        "normal_range": (92.0, 100.0),
        "anomaly_range": (75.0, 85.0),
        "description": "Operational safety and emergency readiness score.",
    },
    {
        "id": "climate",
        "name": "Climate",
        "category": "MUNICIPALITY / OUTDOOR",
        "metric": "Microclimate Temperature",
        "unit": "°C",
        "default_baseline": 25.0,
        "default_warn": 10.0,
        "default_crit": 20.0,
        "normal_range": (20.0, 30.0),
        "anomaly_range": (36.0, 44.0),
        "description": "Facility microclimate sensor indicator.",
    },
]

# Quick lookup by sensor id
SENSOR_CATALOG_MAP: Dict[str, Dict[str, Any]] = {s["id"]: s for s in MASTER_SENSOR_CATALOG}


# ---------------------------------------------------------------------------
# Default Recommended Sensors per Organisation / Facility Type
# ---------------------------------------------------------------------------
RECOMMENDED_SENSORS_BY_TYPE: Dict[str, List[str]] = {
    # 1. Hospital
    "hospital": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "temperature",
        "humidity",
        "equipment_asset",
        "occupancy",
        "safety",
    ],
    # 2. School
    "school": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "temperature",
        "humidity",
        "occupancy",
        "safety",
    ],
    # 3. College / University
    "college": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "temperature",
        "humidity",
        "equipment_asset",
        "occupancy",
        "parking",
        "safety",
    ],
    # 4. Ward Office
    "ward_office": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "occupancy",
        "safety",
    ],
    # 5. Water Pump Station
    "water_pump_station": [
        "energy",
        "water",
        "water_flow",
        "water_level",
        "sewage_level",
        "equipment_asset",
        "pressure",
        "flow",
        "vibration",
        "machine_temperature",
        "safety",
    ],
    # 6. Municipal Office
    "municipal_office": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "occupancy",
        "parking",
        "safety",
    ],
    # 7. Community Facility
    "community_facility": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "temperature",
        "humidity",
        "occupancy",
        "safety",
    ],
    # 8. Municipality
    "municipality": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "temperature",
        "humidity",
        "water_flow",
        "water_level",
        "sewage_level",
        "rainfall",
        "traffic",
        "parking",
        "safety",
        "street_lighting",
        "roads",
        "parks",
        "sewage",
    ],
    # 9. Industrial Organisation
    "industrial": [
        "energy",
        "water",
        "waste",
        "air_quality",
        "vibration",
        "pressure",
        "flow",
        "current_voltage",
        "rpm",
        "machine_temperature",
        "runtime_hours",
        "acoustic_sound",
        "gas",
        "dust_pm",
        "fire_smoke",
        "oil_fluid_level",
        "safety",
    ],
    # 10. Park / Community Park
    "park": [
        "energy",
        "water",
        "water_flow",
        "air_quality",
        "rainfall",
        "temperature",
        "humidity",
        "safety",
    ],
}


def normalize_type_key(org_type: Optional[str]) -> str:
    """Normalize user-entered or DB organisation/facility type into a catalog key."""
    if not org_type:
        return "community_facility"
    t = org_type.lower().strip()
    if "municipality" in t:
        return "municipality"
    if "hospital" in t or "health" in t:
        return "hospital"
    if "school" in t:
        return "school"
    if "college" in t or "universit" in t:
        return "college"
    if "ward" in t:
        return "ward_office"
    if "pump" in t:
        return "water_pump_station"
    if "municipal office" in t:
        return "municipal_office"
    if "industrial" in t or "manufactur" in t:
        return "industrial"
    if "park" in t:
        return "park"
    if "community" in t:
        return "community_facility"
    return "community_facility"


def get_recommended_sensors_for_type(org_type: Optional[str]) -> List[str]:
    """Return default recommended sensor IDs for a given organisation or facility type."""
    key = normalize_type_key(org_type)
    return list(RECOMMENDED_SENSORS_BY_TYPE.get(key, RECOMMENDED_SENSORS_BY_TYPE["community_facility"]))


def get_default_configs_for_sensors(sensor_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Generate default baseline/warning/critical settings dict for given sensor IDs."""
    res = {}
    for sid in sensor_ids:
        c = SENSOR_CATALOG_MAP.get(sid)
        if c:
            res[sid] = {
                "baseline": c["default_baseline"],
                "warning_threshold": c["default_warn"],
                "critical_threshold": c["default_crit"],
                "unit": c["unit"],
            }
        else:
            res[sid] = {
                "baseline": 100.0,
                "warning_threshold": 15.0,
                "critical_threshold": 30.0,
                "unit": "",
            }
    return res
