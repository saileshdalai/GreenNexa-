// GreenNexa TypeScript Interfaces & API Types

export type UserRole = "SUPER_ADMIN" | "ADMIN";
export type OrganisationOwnershipType = "GOVERNMENT" | "PRIVATE";
export type OrganisationType = "Commercial" | "Industrial" | "Residential" | "Educational" | "Healthcare" | "Other";
export type DataSourceType = "synthetic" | "iot";
export type SensorMetricType = "energy" | "water" | "temperature" | "humidity" | "co2" | "waste";
export type AnomalySeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type RecommendationPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type RecommendationStatus = "OPEN" | "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "DISMISSED" | "ACTIONED";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: UserRole;
  organisation_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  last_login_at?: string;
}

export interface Organisation {
  id: string;
  name: string;
  ownership_type?: OrganisationOwnershipType;
  org_type?: string;
  facility_name?: string;
  state?: string;
  district?: string;
  city?: string;
  address?: string;
  org_code?: string;
  location?: string;
  contact_email?: string;
  contact_phone?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  enabled_modules?: string[];
  iot_devices_count?: number;
  admin_name?: string;
  admin_email?: string;
}

export interface OrganisationListResponse {
  total: number;
  items: Organisation[];
}

export interface OrganisationSensorConfig {
  id?: string;
  organisation_id: string;
  data_source: DataSourceType;
  enabled_sensors?: string[];
  enabled_modules?: string[];
  enable_energy?: boolean;
  enable_water?: boolean;
  enable_waste?: boolean;
  enable_temperature?: boolean;
  enable_humidity?: boolean;
  enable_co2?: boolean;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DashboardKPIs {
  organisation_id: string;
  organisation_name: string;
  data_source: DataSourceType;
  kpis?: Record<string, {
    sensor_type: string;
    unit?: string;
    latest_value?: number;
    average?: number;
    minimum?: number;
    maximum?: number;
    reading_count?: number;
    latest_timestamp?: string;
    is_anomaly?: boolean;
    anomaly_severity?: string;
  }>;
  metrics?: {
    energy?: { current: number; unit: string; trend_pct?: number };
    water?: { current: number; unit: string; trend_pct?: number };
    waste?: { current: number; unit: string; trend_pct?: number };
    temperature?: { current: number; unit: string };
    humidity?: { current: number; unit: string };
    co2?: { current: number; unit: string };
    [key: string]: any;
  };
  anomaly_count?: number;
  active_anomaly_count?: number;
  optimal_score?: number;
  open_recommendations_count?: number;
  system_status?: "operational" | "degraded" | "warning";
  last_updated?: string;
  last_updated_at?: string;
}

export interface SensorReading {
  id: string;
  organisation_id: string;
  sensor_type: SensorMetricType;
  value: number;
  unit: string;
  source: DataSourceType;
  device_id?: string;
  timestamp: string;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  sensor_type?: SensorMetricType;
  unit?: string;
  source?: DataSourceType;
  is_anomaly?: boolean;
  anomaly_severity?: string | null;
}

export interface MetricStatistics {
  sensor_type: SensorMetricType;
  count: number;
  min: number;
  max: number;
  average: number;
  unit: string;
  period: string;
}

export interface ForecastPoint {
  timestamp: string;
  predicted_value: number;
  lower_bound?: number;
  upper_bound?: number;
}

export interface ForecastResponse {
  organisation_id: string;
  sensor_type: SensorMetricType;
  horizon: string;
  model: string;
  data_source: DataSourceType;
  unit?: string;
  generated_at?: string;
  is_available?: boolean;
  status_message?: string;
  mode?: string;
  selected_window?: string;
  available_days?: number;
  required_days?: number;
  current_value?: number;
  historical_comparison?: string;
  basis?: string;
  assumptions?: string;
  forecast: ForecastPoint[];
}

export interface AnomalyRecord {
  id: string;
  organisation_id: string;
  facility_id?: string;
  block_id?: string;
  metric?: string;
  sensor_type?: SensorMetricType | string;
  value: number;
  unit?: string;
  expected_min?: number;
  expected_max?: number;
  expected_value?: number;
  score?: number;
  anomaly_score?: number;
  severity: AnomalySeverity;
  status: string;
  source?: DataSourceType;
  timestamp: string;
  description?: string;
  reason?: string;
  created_at?: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

export interface AnomalyListResponse {
  total: number;
  items: AnomalyRecord[];
}

export interface AIRecommendation {
  id: string;
  organisation_id: string;
  facility_id?: string;
  block_id?: string;
  anomaly_id?: string;
  metric?: string;
  target_metric?: SensorMetricType | string;
  current_value?: number;
  expected_range_min?: number;
  expected_range_max?: number;
  priority: RecommendationPriority;
  severity?: string;
  historical_trend?: string;
  possible_causes?: string[];
  recommended_actions?: string[];
  title?: string;
  summary?: string;
  explanation?: string;
  confidence_note?: string;
  suggested_action?: string;
  status: RecommendationStatus;
  estimated_impact?: string;
  data_sufficient?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface RecommendationListResponse {
  total: number;
  items: AIRecommendation[];
}

export interface Message {
  id: string;
  sender_id: string;
  sender_email?: string;
  sender_name?: string;
  recipient_id: string;
  recipient_email?: string;
  recipient_name?: string;
  organisation_id: string;
  subject: string;
  body: string;
  is_read: boolean;
  created_at: string;
  read_at?: string;
}

export interface RecipientUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  organisation_id?: string;
}

export interface IoTDevice {
  id: string;
  device_id?: string;
  device_name?: string;
  organisation_id: string;
  organisation_name?: string;
  device_type?: string;
  sensor_type?: string;
  mac_address?: string;
  location?: string;
  status: "ONLINE" | "OFFLINE" | "DISABLED" | "online" | "offline";
  last_seen?: string;
  last_seen_at?: string;
  firmware_version?: string;
  source?: string;
}

// Super Admin Interfaces
export interface FacilityTypeItem {
  id: string;
  name: string;
  description: string;
}

export interface OrganisationOverviewItem {
  id: string;
  name: string;
  facility_type: string;
  location: string;
  admin_name: string;
  admin_email: string;
  enabled_modules: string[];
  iot_devices_count: number;
  status: "Active" | "Inactive";
  created_at: string;
}

export interface SuperAdminOverviewData {
  total_organisations: number;
  active_organisations: number;
  total_admins: number;
  active_iot_devices: number;
  platform_alerts: number;
  critical_alerts: number;
  organisations: OrganisationOverviewItem[];
}

export interface FacilityBlock {
  id: string;
  organisation_id: string;
  block_id: string;
  block_name: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface BlockCreateItem {
  block_id?: string;
  block_name: string;
}

export interface TrendPointItem {
  timestamp: string;
  value: number;
  is_anomaly?: boolean;
  anomaly_severity?: string | null;
  baseline?: number | null;
  warning_threshold?: number | null;
  critical_threshold?: number | null;
}

export interface BlockComparisonItem {
  block_id: string;
  block_name: string;
  current_value: number;
  unit: string;
  status: string;
}

export interface PredictionRowItem {
  location: string;
  block_id?: string | null;
  current_value: number;
  predicted_value: number;
  change_pct_str: string;
  status: string;
}

export interface ModuleOverallResponse {
  organisation_id: string;
  organisation_name: string;
  module_id: string;
  module_title: string;
  unit: string;
  current_value: number;
  average: number;
  peak: number;
  change_pct_str: string;
  status: string;
  open_anomalies_count: number;
  has_sufficient_history: boolean;
  trend_points: TrendPointItem[];
  block_comparison: BlockComparisonItem[];
  prediction_table: PredictionRowItem[];
  baseline?: number | null;
  warning_threshold?: number | null;
  critical_threshold?: number | null;
}

export interface ModuleBlockDetailResponse {
  organisation_id: string;
  organisation_name: string;
  module_id: string;
  module_title: string;
  block_id: string;
  block_name: string;
  unit: string;
  current_value: number;
  average: number;
  peak: number;
  change_pct_str: string;
  status: string;
  has_sufficient_history: boolean;
  trend_points: TrendPointItem[];
  prediction?: PredictionRowItem | null;
  anomalies: any[];
  recommendations: any[];
  active_anomalies_count?: number;
  active_recommendations_count?: number;
  baseline?: number | null;
  warning_threshold?: number | null;
  critical_threshold?: number | null;
}

export interface FullOrganisationCreatePayload {
  name: string;
  ownership_type?: OrganisationOwnershipType;
  facility_type: string;
  facility_name?: string;
  state: string;
  district: string;
  city: string;
  address: string;
  org_code?: string;
  admin_name: string;
  admin_user_id?: string;
  admin_email?: string;
  admin_phone?: string;
  admin_password: string;
  blocks?: BlockCreateItem[];
  wards?: { ward_name: string; ward_number?: string; zone?: string; population?: number; area_sq_km?: number }[];
  municipality_setup_type?: "NORMAL_MUNICIPALITY" | "OWN_OFFICE";
  enabled_modules: string[];
  sensor_configs?: Record<string, { baseline: number; warning_threshold: number; critical_threshold: number; unit?: string }>;
}

export interface SuperAdminUserItem {
  id: string;
  full_name: string;
  email: string;
  phone?: string;
  role: string;
  organisation_id?: string;
  organisation_name?: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface SensorConfigOverviewItem {
  organisation_id: string;
  organisation_name: string;
  facility_type: string;
  data_source: string;
  enabled_modules: string[];
  sensor_configs?: Record<string, { baseline: number; warning_threshold: number; critical_threshold: number; unit?: string }>;
  is_active: boolean;
  updated_at?: string;
}

export interface PlatformAlertItem {
  id: string;
  title: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  category: string;
  organisation_id?: string;
  organisation_name?: string;
  description: string;
  created_at: string;
}

/** Minimal summary of a GOVERNMENT-owned org, used for municipality association. */
export interface GovernmentOrgItem {
  id: string;
  name: string;
  org_type?: string;
  ownership_type?: string;
  location?: string;
  is_active: boolean;
}

export interface FullOrganisationConfigResponse {
  organisation_id: string;
  organisation_name: string;
  ownership_type?: string;
  facility_type: string;
  facility_name?: string;
  state?: string;
  district?: string;
  city?: string;
  address?: string;
  org_code?: string;
  location?: string;
  contact_email?: string;
  contact_phone?: string;
  is_active: boolean;
  admin_name: string;
  admin_user_id: string;
  admin_email: string;
  admin_phone?: string;
  enabled_modules: string[];
  sensor_configs: Record<string, any>;
  blocks: Array<{ block_id: string; block_name: string; is_active?: boolean }>;
  created_at: string;
  updated_at?: string;
}

/** Municipality → Government org association payload. */
export interface MunicipalityAssociation {
  associated_gov_org_ids: string[];
}

/** Full summary of a Government org returned in the associated-government-orgs endpoint. */
export interface AssociatedGovOrg {
  id: string;
  name: string;
  org_type?: string;
  ownership_type?: string;
  location?: string;
  is_active: boolean;
  contact_email?: string;
  org_code?: string;
}

export interface OrganisationStorageItem {
  organisation_id: string;
  organisation_name: string;
  ownership_type: string;
  logical_storage_bytes: number;
  logical_storage_formatted: string;
  percentage_of_total: number;
  readings_count: number;
  anomalies_count: number;
  recommendations_count: number;
  blocks_count: number;
  wards_count: number;
  devices_count: number;
  messages_count: number;
}

export interface StorageOverviewResponse {
  database_size_bytes: number;
  database_size_formatted: string;
  total_allocated_bytes?: number | null;
  total_allocated_formatted?: string | null;
  available_bytes?: number | null;
  available_formatted?: string | null;
  usage_percentage?: number | null;
  government_total_logical_bytes: number;
  government_total_logical_formatted: string;
  private_total_logical_bytes: number;
  private_total_logical_formatted: string;
  total_logical_bytes: number;
  total_logical_formatted: string;
  organisations: OrganisationStorageItem[];
  generated_at: string;
  database_path?: string | null;
  database_engine: string;
}

