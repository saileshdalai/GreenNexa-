/**
 * GreenNexa — Centralized Master Sensor Catalog & Default Type Mappings (Frontend).
 *
 * Single Source of Truth for sensor definitions, categories, default units,
 * baselines, thresholds, and organisation/facility type-specific recommended sensors.
 */

export interface SensorDefinition {
  id: string;
  name: string;
  category: "CORE" | "MUNICIPALITY / OUTDOOR" | "ASSET / UTILISATION" | "INDUSTRIAL";
  metric: string;
  unit: string;
  defaultBaseline: number;
  defaultWarn: number;
  defaultCrit: number;
  description: string;
}

export const MASTER_SENSOR_CATALOG: SensorDefinition[] = [
  // CORE
  {
    id: "energy",
    name: "Energy",
    category: "CORE",
    metric: "Active Electrical Power",
    unit: "kWh",
    defaultBaseline: 1000,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Total facility electrical power draw and cumulative energy consumption.",
  },
  {
    id: "water",
    name: "Water",
    category: "CORE",
    metric: "Water Consumption",
    unit: "L",
    defaultBaseline: 400,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Mains potable water usage and cumulative fluid volume.",
  },
  {
    id: "temperature",
    name: "Temperature",
    category: "CORE",
    metric: "Ambient Temperature",
    unit: "°C",
    defaultBaseline: 24,
    defaultWarn: 10,
    defaultCrit: 20,
    description: "Ambient dry-bulb environmental room and zone temperature.",
  },
  {
    id: "humidity",
    name: "Humidity",
    category: "CORE",
    metric: "Relative Humidity",
    unit: "%",
    defaultBaseline: 55,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Indoor air relative humidity percentage.",
  },
  {
    id: "co2",
    name: "CO2",
    category: "CORE",
    metric: "Carbon Dioxide Concentration",
    unit: "ppm",
    defaultBaseline: 600,
    defaultWarn: 25,
    defaultCrit: 50,
    description: "Indoor air quality CO2 parts-per-million concentration.",
  },
  {
    id: "waste",
    name: "Waste",
    category: "CORE",
    metric: "Container Fill Level",
    unit: "%",
    defaultBaseline: 40,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Smart bin solid waste fill level percentage.",
  },

  // MUNICIPALITY / OUTDOOR
  {
    id: "air_quality",
    name: "Air Quality",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Air Quality Index (AQI)",
    unit: "AQI",
    defaultBaseline: 50,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Composite outdoor/indoor Air Quality Index rating.",
  },
  {
    id: "traffic",
    name: "Traffic",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Traffic Flow Volume",
    unit: "veh/h",
    defaultBaseline: 150,
    defaultWarn: 25,
    defaultCrit: 50,
    description: "Corridor traffic throughput and congestion monitoring.",
  },
  {
    id: "parking",
    name: "Parking",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Parking Space Occupancy",
    unit: "%",
    defaultBaseline: 70,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Civic parking bay utilization and occupancy percentage.",
  },
  {
    id: "water_flow",
    name: "Water Flow",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Pipeline Flow Rate",
    unit: "L/min",
    defaultBaseline: 120,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Water main distribution flow rate.",
  },
  {
    id: "water_level",
    name: "Water Level",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Reservoir / Tank Level",
    unit: "%",
    defaultBaseline: 75,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Water overhead tank and distribution sump level percentage.",
  },
  {
    id: "sewage_level",
    name: "Sewage / Drainage Level",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Drainage Sump Level",
    unit: "%",
    defaultBaseline: 35,
    defaultWarn: 25,
    defaultCrit: 50,
    description: "Stormwater drain and sewage sump fill level percentage.",
  },
  {
    id: "rainfall",
    name: "Rainfall",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Precipitation Rate",
    unit: "mm",
    defaultBaseline: 5,
    defaultWarn: 50,
    defaultCrit: 100,
    description: "Precipitation gauge depth per hour.",
  },
  {
    id: "street_lighting",
    name: "Street Lighting",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Street Lighting Load",
    unit: "kWh",
    defaultBaseline: 400,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Public street light network cumulative energy load and faults.",
  },
  {
    id: "roads",
    name: "Roads & Infrastructure",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Road Condition Index",
    unit: "%",
    defaultBaseline: 85,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Pavement and civic road infrastructure health percentage.",
  },
  {
    id: "parks",
    name: "Parks & Playgrounds",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Park Health Index",
    unit: "%",
    defaultBaseline: 60,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Public park, playground and green space upkeep index.",
  },
  {
    id: "sewage",
    name: "Drainage & Sewage",
    category: "MUNICIPALITY / OUTDOOR",
    metric: "Sewage Network Health",
    unit: "%",
    defaultBaseline: 40,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Civic sewage and drainage network health / pressure percentage.",
  },

  // ASSET / UTILISATION
  {
    id: "equipment_asset",
    name: "Equipment / Asset",
    category: "ASSET / UTILISATION",
    metric: "Asset Health Score",
    unit: "%",
    defaultBaseline: 95,
    defaultWarn: 10,
    defaultCrit: 20,
    description: "Operational health, availability, and uptime efficiency of machinery.",
  },
  {
    id: "occupancy",
    name: "Occupancy",
    category: "ASSET / UTILISATION",
    metric: "Space Utilization Rate",
    unit: "%",
    defaultBaseline: 65,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Footfall counter and space capacity utilization percentage.",
  },

  // INDUSTRIAL
  {
    id: "vibration",
    name: "Vibration",
    category: "INDUSTRIAL",
    metric: "RMS Vibration Velocity",
    unit: "mm/s",
    defaultBaseline: 2.5,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Motor and pump rotational vibration velocity.",
  },
  {
    id: "pressure",
    name: "Pressure",
    category: "INDUSTRIAL",
    metric: "System Fluid Pressure",
    unit: "bar",
    defaultBaseline: 6.0,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Hydraulic or pneumatic line gauge pressure.",
  },
  {
    id: "flow",
    name: "Flow",
    category: "INDUSTRIAL",
    metric: "Process Flow Rate",
    unit: "L/min",
    defaultBaseline: 100,
    defaultWarn: 20,
    defaultCrit: 40,
    description: "Industrial coolant or chemical dosing line flow.",
  },
  {
    id: "current_voltage",
    name: "Current / Voltage",
    category: "INDUSTRIAL",
    metric: "Phase Voltage / Current",
    unit: "A",
    defaultBaseline: 415,
    defaultWarn: 10,
    defaultCrit: 20,
    description: "Three-phase electric feeder line voltage and phase current.",
  },
  {
    id: "rpm",
    name: "RPM",
    category: "INDUSTRIAL",
    metric: "Rotational Speed",
    unit: "RPM",
    defaultBaseline: 1450,
    defaultWarn: 10,
    defaultCrit: 25,
    description: "Shaft tachometer revolutions per minute.",
  },
  {
    id: "machine_temperature",
    name: "Machine Temperature",
    category: "INDUSTRIAL",
    metric: "Bearing Temperature",
    unit: "°C",
    defaultBaseline: 65,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Equipment motor casing and bearing temperature.",
  },
  {
    id: "runtime_hours",
    name: "Runtime / Operating Hours",
    category: "INDUSTRIAL",
    metric: "Operating Hours Counter",
    unit: "hrs",
    defaultBaseline: 16,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Cumulative continuous machine duty hours per cycle.",
  },
  {
    id: "acoustic_sound",
    name: "Acoustic / Sound",
    category: "INDUSTRIAL",
    metric: "Acoustic Sound Pressure",
    unit: "dB",
    defaultBaseline: 68,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Decibel sound intensity and bearing noise monitor.",
  },
  {
    id: "gas",
    name: "Gas",
    category: "INDUSTRIAL",
    metric: "Hazardous Gas Level",
    unit: "ppm",
    defaultBaseline: 10,
    defaultWarn: 30,
    defaultCrit: 60,
    description: "Toxic gas / methane / VOC concentration ppm.",
  },
  {
    id: "dust_pm",
    name: "Dust / PM",
    category: "INDUSTRIAL",
    metric: "Particulate Matter PM10",
    unit: "µg/m³",
    defaultBaseline: 45,
    defaultWarn: 25,
    defaultCrit: 50,
    description: "Industrial workshop dust and suspended particulate monitor.",
  },
  {
    id: "fire_smoke",
    name: "Fire / Smoke",
    category: "INDUSTRIAL",
    metric: "Optical Smoke Obscuration",
    unit: "idx",
    defaultBaseline: 2,
    defaultWarn: 50,
    defaultCrit: 100,
    description: "Early detection optical obscuration index.",
  },
  {
    id: "oil_fluid_level",
    name: "Oil / Fluid Level",
    category: "INDUSTRIAL",
    metric: "Lube Oil Reservoir Level",
    unit: "%",
    defaultBaseline: 85,
    defaultWarn: 15,
    defaultCrit: 30,
    description: "Hydraulic / lubricant sump level percentage.",
  },
];

export const SENSOR_CATALOG_MAP = new Map<string, SensorDefinition>(
  MASTER_SENSOR_CATALOG.map((s) => [s.id, s])
);

/**
 * Standard recommended default sensors per organisation / facility type.
 */
export const RECOMMENDED_SENSORS_BY_TYPE: Record<string, string[]> = {
  // 1. Hospital
  hospital: [
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
  // 2. School
  school: [
    "energy",
    "water",
    "waste",
    "air_quality",
    "temperature",
    "humidity",
    "occupancy",
    "safety",
  ],
  // 3. College / University
  college: [
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
  // 4. Ward Office
  ward_office: [
    "energy",
    "water",
    "waste",
    "air_quality",
    "occupancy",
    "safety",
  ],
  // 5. Water Pump Station
  water_pump_station: [
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
  // 6. Municipal Office
  municipal_office: [
    "energy",
    "water",
    "waste",
    "air_quality",
    "occupancy",
    "parking",
    "safety",
  ],
  // 7. Community Facility
  community_facility: [
    "energy",
    "water",
    "waste",
    "air_quality",
    "temperature",
    "humidity",
    "occupancy",
    "safety",
  ],
  // 8. Municipality
  municipality: [
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
  // 9. Industrial Organisation
  industrial: [
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
  // 10. Park / Community Park
  park: [
    "energy",
    "water",
    "water_flow",
    "air_quality",
    "rainfall",
    "temperature",
    "humidity",
    "safety",
  ],
};

export function normalizeTypeKey(orgType?: string | null): string {
  if (!orgType) return "community_facility";
  const t = orgType.toLowerCase().trim();
  if (t.includes("municipality")) return "municipality";
  if (t.includes("hospital") || t.includes("health")) return "hospital";
  if (t.includes("school")) return "school";
  if (t.includes("college") || t.includes("universit")) return "college";
  if (t.includes("ward")) return "ward_office";
  if (t.includes("pump")) return "water_pump_station";
  if (t.includes("municipal office")) return "municipal_office";
  if (t.includes("industrial") || t.includes("manufactur")) return "industrial";
  if (t.includes("park")) return "park";
  if (t.includes("community")) return "community_facility";
  return "community_facility";
}

export function getRecommendedSensorsForType(orgType?: string | null): string[] {
  const key = normalizeTypeKey(orgType);
  return RECOMMENDED_SENSORS_BY_TYPE[key] || RECOMMENDED_SENSORS_BY_TYPE["community_facility"];
}

export function getDefaultConfigsForSensors(sensorIds: string[]): Record<string, { baseline: number; warning_threshold: number; critical_threshold: number; unit: string }> {
  const res: Record<string, { baseline: number; warning_threshold: number; critical_threshold: number; unit: string }> = {};
  for (const sid of sensorIds) {
    const def = SENSOR_CATALOG_MAP.get(sid);
    if (def) {
      res[sid] = {
        baseline: def.defaultBaseline,
        warning_threshold: def.defaultWarn,
        critical_threshold: def.defaultCrit,
        unit: def.unit,
      };
    } else {
      res[sid] = {
        baseline: 100,
        warning_threshold: 15,
        critical_threshold: 30,
        unit: "",
      };
    }
  }
  return res;
}
