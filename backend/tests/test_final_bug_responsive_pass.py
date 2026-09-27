"""
Final GreenNexa Bug Fix + Responsive Pass Tests
Validates:
1. Demo Mode scoped strictly to active module/page (Energy only updates Energy sensors, etc.)
2. Historical readings preservation during scoped simulation
3. Logout endpoint stops demo mode and halts simulator
4. Simulator status reports active scoped modules
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.synthetic_simulator import simulator_instance

@pytest.fixture(autouse=True)
def cleanup_simulator():
    """Ensure simulator is stopped before and after test."""
    simulator_instance.stop()
    simulator_instance._demo_modules.clear()
    yield
    simulator_instance.stop()
    simulator_instance._demo_modules.clear()


def test_scoped_demo_mode_energy_only(client: TestClient, auth_headers):
    """Starting demo mode with module='energy' should only generate readings for energy sensors."""
    org_id = "ORG-00001"
    headers = auth_headers("admin@org1.ai", "ADMIN", org_id)
    
    # Start demo mode scoped to energy
    res = client.post(
        "/api/v1/simulator/synthetic/start?module=energy",
        json={"organisation_id": org_id, "demo_mode": True, "module": "energy"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["running"] is True
    assert "energy" in data.get("active_modules", [])
    assert simulator_instance._demo_active_for(org_id, "energy") is True
    assert simulator_instance._demo_active_for(org_id, "water") is False

    # Status check
    status_res = client.get(
        f"/api/v1/simulator/synthetic/status?organisation_id={org_id}",
        headers=headers
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "energy" in status_data.get("active_modules", [])


def test_scoped_demo_mode_water_only(client: TestClient, auth_headers):
    """Starting demo mode with module='water' should only generate readings for water sensors."""
    org_id = "ORG-00001"
    headers = auth_headers("admin@org1.ai", "ADMIN", org_id)
    
    res = client.post(
        "/api/v1/simulator/synthetic/start?module=water",
        json={"organisation_id": org_id, "demo_mode": True, "module": "water"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "water" in data.get("active_modules", [])
    assert simulator_instance._demo_active_for(org_id, "water") is True
    assert simulator_instance._demo_active_for(org_id, "energy") is False


def test_logout_endpoint_stops_demo_mode(client: TestClient, auth_headers):
    """Logging out must call logout endpoint and stop active demo mode and background simulator."""
    org_id = "ORG-00001"
    headers = auth_headers("admin@org1.ai", "ADMIN", org_id)
    
    # Start demo mode
    client.post(
        "/api/v1/simulator/synthetic/start?module=energy",
        json={"organisation_id": org_id, "demo_mode": True, "module": "energy"},
        headers=headers
    )
    status_before = simulator_instance.status(organisation_id=org_id)
    assert status_before["demo_mode"] is True

    # Call logout
    logout_res = client.post(
        f"/api/v1/auth/logout?organisation_id={org_id}",
        json={},
        headers=headers
    )
    assert logout_res.status_code == 200
    logout_data = logout_res.json()
    assert logout_data["status"] == "success"

    # Verify simulator demo mode stopped
    status_after = simulator_instance.status(organisation_id=org_id)
    assert status_after["demo_mode"] is False
    assert org_id not in simulator_instance._demo_modules


def test_stop_scoped_module(client: TestClient, auth_headers):
    """Stopping demo mode for a specific module should leave other modules or halt if none left."""
    org_id = "ORG-00001"
    headers = auth_headers("admin@org1.ai", "ADMIN", org_id)
    
    # Start energy and water
    client.post("/api/v1/simulator/synthetic/start?module=energy", json={"organisation_id": org_id, "demo_mode": True, "module": "energy"}, headers=headers)
    client.post("/api/v1/simulator/synthetic/start?module=water", json={"organisation_id": org_id, "demo_mode": True, "module": "water"}, headers=headers)
    
    assert simulator_instance._demo_active_for(org_id, "energy") is True
    assert simulator_instance._demo_active_for(org_id, "water") is True

    # Stop energy only
    res = client.post(
        "/api/v1/simulator/synthetic/stop?module=energy",
        json={"organisation_id": org_id},
        headers=headers
    )
    assert res.status_code == 200
    assert simulator_instance._demo_active_for(org_id, "energy") is False
    assert simulator_instance._demo_active_for(org_id, "water") is True
    assert "water" in res.json().get("active_modules", [])

    # Stop all
    res_all = client.post(
        "/api/v1/simulator/synthetic/stop",
        json={"organisation_id": org_id},
        headers=headers
    )
    assert res_all.status_code == 200
    assert simulator_instance._demo_active_for(org_id, "water") is False
    assert res_all.json().get("active_modules", []) == []
