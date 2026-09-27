"""
GreenNexa — SQLAlchemy ORM models.

Tables:
  - organisations       Organisation master record
  - sensor_readings     Raw sensor data (energy, water, environment, waste)
  - anomaly_records     Detected anomalies with severity and reason
  - ai_recommendations  Recommendation engine output per anomaly
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# Helper — current UTC time (used as default for timestamps)
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Organisation
# ---------------------------------------------------------------------------
class Organisation(Base):
    """
    Represents a customer organisation (college, hospital, office, etc.).
    All data is scoped to an organisation for full isolation.
    """
    __tablename__ = "organisations"

    OWNERSHIP_GOVERNMENT = "GOVERNMENT"
    OWNERSHIP_PRIVATE = "PRIVATE"
    VALID_OWNERSHIP_TYPES = {OWNERSHIP_GOVERNMENT, OWNERSHIP_PRIVATE}

    # Dashboard Style System — presentation only, never affects stored data.
    DASHBOARD_STYLE_EXECUTIVE = "EXECUTIVE"
    DASHBOARD_STYLE_OPERATIONS = "OPERATIONS"
    DASHBOARD_STYLE_ANALYTICS = "ANALYTICS"
    DASHBOARD_STYLE_COMMAND_CENTER = "COMMAND_CENTER"
    VALID_DASHBOARD_STYLES = (
        DASHBOARD_STYLE_EXECUTIVE,
        DASHBOARD_STYLE_OPERATIONS,
        DASHBOARD_STYLE_ANALYTICS,
        DASHBOARD_STYLE_COMMAND_CENTER,
    )
    DEFAULT_DASHBOARD_STYLE = DASHBOARD_STYLE_EXECUTIVE

    id = Column(String(50), primary_key=True)          # e.g. ORG-COL-001
    name = Column(String(200), nullable=False)
    ownership_type = Column(String(50), nullable=True) # GOVERNMENT / PRIVATE
    org_type = Column(String(100), nullable=True)      # college / hospital / office …
    location = Column(String(300), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    facility_name = Column(String(200), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(String(300), nullable=True)
    org_code = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    # Persisted dashboard presentation preference (scoped per organisation).
    dashboard_style = Column(String(30), nullable=True, default=DEFAULT_DASHBOARD_STYLE)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True)

    # Relationships
    sensor_readings = relationship(
        "SensorReading", back_populates="organisation", cascade="all, delete-orphan"
    )
    anomaly_records = relationship(
        "AnomalyRecord", back_populates="organisation", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "AIRecommendation", back_populates="organisation", cascade="all, delete-orphan"
    )
    users = relationship(
        "User", back_populates="organisation", cascade="all, delete-orphan"
    )
    sensor_config = relationship(
        "OrganisationSensorConfig",
        back_populates="organisation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    iot_devices = relationship(
        "IoTDevice",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    facility_blocks = relationship(
        "FacilityBlock",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    municipality_wards = relationship(
        "MunicipalityWard",
        back_populates="municipality",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organisation id={self.id!r} name={self.name!r}>"

    @property
    def effective_dashboard_style(self) -> str:
        """
        Return the stored dashboard style, falling back to the default for rows
        created before the Dashboard Style system existed (NULL / unknown value).
        """
        value = (self.dashboard_style or "").strip().upper()
        if value in self.VALID_DASHBOARD_STYLES:
            return value
        return self.DEFAULT_DASHBOARD_STYLE


# ---------------------------------------------------------------------------
# Sensor Reading
# ---------------------------------------------------------------------------
class SensorReading(Base):
    """
    A single sensor reading from a device.

    sensor_type examples: energy, water, temperature, humidity, co2, air_quality,
                          waste_level, waste_weight, power, voltage, current
    source: 'synthetic' | 'iot'
    """
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("idx_sensor_readings_org_type_ts", "organisation_id", "sensor_type", "timestamp"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id = Column(String(100), nullable=True, index=True)
    block_id = Column(String(50), nullable=True, index=True)
    ward_id = Column(String(50), nullable=True, index=True)
    device_id = Column(String(100), nullable=True, index=True)
    sensor_type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)   # kWh, L, °C, %, ppm …
    source = Column(String(20), nullable=False, default="synthetic")  # synthetic | iot
    timestamp = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    is_anomaly = Column(Boolean, default=False, nullable=False)
    anomaly_severity = Column(String(20), nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="sensor_readings")

    def __repr__(self) -> str:
        return (
            f"<SensorReading org={self.organisation_id!r} "
            f"type={self.sensor_type!r} value={self.value} "
            f"ts={self.timestamp}>"
        )


# ---------------------------------------------------------------------------
# Anomaly Record
# ---------------------------------------------------------------------------
class AnomalyRecord(Base):
    """
    Stores a detected anomaly for a given sensor reading.

    severity: NORMAL | LOW | MEDIUM | HIGH | CRITICAL
    status:   OPEN | ACKNOWLEDGED | RESOLVED | DISMISSED
    """
    __tablename__ = "anomaly_records"

    SEVERITY_NORMAL = "NORMAL"
    SEVERITY_LOW = "LOW"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_HIGH = "HIGH"
    SEVERITY_CRITICAL = "CRITICAL"

    STATUS_OPEN = "OPEN"
    STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_DISMISSED = "DISMISSED"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id = Column(String(100), nullable=True, index=True)
    block_id = Column(String(50), nullable=True, index=True)
    ward_id = Column(String(50), nullable=True, index=True)
    metric = Column(String(50), nullable=False, index=True)    # energy | water | …
    sensor_type = Column(String(50), nullable=True)
    value = Column(Float, nullable=False)
    expected_min = Column(Float, nullable=True)
    expected_max = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)               # 0.0 – 1.0
    severity = Column(String(20), nullable=False, default="NORMAL", index=True)
    reason = Column(Text, nullable=True)                       # Human-readable explanation
    status = Column(String(20), nullable=False, default="OPEN", index=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    is_seen = Column(Boolean, default=False, nullable=False, index=True)
    seen_at = Column(DateTime(timezone=True), nullable=True)
    seen_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="anomaly_records")
    recommendation = relationship(
        "AIRecommendation",
        back_populates="anomaly",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AnomalyRecord org={self.organisation_id!r} "
            f"metric={self.metric!r} severity={self.severity!r} "
            f"value={self.value}>"
        )


# ---------------------------------------------------------------------------
# AI Recommendation
# ---------------------------------------------------------------------------
class AIRecommendation(Base):
    """
    Recommendation generated by the AI engine for an anomaly.

    IMPORTANT: Recommendations are decision-support suggestions.
    They are NOT verified diagnoses. Language must be hedged.
    """
    __tablename__ = "ai_recommendations"

    STATUS_ACTIVE = "ACTIVE"
    STATUS_OPEN = "OPEN"
    STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
    STATUS_RESOLVED = "RESOLVED"
    STATUS_DISMISSED = "DISMISSED"
    STATUS_ACTIONED = "ACTIONED"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id = Column(String(100), nullable=True, index=True)
    block_id = Column(String(50), nullable=True, index=True)
    ward_id = Column(String(50), nullable=True, index=True)
    anomaly_id = Column(
        String(36),
        ForeignKey("anomaly_records.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    metric = Column(String(50), nullable=False)
    current_value = Column(Float, nullable=False)
    expected_range_min = Column(Float, nullable=True)
    expected_range_max = Column(Float, nullable=True)
    severity = Column(String(20), nullable=False)

    # Trend description: rising | falling | stable | insufficient_data
    historical_trend = Column(String(30), nullable=True)

    # Stored as pipe-separated strings for broad DB compatibility
    # e.g. "Possible HVAC anomaly|Possible lighting left on"
    possible_causes = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)

    # Summary text combining all the above, ready for display
    summary = Column(Text, nullable=False)

    # Mandatory disclaimer — always appended
    confidence_note = Column(
        Text,
        nullable=False,
        default=(
            "These are decision-support suggestions based on statistical analysis. "
            "They are not verified diagnoses. Please investigate before taking action."
        ),
    )

    priority = Column(String(20), nullable=False, default="LOW")  # LOW|MEDIUM|HIGH|CRITICAL
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)
    data_sufficient = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    organisation = relationship("Organisation", back_populates="recommendations")
    anomaly = relationship("AnomalyRecord", back_populates="recommendation")

    @property
    def possible_causes_list(self) -> list[str]:
        """Return possible_causes as a Python list."""
        if not self.possible_causes:
            return []
        return [c.strip() for c in self.possible_causes.split("|") if c.strip()]

    @property
    def recommended_actions_list(self) -> list[str]:
        """Return recommended_actions as a Python list."""
        if not self.recommended_actions:
            return []
        return [a.strip() for a in self.recommended_actions.split("|") if a.strip()]

    def __repr__(self) -> str:
        return (
            f"<AIRecommendation org={self.organisation_id!r} "
            f"metric={self.metric!r} severity={self.severity!r} "
            f"data_sufficient={self.data_sufficient}>"
        )


# ---------------------------------------------------------------------------
# User & Role Management
# ---------------------------------------------------------------------------
class User(Base):
    """
    Represents a user account in the GreenNexa system.

    Roles:
      - SUPER_ADMIN: Global system access across all organisations
      - ADMIN: Administrator for a specific organisation
    """
    __tablename__ = "users"

    ROLE_SUPER_ADMIN = "SUPER_ADMIN"
    ROLE_ADMIN = "ADMIN"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(String(50), nullable=False, default=ROLE_ADMIN, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="users")
    password_reset_otps = relationship(
        "PasswordResetOTP", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def phone_number(self) -> Optional[str]:
        """Alias for phone attribute."""
        return self.phone

    @phone_number.setter
    def phone_number(self, value: Optional[str]):
        self.phone = value

    def __repr__(self) -> str:
        return f"<User email={self.email!r} role={self.role!r} org={self.organisation_id!r}>"


# ---------------------------------------------------------------------------
# Password Reset OTP Model
# ---------------------------------------------------------------------------
class PasswordResetOTP(Base):
    """
    Stores server-generated, hashed OTP records for password reset flows.
    Plaintext OTP is never stored in the database.
    """
    __tablename__ = "password_reset_otps"
    __table_args__ = (
        Index("idx_otp_user_created", "user_id", "created_at"),
        Index("idx_otp_session_expires", "id", "expires_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hashed_otp = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    reset_token = Column(String(128), nullable=True, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="password_reset_otps")

    def __repr__(self) -> str:
        return f"<PasswordResetOTP id={self.id!r} user_id={self.user_id!r} is_used={self.is_used}>"


# ---------------------------------------------------------------------------
# In-App Message Model
# ---------------------------------------------------------------------------
class Message(Base):
    """
    Internal in-app text message exchanged between GreenNexa users.
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_recipient_created", "recipient_id", "created_at"),
        Index("idx_messages_sender_created", "sender_id", "created_at"),
        Index("idx_messages_recipient_read", "recipient_id", "is_read"),
        Index("idx_messages_org_created", "organisation_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subject = Column(String(200), nullable=True)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    organisation = relationship("Organisation")

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id!r} sender={self.sender_id!r} "
            f"recipient={self.recipient_id!r} read={self.is_read}>"
        )



# ---------------------------------------------------------------------------
# Organisation Sensor Configuration & Data Source Management
# ---------------------------------------------------------------------------
class OrganisationSensorConfig(Base):
    """
    Stores sensor configuration and data source mode per organisation.

    data_source: 'synthetic' | 'iot' (mutually exclusive)
    enabled_sensors: pipe-separated string e.g. "energy|water|temperature|humidity"
    """
    __tablename__ = "organisation_sensor_configs"

    DATA_SOURCE_SYNTHETIC = "synthetic"
    DATA_SOURCE_IOT = "iot"
    ALLOWED_DATA_SOURCES = {DATA_SOURCE_SYNTHETIC, DATA_SOURCE_IOT}

    ALLOWED_SENSOR_TYPES = {
        "energy",
        "water",
        "waste",
        "air_quality",
        "temperature",
        "humidity",
        "co2",
        "traffic",
        "parking",
        "water_flow",
        "water_level",
        "sewage_level",
        "rainfall",
        "equipment_asset",
        "occupancy",
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
        # Legacy supported types
        "assets",
        "safety",
        "climate",
        # Civic / Municipality function sensors (natural-location modules — never FacilityBlock scoped)
        "street_lighting",
        "roads",
        "parks",
        "sewage",
    }

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    data_source = Column(String(20), nullable=False, default=DATA_SOURCE_SYNTHETIC)
    enabled_sensors = Column(Text, nullable=False, default="energy|water|temperature|humidity")
    sensor_configs = Column(Text, nullable=True)  # JSON-encoded per-sensor baseline, thresholds & units
    is_active = Column(Boolean, default=True, nullable=False)
    simulated_date = Column(Date, nullable=True)  # Current simulated calendar date
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="sensor_config")

    DEFAULT_SIMULATED_DATE = date(2026, 9, 20)

    @property
    def current_simulated_date(self) -> date:
        """Return the current simulated date for this organisation, defaulting to 2026-09-20."""
        if self.simulated_date is not None:
            return self.simulated_date
        if self.sensor_configs:
            try:
                data = json.loads(self.sensor_configs)
                if "_simulated_date" in data:
                    return date.fromisoformat(data["_simulated_date"])
            except Exception:
                pass
        return self.DEFAULT_SIMULATED_DATE

    def advance_simulated_date(self, days: int = 1) -> date:
        """Advance the simulated calendar date, correctly handling month/year/leap-year boundaries."""
        cur = self.current_simulated_date
        nxt = cur + timedelta(days=days)
        self.simulated_date = nxt
        try:
            stored = json.loads(self.sensor_configs) if self.sensor_configs else {}
            stored["_simulated_date"] = nxt.isoformat()
            self.sensor_configs = json.dumps(stored)
        except Exception:
            pass
        return nxt

    def set_simulated_date(self, new_date: date) -> date:
        """Manually set simulated calendar date, correctly persisting to both column and config."""
        self.simulated_date = new_date
        try:
            stored = json.loads(self.sensor_configs) if self.sensor_configs else {}
            stored["_simulated_date"] = new_date.isoformat()
            self.sensor_configs = json.dumps(stored)
        except Exception:
            pass
        return new_date

    @property
    def enabled_sensors_list(self) -> list[str]:
        """Return enabled sensors as a Python list of strings."""
        if not self.enabled_sensors:
            return []
        raw = self.enabled_sensors.replace(",", "|")
        return [s.strip().lower() for s in raw.split("|") if s.strip()]

    def set_enabled_sensors(self, sensors: list[str]) -> None:
        """Set enabled sensors from a Python list of strings."""
        clean_sensors = [s.strip().lower() for s in sensors if s.strip()]
        self.enabled_sensors = "|".join(clean_sensors)

    @property
    def sensor_configs_dict(self) -> dict[str, dict[str, Any]]:
        """
        Return dict of per-sensor configurations:
        { "energy": { "baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh" }, ... }
        Provides sensible defaults if not explicitly configured.
        """
        defaults = {
            "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
            "water": {"baseline": 400.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
            "temperature": {"baseline": 24.0, "warning_threshold": 10.0, "critical_threshold": 20.0, "unit": "°C"},
            "air_quality": {"baseline": 50.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "AQI"},
            "waste": {"baseline": 50.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "kg"},
            "humidity": {"baseline": 55.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "%"},
            "co2": {"baseline": 600.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "ppm"},
            "traffic": {"baseline": 100.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "veh/h"},
            "parking": {"baseline": 80.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "%"},
            "assets": {"baseline": 95.0, "warning_threshold": 10.0, "critical_threshold": 20.0, "unit": "%"},
            "safety": {"baseline": 98.0, "warning_threshold": 5.0, "critical_threshold": 10.0, "unit": "%"},
            "climate": {"baseline": 25.0, "warning_threshold": 10.0, "critical_threshold": 20.0, "unit": "°C"},
        }
        if not self.sensor_configs:
            return defaults
        try:
            stored = json.loads(self.sensor_configs)
            merged = dict(defaults)
            for k, v in stored.items():
                if isinstance(v, dict):
                    k_lower = k.lower().strip()
                    def_sub = defaults.get(k_lower, {"baseline": 100.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": ""})
                    merged[k_lower] = {
                        "baseline": float(v.get("baseline", def_sub["baseline"])),
                        "warning_threshold": float(v.get("warning_threshold", def_sub["warning_threshold"])),
                        "critical_threshold": float(v.get("critical_threshold", def_sub["critical_threshold"])),
                        "unit": str(v.get("unit", def_sub["unit"])),
                    }
            return merged
        except Exception:
            return defaults

    def set_sensor_configs(self, configs: dict[str, dict[str, Any]]) -> None:
        """Serialize dictionary of sensor configurations to JSON."""
        self.sensor_configs = json.dumps(configs)

    def get_sensor_configs(self) -> dict[str, dict[str, Any]]:
        """Return dictionary of per-sensor configurations."""
        return self.sensor_configs_dict

    @property
    def energy_baseline(self) -> float:
        return float(self.sensor_configs_dict.get("energy", {}).get("baseline", 100.0))

    @property
    def energy_warning_threshold(self) -> float:
        b = self.energy_baseline
        pct = float(self.sensor_configs_dict.get("energy", {}).get("warning_threshold", 20.0))
        return round(b * (1.0 + pct / 100.0), 2)

    @property
    def energy_critical_threshold(self) -> float:
        b = self.energy_baseline
        pct = float(self.sensor_configs_dict.get("energy", {}).get("critical_threshold", 40.0))
        return round(b * (1.0 + pct / 100.0), 2)

    @property
    def water_baseline(self) -> float:
        return float(self.sensor_configs_dict.get("water", {}).get("baseline", 50.0))

    @property
    def water_warning_threshold(self) -> float:
        b = self.water_baseline
        pct = float(self.sensor_configs_dict.get("water", {}).get("warning_threshold", 20.0))
        return round(b * (1.0 + pct / 100.0), 2)

    @property
    def water_critical_threshold(self) -> float:
        b = self.water_baseline
        pct = float(self.sensor_configs_dict.get("water", {}).get("critical_threshold", 40.0))
        return round(b * (1.0 + pct / 100.0), 2)

    def __repr__(self) -> str:
        return (
            f"<OrganisationSensorConfig org={self.organisation_id!r} "
            f"mode={self.data_source!r} sensors={self.enabled_sensors!r}>"
        )


# ---------------------------------------------------------------------------
# IoT Device Registration & Credentials
# ---------------------------------------------------------------------------
class IoTDevice(Base):
    """
    Represents a physical or simulated IoT device (e.g. ESP32 / Wokwi)
    associated with an organisation.
    """
    __tablename__ = "iot_devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_name = Column(String(200), nullable=False)
    device_type = Column(String(100), nullable=False, default="ESP32")
    api_key_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="iot_devices")

    def __repr__(self) -> str:
        return f"<IoTDevice id={self.device_id!r} org={self.organisation_id!r} type={self.device_type!r}>"


# ---------------------------------------------------------------------------
# Facility Block Master Model
# ---------------------------------------------------------------------------
class FacilityBlock(Base):
    """
    Represents an organisation-specific physical block or facility section
    (e.g. Academic Block, Science Block, Library Block, Hostel Block).
    """
    __tablename__ = "facility_blocks"
    __table_args__ = (
        Index("idx_facility_blocks_org_block", "organisation_id", "block_id", unique=True),
        Index("idx_facility_blocks_org_name", "organisation_id", "block_name"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_id = Column(String(50), nullable=False, index=True)      # e.g. BLK-001
    block_name = Column(String(200), nullable=False)               # e.g. Academic Block
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True)

    # Relationships
    organisation = relationship("Organisation", back_populates="facility_blocks")

    def __repr__(self) -> str:
        return f"<FacilityBlock id={self.block_id!r} name={self.block_name!r} org={self.organisation_id!r}>"


# ---------------------------------------------------------------------------
# Municipality Ward Master Model
# ---------------------------------------------------------------------------
class MunicipalityWard(Base):
    """
    Represents an administrative civic ward under a Municipality.
    Wards are civic territorial subdivisions (e.g. Ward 11, Ward 5),
    strictly distinct from physical FacilityBlock records of buildings/offices.
    """
    __tablename__ = "municipality_wards"
    __table_args__ = (
        Index("idx_municipality_wards_org_ward", "municipality_id", "ward_number", unique=True),
        Index("idx_municipality_wards_org_name", "municipality_id", "ward_name"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    municipality_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ward_number = Column(String(50), nullable=False, index=True)   # e.g. "11", "5", "WRD-001"
    ward_name = Column(String(200), nullable=False)                # e.g. "nilesh sahi"
    zone = Column(String(100), nullable=True)                      # e.g. "North Zone"
    population = Column(Integer, nullable=True)
    area_sq_km = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True)

    # Relationships
    municipality = relationship("Organisation", back_populates="municipality_wards")

    def __repr__(self) -> str:
        return f"<MunicipalityWard num={self.ward_number!r} name={self.ward_name!r} muni={self.municipality_id!r}>"


# ---------------------------------------------------------------------------
# Event Read State (Admin New/Unseen Notification Persistence)
# ---------------------------------------------------------------------------
class EventReadState(Base):
    """
    Stores persistent read/viewed state for operational events (anomalies, alerts)
    per admin user and organisation.
    """
    __tablename__ = "event_read_states"
    __table_args__ = (
        Index("idx_event_read_user_event", "user_id", "event_type", "event_id", unique=True),
        Index("idx_event_read_org_user", "organisation_id", "user_id"),
        Index("idx_event_read_user_metric", "user_id", "metric"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organisation_id = Column(
        String(50),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False, default="anomaly")
    event_id = Column(String(36), nullable=False, index=True)
    metric = Column(String(50), nullable=False, index=True)
    block_id = Column(String(50), nullable=True, index=True)
    read_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    organisation = relationship("Organisation")

    def __repr__(self) -> str:
        return (
            f"<EventReadState user={self.user_id!r} org={self.organisation_id!r} "
            f"type={self.event_type!r} event={self.event_id!r} metric={self.metric!r} block={self.block_id!r}>"
        )


# ---------------------------------------------------------------------------
# Platform State (Platform-wide configuration and lifecycle flags)
# ---------------------------------------------------------------------------
class PlatformState(Base):
    """
    Stores platform-level state flags and metadata (e.g. destructive reset / clear all data flag).
    """
    __tablename__ = "platform_state"

    key = Column(String(100), primary_key=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def __repr__(self) -> str:
        return f"<PlatformState key={self.key!r} value={self.value!r}>"



