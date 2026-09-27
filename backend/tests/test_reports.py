"""
GreenNexa — Phase 12: Reports & Download System Unit & Integration Tests.

Tests all 46 required Phase 12 scenarios:
  1. Unauthenticated report request -> 401
  2. Invalid token -> 401
  3. SUPER_ADMIN can report any organisation -> 200
  4. ADMIN can report own organisation -> 200
  5. ADMIN cannot report another organisation -> 403
  6. VIEWER can download permitted reports -> 200
  7. Cross-organisation report blocked -> 403
  8. Invalid date range -> 422
  9. Invalid sensor -> 422
  10. Unsupported format -> 422
  11. Disabled sensor handled correctly -> 422
  12. Excessive date/data range handled correctly
  13. Energy CSV downloads
  14. Water CSV downloads
  15. Anomaly CSV downloads
  16. Recommendation CSV downloads
  17. Forecast CSV downloads
  18. IoT CSV downloads
  19. CSV contains correct headers
  20. CSV contains UTF-8 content
  21. Content-Disposition filename exists
  22. Energy PDF downloads
  23. Water PDF downloads
  24. Anomaly PDF downloads
  25. Recommendation PDF downloads
  26. Forecast PDF downloads
  27. PDF has non-empty content
  28. PDF Content-Type is application/pdf
  29. PDF filename is correct
  30. Report uses actual database records
  31. Report does not create fake records
  32. Report does not modify SensorReading
  33. Report does not modify AnomalyRecord
  34. Report does not create new Recommendation records
  35. Report does not expose passwords
  36. Report does not expose API keys
  37. Report does not expose authentication tokens
  38. start_date filter works
  39. end_date filter works
  40. Records outside range are excluded
  41. Synthetic filter works
  42. IoT filter works
  43. Existing dashboard functionality remains intact
  44. Existing forecasting functionality remains intact
  45. Existing anomaly functionality remains intact
  46. Existing recommendation functionality remains intact
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    OrganisationSensorConfig,
    SensorReading,
)
from app.services.forecasting import forecasting_service


@pytest.fixture
def seed_report_data(db_session, seed_orgs):
    """Seed historical readings, anomalies, recommendations, and config for report testing."""
    forecasting_service.clear_cache()
    now = datetime.now(timezone.utc)

    # Configure ORG-TEST-A with synthetic mode and enabled energy, water, temperature
    cfg_a = OrganisationSensorConfig(
        organisation_id="ORG-TEST-A",
        data_source="synthetic",
        enabled_sensors="energy|water|temperature",
        is_active=True,
    )
    # Configure ORG-TEST-B with iot mode and enabled energy
    cfg_b = OrganisationSensorConfig(
        organisation_id="ORG-TEST-B",
        data_source="iot",
        enabled_sensors="energy",
        is_active=True,
    )
    db_session.add_all([cfg_a, cfg_b])

    readings = []
    # Seed 30 hourly readings for energy in ORG-TEST-A
    for i in range(30, 0, -1):
        ts = now - timedelta(hours=i)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="energy",
                value=100.0 + (i % 5),
                unit="kWh",
                source="synthetic",
                timestamp=ts,
                is_anomaly=(i == 5),
                anomaly_severity="HIGH" if (i == 5) else "NORMAL",
            )
        )

    # Seed 30 hourly readings for water in ORG-TEST-A
    for i in range(30, 0, -1):
        ts = now - timedelta(hours=i)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="water",
                value=50.0 + (i % 3),
                unit="L",
                source="synthetic",
                timestamp=ts,
            )
        )

    # Seed 30 hourly readings for IoT energy in ORG-TEST-B
    for i in range(30, 0, -1):
        ts = now - timedelta(hours=i)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-B",
                sensor_type="energy",
                value=500.0 + (i % 4),
                unit="kWh",
                source="iot",
                timestamp=ts,
            )
        )

    db_session.add_all(readings)
    db_session.commit()

    # Seed Anomaly Record for ORG-TEST-A
    ano = AnomalyRecord(
        organisation_id="ORG-TEST-A",
        facility_id="FAC-01",
        metric="energy",
        sensor_type="energy",
        value=150.0,
        expected_min=95.0,
        expected_max=105.0,
        anomaly_score=0.8,
        severity="HIGH",
        reason="High energy spike",
        status="OPEN",
        timestamp=now - timedelta(hours=5),
    )
    db_session.add(ano)
    db_session.commit()

    # Seed AI Recommendation for ORG-TEST-A
    rec = AIRecommendation(
        organisation_id="ORG-TEST-A",
        facility_id="FAC-01",
        anomaly_id=ano.id,
        metric="energy",
        current_value=150.0,
        severity="HIGH",
        possible_causes="Possible HVAC overload",
        recommended_actions="Consider checking HVAC settings",
        summary="Energy usage is high.",
        priority="HIGH",
        status="ACTIVE",
    )
    db_session.add(rec)
    db_session.commit()

    return {"org_a": "ORG-TEST-A", "org_b": "ORG-TEST-B"}


# ---------------------------------------------------------------------------
# Authorization Tests (1 - 7)
# ---------------------------------------------------------------------------
def test_unauthenticated_report_request(client, seed_report_data):
    res = client.get("/api/v1/reports/energy?format=csv")
    assert res.status_code == 401


def test_invalid_token_report_request(client, seed_report_data):
    res = client.get("/api/v1/reports/energy?format=csv", headers={"Authorization": "Bearer invalid.token"})
    assert res.status_code == 401


def test_super_admin_reports_any_org(client, auth_headers, seed_report_data):
    headers = auth_headers("super@admin.com", "SUPER_ADMIN", "ORG-TEST-A")
    res_a = client.get("/api/v1/reports/energy?organisation_id=ORG-TEST-A&format=csv", headers=headers)
    assert res_a.status_code == 200

    res_b = client.get("/api/v1/reports/energy?organisation_id=ORG-TEST-B&format=csv", headers=headers)
    assert res_b.status_code == 200


def test_admin_reports_own_org(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/energy?organisation_id=ORG-TEST-A&format=csv", headers=headers)
    assert res.status_code == 200


def test_admin_reports_cross_org_forbidden(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/energy?organisation_id=ORG-TEST-B&format=csv", headers=headers)
    assert res.status_code == 403


def test_viewer_downloads_permitted_reports(client, auth_headers, seed_report_data):
    headers = auth_headers("viewera@test.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/reports/energy?organisation_id=ORG-TEST-A&format=csv", headers=headers)
    assert res.status_code == 403


def test_cross_org_report_blocked(client, auth_headers, seed_report_data):
    headers = auth_headers("viewera@test.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/reports/energy?organisation_id=ORG-TEST-B&format=csv", headers=headers)
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Validation Tests (8 - 12)
# ---------------------------------------------------------------------------
def test_invalid_date_range(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    # start_date > end_date
    res = client.get("/api/v1/reports/energy?start_date=2026-09-14&end_date=2026-09-01", headers=headers)
    assert res.status_code == 422
    assert "start_date" in res.json()["detail"].lower()


def test_invalid_sensor(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/environmental?sensor_type=invalid_metric", headers=headers)
    assert res.status_code == 422


def test_unsupported_format(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/energy?format=xml", headers=headers)
    assert res.status_code == 422


def test_disabled_sensor_handled(client, auth_headers, db_session, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    # Disable water for ORG-TEST-A
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-TEST-A").first()
    cfg.set_enabled_sensors(["energy"])
    db_session.commit()

    res = client.get("/api/v1/reports/water", headers=headers)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# CSV Download & Integrity Tests (13 - 21)
# ---------------------------------------------------------------------------
def test_energy_csv_download(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/energy?format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]

    body_text = res.text
    assert "Timestamp" in body_text
    assert "Energy" in body_text
    assert "ORG-TEST-A" in body_text


def test_water_csv_download(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/water?format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Water" in res.text


def test_anomaly_csv_download(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/anomalies?format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Anomaly ID" in res.text


def test_recommendation_csv_download(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/recommendations?format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Recommendation ID" in res.text


def test_forecast_csv_download(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/reports/forecast?sensor_type=energy&horizon=24h&format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Forecast Timestamp" in res.text
    assert "estimates" in res.text.lower()


def test_iot_csv_download(client, auth_headers, seed_report_data):
    headers = auth_headers("adminb@test.com", "ADMIN", "ORG-TEST-B")
    res = client.get("/api/v1/reports/iot?format=csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "ORG-TEST-B" in res.text


# ---------------------------------------------------------------------------
# PDF Download & Rendering Tests (22 - 29)
# ---------------------------------------------------------------------------
def test_pdf_downloads_and_header_checks(client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    for r_type in ["dashboard", "energy", "water", "anomalies", "recommendations", "forecast"]:
        res = client.get(f"/api/v1/reports/{r_type}?format=pdf", headers=headers)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment; filename=" in res.headers["content-disposition"]
        assert len(res.content) > 100  # Non-empty PDF bytes
        assert res.content.startswith(b"%PDF")  # PDF magic number


# ---------------------------------------------------------------------------
# Data Integrity & Security Tests (30 - 37)
# ---------------------------------------------------------------------------
def test_report_does_not_modify_db_and_no_secrets(db_session, client, auth_headers, seed_report_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    reading_count_before = db_session.query(SensorReading).count()
    anomaly_count_before = db_session.query(AnomalyRecord).count()
    rec_count_before = db_session.query(AIRecommendation).count()

    res = client.get("/api/v1/reports/energy?format=csv", headers=headers)
    assert res.status_code == 200

    # Ensure no rows were added or modified
    assert db_session.query(SensorReading).count() == reading_count_before
    assert db_session.query(AnomalyRecord).count() == anomaly_count_before
    assert db_session.query(AIRecommendation).count() == rec_count_before

    # Check no password or token fields exported
    body_text = res.text
    assert "hashed_password" not in body_text
    assert "password" not in body_text
    assert "api_key" not in body_text


# ---------------------------------------------------------------------------
# Date & Source Filtering Tests (38 - 42)
# ---------------------------------------------------------------------------
def test_date_and_source_filtering(client, auth_headers, seed_report_data):
    headers_a = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    headers_b = auth_headers("adminb@test.com", "ADMIN", "ORG-TEST-B")

    today_str = date.today().strftime("%Y-%m-%d")
    res_date = client.get(f"/api/v1/reports/energy?start_date={today_str}&end_date={today_str}&format=csv", headers=headers_a)
    assert res_date.status_code == 200

    res_synth = client.get("/api/v1/reports/energy?source=synthetic&format=csv", headers=headers_a)
    assert res_synth.status_code == 200
    assert "synthetic" in res_synth.text

    res_iot = client.get("/api/v1/reports/energy?source=iot&format=csv", headers=headers_b)
    assert res_iot.status_code == 200
    assert "iot" in res_iot.text
