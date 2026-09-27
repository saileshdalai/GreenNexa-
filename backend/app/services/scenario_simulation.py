"""
GreenNexa — Counterfactual What-If Scenario Simulation Service.

Provides deterministic, grounded simulation of operational facility changes
(thermostat adjustments, AC run hours, solar PV generation, water conservation,
waste route optimization, traffic shifting) using real baseline telemetry
and Indian institutional energy/water benchmarks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.db.models import OrganisationSensorConfig, SensorReading
from app.services.forecasting import forecasting_service

logger = logging.getLogger(__name__)

# Standard Indian Institutional Operational Benchmarks
COMMERCIAL_TARIFF_INR_PER_KWH = 8.50  # Average commercial/institutional grid tariff in India (₹/kWh)
GRID_EMISSION_FACTOR_KG_CO2_PER_KWH = 0.82  # CEA India national grid average (kg CO2/kWh)
WATER_TARIFF_INR_PER_KL = 45.0  # Typical institutional municipal water tariff (₹/1,000 Liters)


class ScenarioSimulationService:
    """
    Simulates operational decisions and returns grounded counterfactual estimates.
    """

    def _get_metric_baseline(
        self,
        db: Session,
        organisation_id: str,
        metric: str,
        horizon_hours: int = 24,
    ) -> float:
        """
        Derive empirical 24h baseline load from live ML forecast, recent telemetry, or sensor config.
        """
        # Try to use 24h forecast sum if available
        if metric in ("energy", "water"):
            try:
                fc = forecasting_service.get_forecast(db, organisation_id, metric, horizon="24h")
                if fc and fc.forecast:
                    hourly_preds = [p.predicted_value for p in fc.forecast]
                    avg_hourly = sum(hourly_preds) / len(hourly_preds)
                    return float(avg_hourly * horizon_hours)
            except Exception as e:
                logger.debug("Forecast baseline lookup fallback: %s", e)

        # Fallback to recent telemetry average
        readings = (
            db.query(SensorReading.value)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == metric,
            )
            .order_by(SensorReading.timestamp.desc())
            .limit(24)
            .all()
        )
        if readings:
            vals = [r[0] for r in readings if r[0] is not None]
            if vals:
                return float((sum(vals) / len(vals)) * horizon_hours)

        # Fallback to config baseline
        config = db.query(OrganisationSensorConfig).filter_by(organisation_id=organisation_id).first()
        cfg_dict = config.sensor_configs_dict if config else {}
        metric_cfg = cfg_dict.get(metric, {})
        default_baseline = 120.0 if metric == "energy" else (800.0 if metric == "water" else 50.0)
        baseline_hourly = metric_cfg.get("baseline", default_baseline)
        return float(baseline_hourly * horizon_hours)

    def run_energy_scenario(
        self,
        db: Session,
        organisation_id: str,
        ac_hours_reduced: float = 0.0,
        thermostat_temp_increase_c: float = 0.0,
        solar_offset_pct: float = 0.0,
        occupancy_change_pct: float = 0.0,
        led_retrofit_pct: float = 0.0,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Simulate energy savings for operational HVAC, solar, and lighting adjustments.
        """
        baseline_kwh = self._get_metric_baseline(db, organisation_id, "energy", horizon_hours)

        hvac_share = 0.50
        lighting_share = 0.18

        assumptions: List[str] = []
        reduction_kwh = 0.0

        # 1. AC hours reduction
        if ac_hours_reduced > 0:
            daily_ac_op_hours = 10.0
            ac_factor = min(ac_hours_reduced / daily_ac_op_hours, 1.0)
            ac_savings = (baseline_kwh * hvac_share) * ac_factor
            reduction_kwh += ac_savings
            assumptions.append(
                f"Reducing AC operation by {ac_hours_reduced:.1f}h saves ~{ac_savings:.1f} kWh "
                f"(assuming 10h baseline daily chiller/split AC schedule at 50% campus load share)."
            )

        # 2. Thermostat setpoint increase
        if thermostat_temp_increase_c > 0:
            temp_factor = min(thermostat_temp_increase_c * 0.06, 0.35)
            temp_savings = (baseline_kwh * hvac_share) * temp_factor
            reduction_kwh += temp_savings
            assumptions.append(
                f"Raising cooling setpoint by +{thermostat_temp_increase_c:.1f}°C yields a "
                f"{thermostat_temp_increase_c * 6:.1f}% reduction in HVAC draw (~{temp_savings:.1f} kWh) per BEE guidelines."
            )

        # 3. Solar PV offset
        if solar_offset_pct > 0:
            solar_pct = min(solar_offset_pct, 100.0) / 100.0
            solar_savings = baseline_kwh * solar_pct
            reduction_kwh += solar_savings
            assumptions.append(
                f"Rooftop solar PV generation offsets {solar_offset_pct:.1f}% of grid draw (~{solar_savings:.1f} kWh)."
            )

        # 4. LED retrofit
        if led_retrofit_pct > 0:
            led_pct = min(led_retrofit_pct, 100.0) / 100.0
            led_savings = (baseline_kwh * lighting_share) * led_pct * 0.50
            reduction_kwh += led_savings
            assumptions.append(
                f"LED fixture retrofit across {led_retrofit_pct:.1f}% of fixtures saves ~{led_savings:.1f} kWh."
            )

        # 5. Occupancy change
        if occupancy_change_pct != 0:
            occ_delta = (baseline_kwh * 0.40) * (occupancy_change_pct / 100.0)
            reduction_kwh -= occ_delta
            assumptions.append(
                f"Occupancy change of {occupancy_change_pct:+.1f}% impacts variable loads by {occ_delta:+.1f} kWh."
            )

        reduction_kwh = max(min(reduction_kwh, baseline_kwh * 0.85), -baseline_kwh * 0.50)
        projected_kwh = round(baseline_kwh - reduction_kwh, 2)
        saved_kwh = round(reduction_kwh, 2)
        saved_pct = round((saved_kwh / baseline_kwh) * 100.0, 1) if baseline_kwh > 0 else 0.0

        cost_savings_inr = round(saved_kwh * COMMERCIAL_TARIFF_INR_PER_KWH, 2)
        co2_avoided_kg = round(saved_kwh * GRID_EMISSION_FACTOR_KG_CO2_PER_KWH, 2)

        return {
            "scenario": "energy",
            "is_modelled_estimate": True,
            "horizon_hours": horizon_hours,
            "baseline_consumption": round(baseline_kwh, 2),
            "projected_consumption": projected_kwh,
            "net_savings": saved_kwh,
            "savings_percentage": saved_pct,
            "unit": "kWh",
            "estimated_cost_savings_inr": cost_savings_inr,
            "co2_avoided_kg": co2_avoided_kg,
            "parameters_applied": {
                "ac_hours_reduced": ac_hours_reduced,
                "thermostat_temp_increase_c": thermostat_temp_increase_c,
                "solar_offset_pct": solar_offset_pct,
                "occupancy_change_pct": occupancy_change_pct,
                "led_retrofit_pct": led_retrofit_pct,
            },
            "assumptions": assumptions or ["Standard operational schedule without structural modifications."],
            "disclaimer": "Decision-support estimate based on GreenNexa historical telemetry and BEE India benchmarks.",
        }

    def run_water_scenario(
        self,
        db: Session,
        organisation_id: str,
        water_reduction_pct: float = 0.0,
        rainwater_harvest_liters: float = 0.0,
        low_flow_fixture_adoption_pct: float = 0.0,
        irrigation_scheduling_hours: float = 0.0,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Simulate water savings for conservation targets, rainwater harvesting, or low-flow fittings.
        """
        baseline_liters = self._get_metric_baseline(db, organisation_id, "water", horizon_hours)

        assumptions: List[str] = []
        reduction_liters = 0.0

        if water_reduction_pct > 0:
            target_pct = min(water_reduction_pct, 100.0) / 100.0
            r_liters = baseline_liters * target_pct
            reduction_liters += r_liters
            assumptions.append(
                f"Facility-wide conservation initiative targets a {water_reduction_pct:.1f}% reduction (~{r_liters:.1f} L)."
            )

        if rainwater_harvest_liters > 0:
            reduction_liters += rainwater_harvest_liters
            assumptions.append(
                f"Rainwater harvesting / reclaimed greywater offsets {rainwater_harvest_liters:.1f} L of municipal draw."
            )

        if low_flow_fixture_adoption_pct > 0:
            fixture_pct = min(low_flow_fixture_adoption_pct, 100.0) / 100.0
            fixture_savings = (baseline_liters * 0.45) * fixture_pct * 0.30
            reduction_liters += fixture_savings
            assumptions.append(
                f"Low-flow aerator fittings on {low_flow_fixture_adoption_pct:.1f}% of taps saves ~{fixture_savings:.1f} L."
            )

        if irrigation_scheduling_hours > 0:
            irrigation_savings = (baseline_liters * 0.15) * 0.25
            reduction_liters += irrigation_savings
            assumptions.append(
                f"Evening smart irrigation scheduling curtails evaporative loss, saving ~{irrigation_savings:.1f} L."
            )

        reduction_liters = max(min(reduction_liters, baseline_liters * 0.90), 0.0)
        projected_liters = round(baseline_liters - reduction_liters, 2)
        saved_liters = round(reduction_liters, 2)
        saved_pct = round((saved_liters / baseline_liters) * 100.0, 1) if baseline_liters > 0 else 0.0
        cost_savings_inr = round((saved_liters / 1000.0) * WATER_TARIFF_INR_PER_KL, 2)

        return {
            "scenario": "water",
            "is_modelled_estimate": True,
            "horizon_hours": horizon_hours,
            "baseline_consumption": round(baseline_liters, 2),
            "projected_consumption": projected_liters,
            "net_savings": saved_liters,
            "savings_percentage": saved_pct,
            "unit": "L",
            "estimated_cost_savings_inr": cost_savings_inr,
            "parameters_applied": {
                "water_reduction_pct": water_reduction_pct,
                "rainwater_harvest_liters": rainwater_harvest_liters,
                "low_flow_fixture_adoption_pct": low_flow_fixture_adoption_pct,
                "irrigation_scheduling_hours": irrigation_scheduling_hours,
            },
            "assumptions": assumptions or ["Standard water distribution across plumbing loops."],
            "disclaimer": "Decision-support estimate based on GreenNexa telemetry and CPWD water norms.",
        }

    def run_waste_scenario(
        self,
        db: Session,
        organisation_id: str,
        collection_route_optimization_pct: float = 0.0,
        recycling_rate_increase_pct: float = 0.0,
        compactor_installation: bool = False,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Simulate waste fill, bin overflow mitigation, and landfill diversion.
        """
        baseline_kg = self._get_metric_baseline(db, organisation_id, "waste", horizon_hours)

        assumptions: List[str] = []
        diverted_kg = 0.0

        if recycling_rate_increase_pct > 0:
            rec_pct = min(recycling_rate_increase_pct, 100.0) / 100.0
            rec_kg = baseline_kg * rec_pct * 0.40
            diverted_kg += rec_kg
            assumptions.append(
                f"Source segregation and compost/recycling diversion keeps ~{rec_kg:.1f} kg out of municipal landfill."
            )

        overflow_risk_reduction_pct = 0.0
        if collection_route_optimization_pct > 0:
            overflow_risk_reduction_pct = min(collection_route_optimization_pct * 0.8, 85.0)
            assumptions.append(
                f"Dynamic sensor-triggered bin clearance reduces peak overflow probability by ~{overflow_risk_reduction_pct:.1f}%."
            )

        if compactor_installation:
            assumptions.append("Smart solar compactor reduces bin pickup trip frequency by a factor of 4x.")

        projected_landfill_kg = round(max(baseline_kg - diverted_kg, 0.0), 2)
        saved_pct = round((diverted_kg / baseline_kg) * 100.0, 1) if baseline_kg > 0 else 0.0

        return {
            "scenario": "waste",
            "is_modelled_estimate": True,
            "horizon_hours": horizon_hours,
            "baseline_generation": round(baseline_kg, 2),
            "projected_landfill_waste": projected_landfill_kg,
            "diverted_waste": round(diverted_kg, 2),
            "diversion_percentage": saved_pct,
            "overflow_risk_reduction_pct": round(overflow_risk_reduction_pct, 1),
            "unit": "kg",
            "parameters_applied": {
                "collection_route_optimization_pct": collection_route_optimization_pct,
                "recycling_rate_increase_pct": recycling_rate_increase_pct,
                "compactor_installation": compactor_installation,
            },
            "assumptions": assumptions or ["Standard uncompacted waste bins with manual clearance."],
            "disclaimer": "Decision-support estimate based on SWM Rules 2016 and GreenNexa fill telemetry.",
        }

    def run_traffic_scenario(
        self,
        db: Session,
        organisation_id: str,
        shuttle_frequency_increase_pct: float = 0.0,
        carpool_incentive_adoption_pct: float = 0.0,
        staggered_shifts_pct: float = 0.0,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Simulate traffic bottleneck easing, parking bay occupancy relief, and emissions mitigation.
        """
        baseline_vehicles = self._get_metric_baseline(db, organisation_id, "traffic", horizon_hours)

        assumptions: List[str] = []
        reduction_vehicles = 0.0

        if shuttle_frequency_increase_pct > 0:
            shuttle_pct = min(shuttle_frequency_increase_pct, 100.0) / 100.0
            shuttle_relief = baseline_vehicles * (shuttle_pct * 0.15)
            reduction_vehicles += shuttle_relief
            assumptions.append(
                f"Increased feeder electric shuttle frequency diverts ~{shuttle_relief:.0f} private vehicle trips."
            )

        if carpool_incentive_adoption_pct > 0:
            carpool_pct = min(carpool_incentive_adoption_pct, 100.0) / 100.0
            carpool_relief = baseline_vehicles * (carpool_pct * 0.12)
            reduction_vehicles += carpool_relief
            assumptions.append(
                f"Reserved carpool parking and rideshare incentives lower campus entry gate volume by ~{carpool_relief:.0f} vehicles."
            )

        peak_congestion_reduction_pct = 0.0
        if staggered_shifts_pct > 0:
            peak_congestion_reduction_pct = min(staggered_shifts_pct * 0.75, 50.0)
            assumptions.append(
                f"Staggering start/end times across departments flattens gate surge queues by ~{peak_congestion_reduction_pct:.1f}%."
            )

        reduction_vehicles = min(reduction_vehicles, baseline_vehicles * 0.60)
        projected_vehicles = round(max(baseline_vehicles - reduction_vehicles, 0.0), 0)
        relief_pct = round((reduction_vehicles / baseline_vehicles) * 100.0, 1) if baseline_vehicles > 0 else 0.0
        co2_avoided_kg = round(reduction_vehicles * 2.4, 2)

        return {
            "scenario": "traffic",
            "is_modelled_estimate": True,
            "horizon_hours": horizon_hours,
            "baseline_vehicle_volume": round(baseline_vehicles, 0),
            "projected_vehicle_volume": projected_vehicles,
            "vehicles_diverted": round(reduction_vehicles, 0),
            "traffic_reduction_pct": relief_pct,
            "peak_congestion_reduction_pct": round(peak_congestion_reduction_pct, 1),
            "co2_avoided_kg": co2_avoided_kg,
            "unit": "vehicles",
            "parameters_applied": {
                "shuttle_frequency_increase_pct": shuttle_frequency_increase_pct,
                "carpool_incentive_adoption_pct": carpool_incentive_adoption_pct,
                "staggered_shifts_pct": staggered_shifts_pct,
            },
            "assumptions": assumptions or ["Standard private car and two-wheeler modal split."],
            "disclaimer": "Decision-support estimate based on campus gate telemetry and modal split models.",
        }


scenario_simulation_service = ScenarioSimulationService()
