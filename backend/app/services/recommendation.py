"""
GreenNexa — AI Recommendation Service.

Generates decision-support sustainability recommendations dynamically from detected
anomalies, historical statistics, and Phase 9 forecasting trends.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    MunicipalityWard,
    OrganisationSensorConfig,
    SensorReading,
)
from app.services.forecasting import forecasting_service

logger = logging.getLogger(__name__)

SUPPORTED_RECOMMENDATION_SENSORS = {
    "energy",
    "water",
    "temperature",
    "humidity",
    "co2",
    "waste",
    "air_quality",
    "traffic",
    "parking",
    "assets",
    "safety",
    "climate",
    # Civic / Municipality natural-location modules (anomaly -> recommendation)
    "street_lighting",
    "roads",
    "parks",
    "sewage",
    "sewage_level",
    "water_flow",
    "water_level",
    "rainfall",
}

RECOMMENDATION_TEMPLATES = {
    "energy": {
        "title": "High Energy Usage Alert",
        "cause": "Possible high-load equipment operation|Unscheduled electrical consumption|HVAC/AC spike",
        "action": "Inspect high-load equipment|Check HVAC/AC operation|Reduce non-essential electrical load temporarily|Inspect unusual consumption zone",
        "summary": "Energy usage is significantly above its configured baseline. Inspect high-load equipment and consider reducing non-essential HVAC/AC usage temporarily.",
    },
    "water": {
        "title": "Water Consumption Spike Alert",
        "cause": "Possible plumbing leakage|Faulty fixture or tap|Abnormal water equipment draw",
        "action": "Inspect for possible leakage|Check taps and pipes|Inspect water-consuming equipment|Verify abnormal consumption",
        "summary": "Water usage is significantly above its configured baseline. Inspect pipes, taps, and water-consuming equipment for possible leakage or abnormal use.",
    },
    "waste": {
        "title": "Critical Waste Capacity Alert",
        "cause": "Waste container at or near full capacity|High fill rate|Collection schedule backlog",
        "action": "Prioritize collection|Inspect full or near-full bins|Route collection to affected block",
        "summary": "Waste fill level has reached critical capacity. Prioritize waste collection.",
    },
    "air_quality": {
        "title": "Air Quality Anomaly Alert",
        "cause": "Elevated particulate matter|Inadequate air handling|Local pollution source",
        "action": "Inspect ventilation|Inspect local pollution source|Increase monitoring|Inspect air-handling equipment",
        "summary": "Air quality levels deviate from standard thresholds. Inspect ventilation and air-handling equipment.",
    },
    "temperature": {
        "title": "Temperature Deviation Alert",
        "cause": "HVAC thermal setting conflict|Door or window breach|Cooling/heating performance deficit",
        "action": "Inspect HVAC/temperature control|Check thermostat settings|Inspect cooling/heating performance",
        "summary": "Temperature deviates from operating baseline. Inspect HVAC settings and temperature controls.",
    },
    "humidity": {
        "title": "Humidity Anomaly Alert",
        "cause": "Ventilation deficiency|Dehumidifier failure|Moisture ingress",
        "action": "Inspect ventilation/dehumidification|Check moisture source",
        "summary": "Humidity levels are outside standard operating thresholds. Inspect ventilation and dehumidification systems.",
    },
    "co2": {
        "title": "Elevated CO2 Levels Alert",
        "cause": "Inadequate fresh air exchange|High room occupancy concentration",
        "action": "Inspect ventilation|Check occupancy/air exchange|Increase fresh-air circulation where operationally appropriate",
        "summary": "CO2 levels are elevated. Inspect ventilation and increase fresh-air circulation.",
    },
    "traffic": {
        "title": "Traffic Congestion Alert",
        "cause": "Peak vehicle ingress|Gate delay|Bottleneck at route",
        "action": "Inspect congested gate/route|Adjust traffic operations|Investigate peak-period bottleneck",
        "summary": "Traffic rate is elevated above baseline. Inspect congested routes and adjust traffic operations.",
    },
    "parking": {
        "title": "Parking Capacity Alert",
        "cause": "Parking capacity threshold reached|Uneven lot distribution",
        "action": "Inspect parking occupancy|Redirect vehicles to available area|Review peak-period utilization",
        "summary": "Parking occupancy has reached critical capacity. Redirect vehicles to alternative parking zones.",
    },
    "assets": {
        "title": "Asset Utilization Alert",
        "cause": "Under-utilized equipment|Abnormal run hours|Maintenance requirement",
        "action": "Inspect under-utilized equipment|Check maintenance status|Inspect abnormal utilization",
        "summary": "Asset utilization shows unexpected deviation. Inspect equipment status and maintenance schedule.",
    },
    "safety": {
        "title": "Safety Compliance Alert",
        "cause": "Safety threshold deviation|Incident indicator flag",
        "action": "Inspect affected zone|Review incident context|Prioritize safety inspection",
        "summary": "Safety indicator requires attention. Prioritize immediate safety inspection.",
    },
    "climate": {
        "title": "Climate Resilience Alert",
        "cause": "Elevated environmental risk indicator|Weather resilience threshold breach",
        "action": "Inspect affected resilience/risk indicator|Review preparedness condition|Inspect related infrastructure",
        "summary": "Climate resilience indicator indicates risk. Review facility preparedness and related infrastructure.",
    },
    "street_lighting": {
        "title": "Street Lighting Outage Alert",
        "cause": "Street light circuit outage|Faulty pole controller|Power feeder trip in the zone",
        "action": "Dispatch maintenance crew to the affected zone|Reboot pole controllers|Check feeder line protection",
        "summary": "Street lighting demonstrates an outage pattern in the affected zone. Inspect lighting circuits and pole controllers.",
    },
    "roads": {
        "title": "Roads & Infrastructure Alert",
        "cause": "Deteriorating road surface indicator|Drainage grate obstruction|Infrastructure wear",
        "action": "Schedule road inspection|Clear drainage grates|Escalate infrastructure maintenance",
        "summary": "Roads & infrastructure indicators deviate from baseline. Schedule inspection and maintenance.",
    },
    "parks": {
        "title": "Parks & Public Spaces Alert",
        "cause": "Public asset deterioration|Irrigation/watering anomaly|Park amenity outage",
        "action": "Inspect park amenities|Check irrigation systems|Schedule public-space maintenance",
        "summary": "Parks & public spaces indicator deviates from baseline. Inspect amenities and maintenance.",
    },
    "sewage": {
        "title": "Sewage & Drainage Alert",
        "cause": "Drain intake grate blocked|Stormwater flash surge|Sump lift pump trip",
        "action": "Deploy sanitation maintenance crew|Clear intake grates|Start backup lift pump",
        "summary": "Sewage & drainage levels deviate from operating thresholds. Deploy maintenance and inspect lift pumps.",
    },
    "sewage_level": {
        "title": "Drainage Water Level Alert",
        "cause": "Drain intake grate blocked by debris|Stormwater flash surge|Sump lift pump trip",
        "action": "Deploy sanitation maintenance crew to clear intake grates|Start backup lift pump|Inspect stormwater channels",
        "summary": "Drainage water level exceeds safe thresholds. Inspect sumps and stormwater channels for blockage risk.",
    },
    "water_flow": {
        "title": "Water Flow / Pumps Alert",
        "cause": "Main distribution pipeline burst|Gate valve failure|Downstream overflow",
        "action": "Dispatch field technician to inspect pipeline flow meters|Verify shut-off valve positions",
        "summary": "Water flow deviates from expected network values. Inspect the distribution pipeline and pump stations.",
    },
    "water_level": {
        "title": "Water Level Alert",
        "cause": "Storage sump inlet supply disruption|High drawdown rate|Tank structural leakage",
        "action": "Activate auxiliary water feed line|Verify tank level sensor calibration",
        "summary": "Water level is outside safe operating range. Verify reservoir supply and tank integrity.",
    },
    "rainfall": {
        "title": "Heavy Rainfall Alert",
        "cause": "Heavy localized monsoon storm front|Urban cloudburst",
        "action": "Alert civic emergency drainage operations|Inspect low-lying retention basins",
        "summary": "Rainfall rate is above threshold. Activate stormwater retention protocols.",
    },
}

CONFIDENCE_NOTE = (
    "These are decision-support suggestions based on statistical analysis. "
    "They are not verified diagnoses. Please investigate before taking action."
)


class RecommendationService:
    """
    Service handling recommendation generation, forecast integration,
    deduplication, and status update management.
    """

    def generate_recommendations_for_organisation(
        self,
        db: Session,
        organisation_id: str,
        sensor_type: Optional[str] = None,
        skip_recent_dedup: bool = False,
    ) -> List[AIRecommendation]:
        """
        Generate recommendations for open anomalies and forecast trends.

        skip_recent_dedup=True (used by the Demo cadence path) disables the
        1-hour same-org/sensor/location recommendation dedup so EVERY forced-new
        anomaly record still receives its own linked recommendation.
        """
        # 1. Get organisation sensor configuration
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        enabled_sensors = config.enabled_sensors_list if config else list(SUPPORTED_RECOMMENDATION_SENSORS)

        if sensor_type:
            clean_sensor = sensor_type.lower().strip()
            if clean_sensor not in SUPPORTED_RECOMMENDATION_SENSORS:
                raise ValueError(
                    f"Unsupported sensor type '{sensor_type}' for recommendations. "
                    f"Supported types: {', '.join(sorted(SUPPORTED_RECOMMENDATION_SENSORS))}."
                )
            if clean_sensor not in enabled_sensors:
                raise ValueError(
                    f"Sensor '{sensor_type}' is disabled for organisation '{organisation_id}'."
                )
            target_sensors = [clean_sensor]
        else:
            target_sensors = [s for s in enabled_sensors if s in SUPPORTED_RECOMMENDATION_SENSORS]

        # 2. Query open anomalies for enabled sensors
        anomalies = (
            db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.organisation_id == organisation_id,
                AnomalyRecord.metric.in_(target_sensors),
                AnomalyRecord.status == AnomalyRecord.STATUS_OPEN,
                AnomalyRecord.severity != AnomalyRecord.SEVERITY_NORMAL,
            )
            .order_by(AnomalyRecord.created_at.desc())
            .all()
        )

        generated_recs: List[AIRecommendation] = []
        now = datetime.now(timezone.utc)

        for ano in anomalies:
            # Deduplication: check if recommendation already exists for this anomaly
            existing = (
                db.query(AIRecommendation)
                .filter(AIRecommendation.anomaly_id == ano.id)
                .first()
            )
            if existing:
                generated_recs.append(existing)
                continue

            # Deduplication: check active recommendation for same org + block + metric in last 1 hour
            # (skipped when skip_recent_dedup=True so each Demo anomaly gets its own rec)
            recent_same_metric = None
            if not skip_recent_dedup:
                query_rec = db.query(AIRecommendation).filter(
                    AIRecommendation.organisation_id == organisation_id,
                    AIRecommendation.metric == ano.metric,
                    AIRecommendation.created_at >= now - timedelta(hours=1),
                )
                if ano.block_id:
                    query_rec = query_rec.filter(AIRecommendation.block_id == ano.block_id)
                elif ano.ward_id:
                    query_rec = query_rec.filter(AIRecommendation.ward_id == ano.ward_id)
                recent_same_metric = query_rec.first()
                if recent_same_metric:
                    generated_recs.append(recent_same_metric)
                    continue

            # Resolve block context
            block_name: Optional[str] = None
            if ano.block_id:
                fb = (
                    db.query(FacilityBlock)
                    .filter(
                        FacilityBlock.organisation_id == organisation_id,
                        (FacilityBlock.block_id == ano.block_id) | (FacilityBlock.block_name == ano.block_id),
                    )
                    .first()
                )
                block_name = fb.block_name if fb else ano.block_id
            elif ano.ward_id:
                wd = (
                    db.query(MunicipalityWard)
                    .filter(
                        MunicipalityWard.municipality_id == organisation_id,
                        (MunicipalityWard.ward_number == ano.ward_id) | (MunicipalityWard.id == ano.ward_id),
                    )
                    .first()
                )
                block_name = wd.ward_name if wd else ano.facility_id
            elif ano.facility_id:
                block_name = ano.facility_id

            location_label = block_name if block_name else "facility"

            # Module-specific recommendation template
            tmpl = RECOMMENDATION_TEMPLATES.get(
                ano.metric,
                {
                    "title": f"Anomaly Alert for {ano.metric}",
                    "cause": f"Possible abnormal {ano.metric} variation",
                    "action": f"Consider checking {ano.metric} sensors and facility systems",
                    "summary": f"{ano.metric.capitalize()} reading is outside normal baseline.",
                },
            )

            # Build tailored action and summary with exact block context
            metric_clean = ano.metric.lower()
            if metric_clean == "water":
                summary_base = f"Water usage in {location_label} is significantly above its configured baseline. Inspect pipes, taps, and water-consuming equipment for possible leakage or abnormal use."
                actions_str = f"Inspect pipes, taps, and water-consuming equipment in {location_label} for possible leakage or abnormal use|Check water supply valves and fixtures"
                causes_str = f"Possible plumbing leakage in {location_label}|Faulty tap or fixture|Abnormal water equipment draw"
            elif metric_clean == "energy":
                summary_base = f"Energy usage in {location_label} is significantly above its configured baseline. Inspect high-load equipment and consider reducing non-essential HVAC/AC usage temporarily."
                actions_str = f"Inspect high-load equipment in {location_label}|Check HVAC/AC operation and consider reducing non-essential electrical load temporarily"
                causes_str = f"High electrical load in {location_label}|HVAC cooling spike|Equipment active outside scheduled hours"
            elif metric_clean == "waste":
                summary_base = f"Waste fill level in {location_label} has reached critical capacity. Prioritize waste collection for {location_label}."
                actions_str = f"Prioritize waste collection for {location_label}|Inspect full or near-full bins|Route collection to {location_label}"
                causes_str = f"Waste container at critical capacity in {location_label}|High bin fill rate|Improper waste packing"
            elif metric_clean in {"temperature", "climate"}:
                summary_base = f"Temperature in {location_label} deviates significantly from baseline. Inspect HVAC settings and temperature controls."
                actions_str = f"Inspect HVAC/temperature control in {location_label}|Check thermostat settings and cooling/heating performance"
                causes_str = f"HVAC thermal setting conflict in {location_label}|Door or window breach"
            elif metric_clean == "humidity":
                summary_base = f"Humidity levels in {location_label} are outside standard operating thresholds. Inspect ventilation and dehumidification systems."
                actions_str = f"Inspect ventilation and dehumidification in {location_label}|Check moisture source"
                causes_str = f"Ventilation fan underperformance in {location_label}|Dehumidifier failure"
            elif metric_clean == "co2":
                summary_base = f"CO2 levels in {location_label} are elevated. Inspect ventilation and increase fresh-air circulation."
                actions_str = f"Inspect ventilation in {location_label}|Check occupancy/air exchange|Increase fresh-air circulation where operationally appropriate"
                causes_str = f"Inadequate fresh air exchange in {location_label}|High room occupancy concentration"
            elif metric_clean == "traffic":
                summary_base = f"Traffic activity in {location_label} exceeds baseline. Inspect congested routes and adjust traffic operations."
                actions_str = f"Inspect congested gate/route in {location_label}|Adjust traffic operations|Investigate peak-period bottleneck"
                causes_str = f"Peak vehicle ingress in {location_label}|Gate delay"
            elif metric_clean == "parking":
                summary_base = f"Parking occupancy in {location_label} has reached critical threshold. Redirect incoming vehicles."
                actions_str = f"Inspect parking occupancy in {location_label}|Redirect vehicles to available area|Review peak-period utilization"
                causes_str = f"Parking capacity threshold reached in {location_label}"
            elif metric_clean == "assets":
                summary_base = f"Asset utilization in {location_label} shows abnormal deviation. Inspect equipment status and maintenance schedule."
                actions_str = f"Inspect under-utilized equipment in {location_label}|Check maintenance status|Inspect abnormal utilization"
                causes_str = f"Under-utilized equipment in {location_label}|Abnormal run hours"
            elif metric_clean == "safety":
                summary_base = f"Safety metric in {location_label} requires attention. Prioritize on-site safety inspection."
                actions_str = f"Inspect affected zone in {location_label}|Review incident context|Prioritize safety inspection"
                causes_str = f"Safety threshold deviation in {location_label}"
            else:
                summary_base = f"{ano.metric.capitalize()} reading in {location_label} deviates from operating baseline."
                actions_str = tmpl["action"]
                causes_str = tmpl["cause"]

            # Forecast trend integration: module-aware
            forecast_note = ""
            if metric_clean == "energy":
                try:
                    fc = forecasting_service.get_forecast(db, organisation_id, "energy", horizon="24h")
                    if fc and fc.forecast:
                        avg_pred = sum(p.predicted_value for p in fc.forecast) / len(fc.forecast)
                        if avg_pred > ano.value * 1.05:
                            forecast_note = f" Energy consumption is trending upward. Consider reviewing HVAC and lighting schedules before the expected increase."
                except Exception as e:
                    logger.debug(f"Forecast check skipped during energy recommendation: {e}")
            elif metric_clean == "water":
                try:
                    fc = forecasting_service.get_forecast(db, organisation_id, "water", horizon="24h")
                    if fc and fc.forecast:
                        avg_pred = sum(p.predicted_value for p in fc.forecast) / len(fc.forecast)
                        if avg_pred > ano.value * 1.05:
                            forecast_note = f" Water consumption is trending upward. Inspect plumbing lines and supply fixtures before the expected increase."
                except Exception as e:
                    logger.debug(f"Forecast check skipped during water recommendation: {e}")

            summary_text = f"{summary_base}{forecast_note} ({CONFIDENCE_NOTE})"

            new_rec = AIRecommendation(
                organisation_id=organisation_id,
                block_id=ano.block_id,
                ward_id=ano.ward_id,
                facility_id=location_label,
                anomaly_id=ano.id,
                metric=ano.metric,
                current_value=ano.value,
                expected_range_min=ano.expected_min,
                expected_range_max=ano.expected_max,
                severity=ano.severity,
                historical_trend="rising" if ano.value > (ano.expected_max or ano.value) else "stable",
                possible_causes=causes_str,
                recommended_actions=actions_str,
                summary=summary_text,
                confidence_note=CONFIDENCE_NOTE,
                priority=ano.severity,
                status=AIRecommendation.STATUS_ACTIVE,
                data_sufficient=True,
            )
            db.add(new_rec)
            db.commit()
            db.refresh(new_rec)
            generated_recs.append(new_rec)

        return generated_recs

    def update_recommendation_status(
        self,
        db: Session,
        recommendation_id: str,
        new_status: str,
    ) -> AIRecommendation:
        """
        Update status of a recommendation (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED, ACTIONED).
        Synchronizes linked anomaly record status.
        """
        rec = (
            db.query(AIRecommendation)
            .filter(AIRecommendation.id == recommendation_id)
            .first()
        )
        if not rec:
            raise ValueError(f"Recommendation '{recommendation_id}' not found.")

        clean_status = new_status.upper().strip()
        rec.status = clean_status

        # Synchronize linked anomaly
        if rec.anomaly:
            now = datetime.now(timezone.utc)
            if clean_status == "RESOLVED" or clean_status == "ACTIONED":
                rec.anomaly.status = AnomalyRecord.STATUS_RESOLVED
                rec.anomaly.resolved_at = now
            elif clean_status == "DISMISSED":
                rec.anomaly.status = AnomalyRecord.STATUS_DISMISSED
                rec.anomaly.resolved_at = now
            elif clean_status == "ACKNOWLEDGED":
                rec.anomaly.status = AnomalyRecord.STATUS_ACKNOWLEDGED
                rec.anomaly.acknowledged_at = now

        db.commit()
        db.refresh(rec)
        return rec


# Singleton instance
recommendation_service = RecommendationService()

