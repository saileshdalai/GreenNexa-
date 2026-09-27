"""
GreenNexa — Gemini Assistant Tools Factory.

Builds tenant-scoped, role-isolated Python callable functions that the Google
Gemini API invokes via Automatic Function Calling (AFC).

Guarantees that:
1. ADMIN users can only retrieve telemetry and run scenarios within their own organisation.
2. SUPER_ADMIN users receive platform aggregation tools if in platform scope.
3. What-If counterfactual scenario calculations are grounded in real telemetry/forecasts.
4. Gemini NEVER fabricates telemetry numbers — all values originate from GreenNexa backend.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.orm import Session

from app.ai.assistant.tools import GreenNexaDataTools
from app.services.scenario_simulation import scenario_simulation_service

logger = logging.getLogger(__name__)


def build_gemini_tools(
    db: Session,
    effective_org_id: Optional[str],
    is_super_admin: bool = False,
) -> List[Callable[..., Any]]:
    """
    Construct a list of scoped Python callable tools for Gemini.
    """
    tools: List[Callable[..., Any]] = []

    if effective_org_id:
        org_id = effective_org_id

        def get_current_metrics(metric: str, block_name: Optional[str] = None) -> str:
            """
            Retrieve the current live sensor reading, baseline, percentage deviation,
            and anomaly status for a specific metric (e.g. energy, water, waste, temperature)
            and optional facility block.
            """
            res = GreenNexaDataTools.get_current_metric(db, org_id, metric, block_name)
            return str(res)

        def get_active_anomalies(metric: Optional[str] = None, block_name: Optional[str] = None) -> str:
            """
            Retrieve currently active open or acknowledged anomalies, including their severity,
            observed value, expected baseline range, and root-cause reasons.
            """
            res = GreenNexaDataTools.get_active_anomalies(db, org_id, metric, block_name)
            return str(res)

        def get_forecast(metric: str) -> str:
            """
            Retrieve the 24-hour Machine Learning time-series forecast for energy or water,
            including predicted average, trend direction, and model details.
            """
            res = GreenNexaDataTools.get_forecast(db, org_id, metric)
            return str(res)

        def get_block_comparison(metric: str) -> str:
            """
            Compare and rank facility blocks by consumption or sensor readings to determine
            which block has the highest or lowest consumption.
            """
            res = GreenNexaDataTools.get_block_comparison(db, org_id, metric)
            return str(res)

        def get_recommendations(metric: Optional[str] = None) -> str:
            """
            Retrieve active AI sustainability recommendations, prioritized action steps,
            and identified root causes for the facility.
            """
            res = GreenNexaDataTools.get_recommendations(db, org_id, metric)
            return str(res)

        def get_facility_status() -> str:
            """
            Get a general health summary of the facility, including total active blocks,
            anomaly counts, and active sustainability recommendations.
            """
            res = GreenNexaDataTools.get_organisation_summary(db, org_id)
            return str(res)

        # What-If Scenario Simulation Tools
        def run_energy_scenario(
            ac_hours_reduced: float = 0.0,
            thermostat_temp_increase_c: float = 0.0,
            solar_offset_pct: float = 0.0,
            occupancy_change_pct: float = 0.0,
            led_retrofit_pct: float = 0.0,
        ) -> str:
            """
            Run a counterfactual What-If simulation for energy consumption over the next 24 hours.
            Parameters:
              - ac_hours_reduced: Hours of AC / chiller operation curtailed (e.g. 2.0).
              - thermostat_temp_increase_c: Temperature setpoint increase in Celsius (e.g. 1.0 or 2.0).
              - solar_offset_pct: Percentage of electrical load offset by solar PV (0 to 100).
              - occupancy_change_pct: Percentage change in facility occupancy (-100 to +100).
              - led_retrofit_pct: Percentage of lighting upgraded to energy-efficient LEDs (0 to 100).
            Returns baseline kWh, projected kWh, net savings, INR cost impact, CO2 avoided, and assumptions.
            """
            res = scenario_simulation_service.run_energy_scenario(
                db=db,
                organisation_id=org_id,
                ac_hours_reduced=ac_hours_reduced,
                thermostat_temp_increase_c=thermostat_temp_increase_c,
                solar_offset_pct=solar_offset_pct,
                occupancy_change_pct=occupancy_change_pct,
                led_retrofit_pct=led_retrofit_pct,
            )
            return str(res)

        def run_water_scenario(
            water_reduction_pct: float = 0.0,
            rainwater_harvest_liters: float = 0.0,
            low_flow_fixture_adoption_pct: float = 0.0,
            irrigation_scheduling_hours: float = 0.0,
        ) -> str:
            """
            Run a counterfactual What-If simulation for water consumption over the next 24 hours.
            Parameters:
              - water_reduction_pct: Overall targeted percentage reduction in water draw (e.g. 10.0 for 10%).
              - rainwater_harvest_liters: Liters of rainwater or recycled greywater supplied.
              - low_flow_fixture_adoption_pct: Percentage of taps/restrooms fitted with low-flow aerators.
              - irrigation_scheduling_hours: Hours irrigation shifted to early morning/evening.
            Returns baseline Liters, projected Liters, net savings, INR savings, and assumptions.
            """
            res = scenario_simulation_service.run_water_scenario(
                db=db,
                organisation_id=org_id,
                water_reduction_pct=water_reduction_pct,
                rainwater_harvest_liters=rainwater_harvest_liters,
                low_flow_fixture_adoption_pct=low_flow_fixture_adoption_pct,
                irrigation_scheduling_hours=irrigation_scheduling_hours,
            )
            return str(res)

        def run_waste_scenario(
            collection_route_optimization_pct: float = 0.0,
            recycling_rate_increase_pct: float = 0.0,
            compactor_installation: bool = False,
        ) -> str:
            """
            Run a counterfactual What-If simulation for campus waste management over the next 24 hours.
            Parameters:
              - collection_route_optimization_pct: Percentage improvement in bin collection dispatch efficiency.
              - recycling_rate_increase_pct: Percentage increase in source segregation and recycling.
              - compactor_installation: Whether solar smart compactors are activated.
            Returns baseline kg, diverted kg, overflow risk reduction %, and assumptions.
            """
            res = scenario_simulation_service.run_waste_scenario(
                db=db,
                organisation_id=org_id,
                collection_route_optimization_pct=collection_route_optimization_pct,
                recycling_rate_increase_pct=recycling_rate_increase_pct,
                compactor_installation=compactor_installation,
            )
            return str(res)

        def run_traffic_scenario(
            shuttle_frequency_increase_pct: float = 0.0,
            carpool_incentive_adoption_pct: float = 0.0,
            staggered_shifts_pct: float = 0.0,
        ) -> str:
            """
            Run a counterfactual What-If simulation for campus traffic and gate congestion.
            Parameters:
              - shuttle_frequency_increase_pct: Percentage boost in feeder electric shuttle runs.
              - carpool_incentive_adoption_pct: Percentage adoption of reserved carpool bays.
              - staggered_shifts_pct: Percentage of departments with staggered operational shifts.
            Returns vehicle volume reduction, peak gate queue relief %, CO2 avoided, and assumptions.
            """
            res = scenario_simulation_service.run_traffic_scenario(
                db=db,
                organisation_id=org_id,
                shuttle_frequency_increase_pct=shuttle_frequency_increase_pct,
                carpool_incentive_adoption_pct=carpool_incentive_adoption_pct,
                staggered_shifts_pct=staggered_shifts_pct,
            )
            return str(res)

        tools.extend([
            get_current_metrics,
            get_active_anomalies,
            get_forecast,
            get_block_comparison,
            get_recommendations,
            get_facility_status,
            run_energy_scenario,
            run_water_scenario,
            run_waste_scenario,
            run_traffic_scenario,
        ])

    # Platform tools (Only available to SUPER_ADMIN)
    if is_super_admin:
        def get_platform_summary() -> str:
            """
            Platform-wide overview across all registered customer organisations (Super Admin only).
            """
            res = GreenNexaDataTools.get_platform_summary(db)
            return str(res)

        def get_organisation_list() -> str:
            """
            List all registered customer organisations, facility types, and status (Super Admin only).
            """
            res = GreenNexaDataTools.get_organisation_list(db)
            return str(res)

        def count_organisations_by_facility_type(facility_type: str) -> str:
            """
            Count how many organisations match a facility type (e.g. school, college, hospital, municipality).
            """
            res = GreenNexaDataTools.count_organisations_by_facility_type(db, facility_type)
            return str(res)

        def get_total_admins() -> str:
            """
            Get the total number of registered administrator accounts across all organisations.
            """
            res = GreenNexaDataTools.get_total_admins(db)
            return str(res)

        def compare_organisations(metric: str) -> str:
            """
            Compare customer organisations by metric consumption or anomaly volume (Super Admin only).
            """
            res = GreenNexaDataTools.compare_organisations(db, metric)
            return str(res)

        tools.extend([
            get_platform_summary,
            get_organisation_list,
            count_organisations_by_facility_type,
            get_total_admins,
            compare_organisations,
        ])

    return tools
