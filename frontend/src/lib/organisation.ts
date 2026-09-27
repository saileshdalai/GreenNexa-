/**
 * GreenNexa — Authoritative Organisation Helpers.
 */

export function isMunicipality(orgOrType: any): boolean {
  if (!orgOrType) return false;
  const raw =
    typeof orgOrType === "string"
      ? orgOrType
      : orgOrType.org_type || orgOrType.facility_type || orgOrType.type || "";
  const t = raw.toString().trim().toLowerCase();

  // Explicitly disallow Municipal Office (normal organisation)
  if (t === "municipal office" || t === "municipal_office") {
    return false;
  }

  return t === "municipality" || t === "municipality_civic";
}
