"""
GreenNexa AI Assistant — Multilingual Natural Language Understanding & Generation.

Supports English, Hinglish, Odia (Unicode Script), and Roman Odia queries.
Produces factually grounded, explainable responses strictly based on GreenNexa operational data.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class GreenNexaNLU:
    """
    Multilingual intent classification, entity parsing, and response formulation.
    """

    ODIA_SCRIPT_REGEX = re.compile(r"[\u0b00-\u0b7f]+")

    ODIA_KEYWORDS = {
        "kete", "badhichi", "sabuthu", "besi", "keun", "achhi", "aji", "kn", "pain",
        "heichi", "re", "karantu", "ku", "tebe", "adhika", "kamti", "bhalare", "mo",
        "ethire", "seithi", "dekhantu", "thila", "tethipain", "uchit", "kichi", "saburi",
        "ko", "hauchhi", "baisichi", "janiba", "achhanti", "keteta"
    }

    HINGLISH_KEYWORDS = {
        "aaj", "kyu", "kyun", "kitna", "kaha", "kahan", "kaunsa", "sabse", "zyada",
        "jyada", "kam", "hai", "kya", "batao", "batayein", "chal", "raha", "rahi",
        "hua", "hui", "kaise", "karein", "dekhna", "hoga", "wali", "wale", "kis", "kitne"
    }

    METRIC_ALIASES = {
        "energy": ["energy", "power", "electricity", "kwh", "bijuli", "current", "ଶକ୍ତି", "ବିଜୁଳି"],
        "water": ["water", "pani", "jala", "litre", "tap", "leakage", "ଜଳ", "ପାଣି"],
        "waste": ["waste", "trash", "garbage", "bin", "abarjana", "kachra", "ଆବର୍ଜନା"],
        "temperature": ["temperature", "temp", "thermal", "heat", "garmi", "tapamatra", "ତାପମାତ୍ରା"],
        "humidity": ["humidity", "moisture", "ardrata", "ଆର୍ଦ୍ରତା"],
        "co2": ["co2", "carbon", "ppm"],
        "air_quality": ["air_quality", "aqi", "air", "bata", "ବାୟୁ"],
        "traffic": ["traffic", "vehicle", "vehicles"],
        "parking": ["parking", "slot", "slots"],
        "assets": ["assets", "equipment", "asset"],
        "safety": ["safety", "suraksha", "hazard"],
        "climate": ["climate", "weather"],
    }

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Classify input text into 'odia', 'roman_odia', 'hinglish', or 'english'."""
        if cls.ODIA_SCRIPT_REGEX.search(text):
            return "odia"

        tokens = set(re.findall(r"\b\w+\b", text.lower()))
        odia_matches = tokens.intersection(cls.ODIA_KEYWORDS)
        hinglish_matches = tokens.intersection(cls.HINGLISH_KEYWORDS)

        if len(odia_matches) >= 1:
            return "roman_odia"
        if len(hinglish_matches) >= 1:
            return "hinglish"
        return "english"

    @classmethod
    def check_language_mismatch(cls, text: str, selected_language: str) -> Tuple[bool, str, str]:
        """
        Check if input query language conflicts with selected conversation language.
        Returns: (has_mismatch, detected_language, mismatch_note_prefix)
        """
        detected = cls.detect_language(text)
        sel = (selected_language or "english").lower().strip()

        if detected == sel:
            return False, detected, ""

        # Language display names
        lang_names = {
            "english": "English",
            "hinglish": "Hinglish",
            "odia": "Odia (ଓଡ଼ିଆ)",
            "roman_odia": "Roman Odia",
        }
        det_label = lang_names.get(detected, detected)

        if sel == "english":
            note = f"(Note: You have selected English as your assistant language, but your query appeared to be in {det_label}. Responding in English:)\n\n"
        elif sel == "hinglish":
            note = f"(Note: Aapne Hinglish select kiya hai, lekin aapki query {det_label} me lagi. Hinglish me uttar:)\n\n"
        elif sel == "odia":
            note = f"(ସୂଚନା: ଆପଣ ଓଡ଼ିଆ ବାଛିଛନ୍ତି, କିନ୍ତୁ ଆପଣଙ୍କ ପ୍ରଶ୍ନ {det_label} ରେ ପ୍ରତୀତ ହେଉଛି। ଓଡ଼ିଆରେ ଉତ୍ତର:)\n\n"
        elif sel == "roman_odia":
            note = f"(Note: Apana Roman Odia select karichhanti, kintu apanka prashna {det_label} re thila. Roman Odia re uttara:)\n\n"
        else:
            note = ""

        return True, detected, note

    @classmethod
    def extract_entities(
        cls,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract metric, block_id, severity, and intent signals from query and screen context."""
        lower = text.lower()
        context = context or {}

        # 1. Metric extraction from text
        detected_metric = None
        for metric, aliases in cls.METRIC_ALIASES.items():
            for alias in aliases:
                if re.search(r"(?:^|\b|\s)" + re.escape(alias) + r"(?:\b|\s|$)", lower, re.UNICODE):
                    detected_metric = metric
                    break
            if detected_metric:
                break

        explicit_metric = detected_metric is not None

        # Fallback to screen context module if metric not in query text
        if not detected_metric and context.get("module"):
            mod = str(context.get("module")).lower().strip()
            if mod in cls.METRIC_ALIASES:
                detected_metric = mod

        # 2. Block extraction
        detected_block = None
        block_match = re.search(r"\bblock[-\s]([a-z0-9]+)\b", lower)
        if block_match:
            detected_block = f"Block {block_match.group(1).upper()}"
        else:
            for b_keyword in ["science", "engineering", "academic", "library", "hostel", "tower", "hospital", "wing"]:
                if b_keyword in lower:
                    detected_block = b_keyword.capitalize()
                    break

        if not detected_block and context.get("block_id"):
            detected_block = context.get("block_id")

        # 3. Facility Type extraction
        detected_facility_type = None
        facility_type_keywords = {
            "school": ["school", "schools", "school org", "school organisation", "school facility", "ସ୍କୁଲ"],
            "college": ["college", "colleges", "university", "universities", "kolege", "କଲେଜ"],
            "hospital": ["hospital", "hospitals", "medical", "ହସ୍ପିଟାଲ", "হাসপাতাল"],
            "municipality": ["municipality", "municipal", "civic", "ପୌରପାଳିକା"],
            "industrial": ["industrial", "factory", "factories", "ଶିଳ୍ପ"],
            "public_sector": ["public sector", "government", "govt"],
        }

        for f_type, kw_list in facility_type_keywords.items():
            if any(re.search(r"(?:^|\b|\s)" + re.escape(kw) + r"(?:\b|\s|$)", lower, re.UNICODE) for kw in kw_list):
                detected_facility_type = f_type
                break

        # 4. Intent classification
        intent = "general_query"
        has_block_q = any(w in lower for w in ["ko block", "keun block", "kis block", "which block", "କେଉଁ ବ୍ଲକ", "block"])
        has_highest = any(w in lower for w in ["highest", "sabuthu besi", "sabse zyada", "sabse jyada", "maximum", "peak", "adhika", "adhik", "zyada", "jyada", "besi", "ଅଧିକ", "ସବୁଠାରୁ"])

        # PLATFORM INTENT PATTERNS
        if detected_facility_type and any(w in lower for w in [
            "how many", "total", "count", "kete", "keteta", "kitne", "kitni", "ସଂଖ୍ୟା", "କେତୋଟି"
        ]):
            intent = "organisation_count_by_facility_type"

        elif any(w in lower for w in [
            "total organization", "total organisation", "organization count", "organisation count",
            "keteta organization", "keteta organisation", "organization kete", "organisation kete",
            "how many organisation", "how many organization", "how many org", "total org",
            "kitne organisation", "kitni organisation", "kitne org", "mo platform re kete organisation",
            "keteta org", "ମୋଟ ସଂସ୍ଥା", "କେତୋଟି ସଂସ୍ଥା", "ସଂସ୍ଥା ସଂଖ୍ୟା"
        ]):
            intent = "organisation_count"

        elif any(w in lower for w in [
            "total admin", "admin count", "how many admin", "how many admins",
            "keteta admin", "admin kete", "kitne admin", "kitni admin",
            "ମୋଟ ଆଡମିନ୍", "କେତୋଟି ଆଡମିନ୍"
        ]):
            intent = "admin_count"

        elif any(w in lower for w in [
            "ke ke organisation", "ke ke organization", "keun organisation sabu", "keun organization sabu",
            "list organisation", "list organization", "show all organisation", "which organisation exist",
            "kaun kaun se organisation", "kaun se organisation", "ସଂସ୍ଥା ତାଲିକା", "କେଉଁ କେଉଁ ସଂସ୍ଥା"
        ]):
            intent = "organisation_list"

        elif any(w in lower for w in [
            "which organisation has highest", "which organization has highest",
            "which organisation has most", "which organization has most",
            "compare organisation", "compare organization",
            "organisations comparison", "organisation comparison",
            "keun organisation re besi", "keun organization re besi",
            "sabuthu besi anomalies keun", "kis organisation me sabse",
            "କେଉଁ ସଂସ୍ଥାରେ ସବୁଠାରୁ"
        ]):
            intent = "organisation_comparison"

        elif any(w in lower for w in [
            "overall platform status", "platform summary", "platform health", "system overview",
            "platform status", "platform overview", "ପ୍ଲାଟଫର୍ମ ସ୍ଥିତି"
        ]):
            intent = "platform_summary"

        elif any(w in lower for w in [
            "what if", "what-if", "scenario", "simulate", "kam chalile", "reduce kale",
            "reduce kare", "reduce karein", "kam kare", "kam karein", "badhayein", "badhaile",
            "kete heba", "kana heba", "kitna bachega", "kitna hoga", "kya hoga", "how much will",
            "ac 2 ghanta", "ac 1 ghanta", "ac 3 ghanta", "thermostat", "solar offset"
        ]):
            intent = "scenario_simulation"
            if not detected_metric:
                if any(w in lower for w in ["water", "pani", "paani"]):
                    detected_metric = "water"
                elif any(w in lower for w in ["waste", "kachra", "bin"]):
                    detected_metric = "waste"
                elif any(w in lower for w in ["traffic", "car", "parking", "shuttle"]):
                    detected_metric = "traffic"
                else:
                    detected_metric = "energy"

        elif any(w in lower for w in ["why", "kn pain", "kyu", "kyun", "reason", "cause", "spike", "abnormal", "କାହିଁକି", "କାରଣ"]):
            intent = "explain_anomaly_or_spike"
        elif has_highest or (has_block_q and any(w in lower for w in ["besi", "adhika", "zyada", "highest", "more"])):
            intent = "find_highest_block"
        elif any(w in lower for w in ["compare", "tulanatmak", "across organisations", "all org", "ତୁଳନା"]):
            intent = "compare_entities"
        elif any(w in lower for w in ["forecast", "future", "aage", "predict", "ପୂର୍ବାନୁମାନ"]):
            intent = "forecast_query"
        elif any(w in lower for w in ["recommend", "action", "step", "kn kariba", "kya karein", "solution", "ସୁପାରିଶ"]):
            intent = "recommendation_query"
        elif any(w in lower for w in ["critical", "anomaly", "anomalies", "alert", "alerts", "ଆଲର୍ଟ"]):
            intent = "list_anomalies"
        elif any(w in lower for w in ["how much", "kete", "kitna", "baseline thu", "baseline se", "କେତେ"]):
            intent = "delta_from_baseline"
        elif any(w in lower for w in ["reading", "usage", "current", "aji", "aaj", "now", "level", "value", "status", "ଆଜି", "ବ୍ୟବହାର"]):
            intent = "current_reading"
        elif has_block_q:
            intent = "find_highest_block"

        return {
            "metric": detected_metric,
            "explicit_metric": explicit_metric,
            "block": detected_block,
            "facility_type": detected_facility_type,
            "intent": intent,
        }

    # =========================================================================
    # RESPONSE GENERATORS
    # =========================================================================

    @classmethod
    def generate_response(
        cls,
        language: str,
        intent: str,
        entities: Dict[str, Any],
        tool_data: Dict[str, Any],
        is_super_admin: bool = False,
    ) -> Tuple[str, Optional[str], List[str]]:
        """
        Generate grounded, natural response in matching language style.
        Returns: (reply_text, data_source_citation, suggested_followups)
        """
        lang = (language or "english").lower().strip()
        metric = entities.get("metric")
        block = entities.get("block")

        # 0A. PLATFORM INTENT: ORGANISATION COUNT
        if intent == "organisation_count":
            org_data = tool_data.get("organisation_count", {})
            total = org_data.get("total_organisations", 0)
            active = org_data.get("active_organisations", 0)

            if lang == "odia":
                reply = f"GreenNexa ରେ ବର୍ତ୍ତମାନ ମୋଟ **{total}** ଟି ସଂସ୍ଥା ପଞ୍ଜୀକୃତ ଅଛି ({active} ଟି ସକ୍ରିୟ)।"
            elif lang == "roman_odia":
                reply = f"GreenNexa re ebe total **{total}** ti organisation achhi ({active} ti active)."
            elif lang == "hinglish":
                reply = f"GreenNexa mein abhi total **{total}** organisations registered hain ({active} active)."
            else:
                reply = f"There are currently **{total}** organisations registered in GreenNexa ({active} active)."

            return reply, "Platform Database • Organisation Registry", [
                "List all registered organisations",
                "How many admin accounts are registered?",
                "Which organisation has highest energy usage?",
            ]

        # 0A1. PLATFORM INTENT: FACILITY TYPE ORGANISATION COUNT
        if intent == "organisation_count_by_facility_type":
            ft_data = tool_data.get("facility_type_count", {})
            total = ft_data.get("total_organisations", 0)
            active = ft_data.get("active_organisations", 0)
            f_type = ft_data.get("facility_type") or entities.get("facility_type") or "Facility"

            if lang == "odia":
                reply = f"GreenNexa ରେ ବର୍ତ୍ତମାନ ମୋଟ **{total}** ଟି **{f_type}** ସଂସ୍ଥା ପଞ୍ଜୀକୃତ ଅଛି ({active} ଟି ସକ୍ରିୟ)।"
            elif lang == "roman_odia":
                reply = f"GreenNexa re ebe total **{total}** ti **{f_type}** organisation achhi ({active} ti active)."
            elif lang == "hinglish":
                reply = f"GreenNexa mein abhi total **{total}** **{f_type}** organisations registered hain ({active} active)."
            else:
                reply = f"There are currently **{total}** **{f_type}** organisations registered in GreenNexa ({active} active)."

            return reply, "Platform Database • Organisation Registry", [
                "List all registered organisations",
                "How many total organisations?",
                "Which organisation has highest energy usage?",
            ]

        # 0B. PLATFORM INTENT: ADMIN COUNT
        if intent == "admin_count":
            admin_data = tool_data.get("admin_count", {})
            total = admin_data.get("total_admins", 0)

            if lang == "odia":
                reply = f"GreenNexa ରେ ବର୍ତ୍ତମାନ ମୋଟ **{total}** ଟି ଆଡମିନ୍ ଆକାଉଣ୍ଟ ପଞ୍ଜୀକୃତ ଅଛି।"
            elif lang == "roman_odia":
                reply = f"GreenNexa re ebe total **{total}** ti admin account achhanti."
            elif lang == "hinglish":
                reply = f"GreenNexa mein abhi total **{total}** admin accounts registered hain."
            else:
                reply = f"There are currently **{total}** admin accounts registered across all organisations."

            return reply, "Platform Database • User Registry", [
                "How many total organisations?",
                "List all organisations",
                "Show platform overview",
            ]

        # 0C. PLATFORM INTENT: ORGANISATION LIST
        if intent == "organisation_list":
            org_list = tool_data.get("organisation_list", {})
            items = org_list.get("organisations", [])
            total = org_list.get("total_organisations", len(items))

            if not items:
                if lang == "odia":
                    reply = "ବର୍ତ୍ତମାନ କୌଣସି ପଞ୍ଜୀକୃତ ସଂସ୍ଥା ନାହିଁ।"
                elif lang == "roman_odia":
                    reply = "GreenNexa re ebe konasi registered organisation nahi."
                elif lang == "hinglish":
                    reply = "GreenNexa mein abhi koi registered organisation nahi hai."
                else:
                    reply = "There are currently no registered organisations in the platform."
                return reply, "Platform Database • Organisation Catalog", ["How many total admins?"]

            lines = []
            if lang == "odia":
                lines.append(f"GreenNexa ରେ ପଞ୍ଜୀକୃତ ସଂସ୍ଥାସମୂହ (ମୋଟ {total} ଟି):")
                for o in items:
                    lines.append(f"- **{o['name']}** ({o['org_type']}, {o['location']})")
            elif lang == "roman_odia":
                lines.append(f"GreenNexa re registered organisations (total {total} ti):")
                for o in items:
                    lines.append(f"- **{o['name']}** ({o['org_type']}, {o['location']})")
            elif lang == "hinglish":
                lines.append(f"GreenNexa mein registered organisations (total {total}):")
                for o in items:
                    lines.append(f"- **{o['name']}** ({o['org_type']}, {o['location']})")
            else:
                lines.append(f"Currently registered organisations ({total} total):")
                for o in items:
                    lines.append(f"- **{o['name']}** ({o['org_type']}, {o['location']})")

            reply = "\n".join(lines)
            return reply, "Platform Database • Organisation Catalog", [
                "How many total admins?",
                "Which organisation has highest energy usage?",
                "Show platform overview",
            ]

        # 0D. PLATFORM INTENT: ORGANISATION COMPARISON
        if intent in ("organisation_comparison", "compare_entities"):
            comp = tool_data.get("org_comparison", {})
            ranked = comp.get("ranked_organisations", [])
            met = comp.get("metric", metric or "energy")

            if ranked:
                top_org = ranked[0]
                val = top_org.get("latest_value", 0)
                unit = top_org.get("unit", "")
                name = top_org.get("org_name", "N/A")

                if lang == "odia":
                    lines = [f"ସବୁଠାରୁ ଅଧିକ {met} ବ୍ୟବହାର କରୁଥିବା ସଂସ୍ଥା ହେଉଛି **{name}** ({val} {unit})።\n"]
                    lines.append("ସଂସ୍ଥାଗୁଡ଼ିକର ତୁଳନା:")
                    for o in ranked:
                        lines.append(f"- **{o['org_name']}**: {o['latest_value']} {o['unit']} (Active Anomalies: {o['active_anomalies']})")
                    reply = "\n".join(lines)
                elif lang == "roman_odia":
                    lines = [f"Sabuthu besi {met} usage **{name}** re achhi ({val} {unit}).\n"]
                    lines.append("Organisations tulana:")
                    for o in ranked:
                        lines.append(f"- **{o['org_name']}**: {o['latest_value']} {o['unit']} (Active Anomalies: {o['active_anomalies']})")
                    reply = "\n".join(lines)
                elif lang == "hinglish":
                    lines = [f"Sabse zyada {met} usage **{name}** me hai ({val} {unit}).\n"]
                    lines.append("Organisations ka comparison:")
                    for o in ranked:
                        lines.append(f"- **{o['org_name']}**: {o['latest_value']} {o['unit']} (Active Anomalies: {o['active_anomalies']})")
                    reply = "\n".join(lines)
                else:
                    lines = [f"**{name}** currently has the highest {met} usage at **{val} {unit}**.\n"]
                    lines.append("Organisation comparison breakdown:")
                    for o in ranked:
                        lines.append(f"- **{o['org_name']}**: {o['latest_value']} {o['unit']} (Active Anomalies: {o['active_anomalies']})")
                    reply = "\n".join(lines)

                return reply, "Super Admin Platform Engine • Cross-Tenant Metric Aggregator", [
                    "Compare water usage across organisations",
                    "List all registered organisations",
                    "Show platform health summary",
                ]

        # 0. UNRESOLVED AMBIGUOUS METRIC CLARIFICATION
        if intent in ("find_highest_block", "explain_anomaly_or_spike", "current_reading", "delta_from_baseline", "forecast_query") and not metric:
            if lang == "odia":
                reply = "ଆପଣ କେଉଁ ମେଟ୍ରିକ୍ (Energy, Water, Waste, Temperature ଇତ୍ୟାଦି) ର ତୁଳନା କିମ୍ବା ତଥ୍ୟ ଦେଖିବାକୁ ଚାହାନ୍ତି? କୃପା କରି ମେଟ୍ରିକ୍ ନାମ ସ୍ପଷ୍ଟ କରନ୍ତୁ।"
            elif lang == "roman_odia":
                reply = "Apana keun metric (Energy, Water, Waste, Temperature, ityadi) ra comparison ba reading dekhiba ku chahanchhanti? Krupaya metric name specify karantu."
            elif lang == "hinglish":
                reply = "Aap kis metric (Energy, Water, Waste, Temperature, aadi) ka comparison ya data dekhna chahte hain? Kripya metric mention karein."
            else:
                reply = "Which metric would you like to check or compare across facility blocks (Energy, Water, Waste, Temperature, etc.)?"

            return reply, "Metric Clarification Prompt", [
                "Which block has highest energy usage?",
                "Which block has highest water consumption?",
                "Show active anomalies",
            ]

        metric = metric or "energy"

        # 1. EXPLAIN ANOMALY / SPIKE
        if intent == "explain_anomaly_or_spike":
            current = tool_data.get("current_metric", {})
            anomalies = tool_data.get("anomalies", {}).get("anomalies", [])
            recs = tool_data.get("recommendations", {}).get("recommendations", [])

            if not current.get("available") and not anomalies:
                if lang == "odia":
                    reply = f"{metric.capitalize()} ପାଇଁ ପର୍ଯ୍ୟାପ୍ତ ସେନ୍ସର ତଥ୍ୟ କିମ୍ବା ଆନୋମାଲି ରେକର୍ଡ ଉପଲବ୍ଧ ନାହିଁ।"
                elif lang == "roman_odia":
                    reply = f"{metric.capitalize()} pain prapuri sensor data ba anomaly record available nahi. Tethipain spike ra exact reason confirm kariheba nahi."
                elif lang == "hinglish":
                    reply = f"{metric.capitalize()} ke liye sufficient sensor data ya anomaly record available nahi hai. Isliye increase ka exact reason confirm nahi kiya ja sakta."
                else:
                    reply = f"There is currently insufficient telemetry recorded for {metric} to determine a cause reliably."
                return reply, "Telemetry Cache (Insufficient Data)", ["Show active anomalies", "Check current readings"]

            val = current.get("value", "N/A")
            base = current.get("baseline", "N/A")
            pct = current.get("pct_diff_from_baseline", 0)
            unit = current.get("unit", "")
            loc = block or current.get("block_id") or "configured facilities"

            relevant_anom = next((a for a in anomalies if a["metric"] == metric), None)
            reason_text = relevant_anom["reason"] if relevant_anom else f"Reading is {pct}% above baseline threshold"

            relevant_rec = next((r for r in recs if r["metric"] == metric), None)
            actions = relevant_rec["actions"][0] if relevant_rec and relevant_rec.get("actions") else "Inspect associated equipment and supply lines"

            if lang == "odia":
                reply = (
                    f"{loc} ରେ {metric} ବ୍ୟବହାର {val} {unit} ଅଛି, ଯାହା ବେସଲାଇନ୍ ({base} {unit}) ଠାରୁ {pct}% ଅଧିକ। "
                    f"ଆନୋମାଲି କାରଣ: {reason_text}। "
                    f"ସୁପାରିଶ କରାଯାଇଥିବା ପଦକ୍ଷେପ: {actions}।"
                )
            elif lang == "roman_odia":
                reply = (
                    f"{loc} re {metric} usage {val} {unit} achhi, jaha baseline ({base} {unit}) thu {pct}% adhika. "
                    f"Anomaly reason: {reason_text}. "
                    f"Action: {actions}. (Decision-support suggestion)."
                )
            elif lang == "hinglish":
                reply = (
                    f"{loc} me {metric} consumption {val} {unit} record hua hai, jo baseline ({base} {unit}) se {pct}% zyada hai. "
                    f"Anomaly note: {reason_text}. "
                    f"Recommended action: {actions}."
                )
            else:
                reply = (
                    f"{metric.capitalize()} usage in {loc} is currently {val} {unit}, which is {pct}% above the configured baseline ({base} {unit}). "
                    f"Observed factor: {reason_text}. "
                    f"Suggested action: {actions}. This is an automated decision-support observation based on historical statistical thresholds."
                )

            data_src = f"Live 24h Sensor Telemetry • Baseline: {base} {unit}"
            followups = [
                f"How much higher than baseline?",
                f"Which block has highest {metric} usage?",
                f"What is the {metric} forecast?",
            ]
            return reply, data_src, followups

        # 2. FIND HIGHEST BLOCK (STRUCTURED RESPONSE)
        if intent == "find_highest_block":
            comp = tool_data.get("block_comparison", {})
            highest = comp.get("highest_block")
            all_blocks = comp.get("blocks", [])

            if not highest or highest.get("value", 0) == 0:
                if lang == "odia":
                    reply = f"ବ୍ଲକ-ୱାଇଜ୍ {metric} ସେନ୍ସର ତଥ୍ୟ ବର୍ତ୍ତମାନ ଉପଲବ୍ଧ ନାହିଁ କିମ୍ବା 0 ଅଛି।"
                elif lang == "roman_odia":
                    reply = f"Block-wise {metric} telemetry ebe prapuri sync heini ba zero achhi."
                elif lang == "hinglish":
                    reply = f"Block-wise {metric} telemetry abhi sync nahi hua hai ya data zero hai."
                else:
                    reply = f"No active block-level telemetry is currently available for {metric}."
                return reply, "Facility Block Telemetry", ["List all blocks", "Check active anomalies"]

            b_name = highest.get("block_name") or highest.get("block_id")
            val = highest.get("value")
            unit = highest.get("unit", "")

            # Build ranked list of other blocks
            other_blocks = [b for b in all_blocks if (b.get("block_name") or b.get("block_id")) != b_name]

            if lang == "odia":
                lines = [f"ଆପଣଙ୍କ ସଂସ୍ଥାରେ ସବୁଠାରୁ ଅଧିକ {metric} ବ୍ୟବହାର **{b_name}** ରେ ଅଛି ({val} {unit})。\n"]
                if other_blocks:
                    lines.append("ଅନ୍ୟାନ୍ୟ ବ୍ଲକଗୁଡ଼ିକର ତୁଳନା:")
                    for ob in other_blocks:
                        lines.append(f"- {ob.get('block_name')}: {ob.get('value')} {ob.get('unit', unit)}")
                lines.append("\nତୁଳନାର ଆଧାର: ସଦ୍ୟତମ ୨୪ ଘଣ୍ଟାର ସେନ୍ସର ଟେଲିମେଟ୍ରି।")
                reply = "\n".join(lines)

            elif lang == "roman_odia":
                lines = [f"Apanka organisation re sabuthu besi {metric} usage **{b_name}** re achhi ({val} {unit}).\n"]
                if other_blocks:
                    lines.append("Anyanya block gudikara breakdown:")
                    for ob in other_blocks:
                        lines.append(f"- {ob.get('block_name')}: {ob.get('value')} {ob.get('unit', unit)}")
                lines.append("\nTulanara adhara: Latest 24-hour sensor telemetry readings.")
                reply = "\n".join(lines)

            elif lang == "hinglish":
                lines = [f"Aapki organisation me sabse zyada {metric} usage **{b_name}** me hai ({val} {unit}).\n"]
                if other_blocks:
                    lines.append("Baaki blocks ka breakdown:")
                    for ob in other_blocks:
                        lines.append(f"- {ob.get('block_name')}: {ob.get('value')} {ob.get('unit', unit)}")
                lines.append("\nComparison basis: Recent 24-hour telemetry readings.")
                reply = "\n".join(lines)

            else:
                lines = [f"**{b_name}** currently has the highest {metric} consumption at **{val} {unit}** across your facility blocks.\n"]
                if other_blocks:
                    lines.append("Breakdown of other blocks:")
                    for ob in other_blocks:
                        lines.append(f"- {ob.get('block_name')}: {ob.get('value')} {ob.get('unit', unit)}")
                lines.append("\nBasis of comparison: Latest 24-hour sensor telemetry readings.")
                reply = "\n".join(lines)

            data_src = f"Facility Block Telemetry Table • Metric: {metric}"
            followups = [
                f"Why is {metric} high in {b_name}?",
                f"How much higher than baseline?",
                f"What are today's critical anomalies?",
            ]
            return reply, data_src, followups

        # 3. LIST ANOMALIES
        if intent == "list_anomalies":
            anom_data = tool_data.get("anomalies", {})
            total = anom_data.get("total_active", 0)
            items = anom_data.get("anomalies", [])

            if total == 0:
                if lang == "odia":
                    reply = "ଆଜି କୌଣସି ଆକ୍ଟିଭ୍ କିମ୍ବା କ୍ରିଟିକାଲ୍ ଆନୋମାଲି ନାହିଁ। ସମସ୍ତ ମେଟ୍ରିକ୍ ସାଧାରଣ ସୀମା ଭିତରେ ଅଛି।"
                elif lang == "roman_odia":
                    reply = "Aji konasi open ba critical anomaly nahi. Samasta facility metrics normal baseline bhitare achhi."
                elif lang == "hinglish":
                    reply = "Aaj koi bhi open ya critical anomaly nahi hai. Sabhi facility metrics baseline range ke andar hain."
                else:
                    reply = "There are currently no active critical anomalies. All monitored facility metrics are operating within expected baseline thresholds."
                return reply, "Anomaly Engine (0 Active)", ["Show recent readings", "Check 24h forecast"]

            crit_count = anom_data.get("critical_count", 0)
            summary_list = []
            for a in items[:3]:
                summary_list.append(f"{a['metric'].capitalize()} in {a['block']}: {a['value']} ({a['severity']})")
            details = "; ".join(summary_list)

            if lang == "odia":
                reply = f"ଆଜି ମୋଟ {total} ଟି ଆକ୍ଟିଭ୍ ଆନୋମାଲି ଅଛି (କ୍ରିଟିକାଲ୍: {crit_count})। ମୁଖ୍ୟ ଆନୋମାଲି: {details}।"
            elif lang == "roman_odia":
                reply = f"Aji total {total} ti active anomaly achhi (Critical: {crit_count}). Mukhyata: {details}."
            elif lang == "hinglish":
                reply = f"Aaj total {total} active anomalies hain (Critical: {crit_count}). Key items: {details}."
            else:
                reply = f"There are currently {total} active anomalies ({crit_count} Critical). Most recent: {details}."

            data_src = f"Anomaly Detection Service • {total} Active Anomalies"
            followups = [
                "What actions are recommended?",
                f"Which block has the highest anomaly count?",
                "Show platform health status",
            ]
            return reply, data_src, followups

        # 4. CURRENT READING / DELTA FROM BASELINE
        if intent in ("current_reading", "delta_from_baseline"):
            curr = tool_data.get("current_metric", {})
            if not curr.get("available"):
                if lang == "odia":
                    reply = f"ଆଜି {metric} ର କୌଣସି ନୂତନ ସେନ୍ସର ରିଡିଂ ରେକର୍ଡ ହୋଇନାହିଁ।"
                elif lang == "roman_odia":
                    reply = f"Aji pain {metric} ra konasi recent sensor reading record heini."
                elif lang == "hinglish":
                    reply = f"Aaj ke liye {metric} ki koi recent sensor reading record nahi hui hai."
                else:
                    reply = f"No recent sensor telemetry has been recorded for {metric} today."
                return reply, "Sensor Readings Table", ["Show all enabled sensors", "Check anomalies"]

            val = curr.get("value")
            base = curr.get("baseline")
            diff = curr.get("diff_from_baseline", 0)
            pct = curr.get("pct_diff_from_baseline", 0)
            unit = curr.get("unit", "")
            loc = block or curr.get("block_id") or "Facility"

            if lang == "odia":
                reply = f"ଆଜି {loc} ରେ {metric} ରିଡିଂ {val} {unit} ଅଛି (ବେସଲାଇନ୍: {base} {unit}, ପାର୍ଥକ୍ୟ: {pct}%)।"
            elif lang == "roman_odia":
                reply = f"Aji {loc} re {metric} reading {val} {unit} achhi (Baseline: {base} {unit}, Variation: {pct}%)."
            elif lang == "hinglish":
                reply = f"Aaj {loc} me {metric} reading {val} {unit} hai (Baseline: {base} {unit}, Difference: {pct}%)."
            else:
                reply = f"Today's recorded {metric} reading for {loc} is {val} {unit} (Baseline: {base} {unit}, Delta: {pct}%)."

            data_src = f"Sensor Readings Telemetry • Sensor: {metric}"
            followups = [
                f"Why is {metric} usage high?" if diff > 0 else f"What is the {metric} forecast?",
                f"Which block has highest {metric} usage?",
            ]
            return reply, data_src, followups

        # 5. FORECAST QUERY
        if intent == "forecast_query":
            fc = tool_data.get("forecast", {})
            if not fc.get("available"):
                reason = fc.get("reason", "Forecasting requires at least 5 consecutive historical telemetry points.")
                if lang == "odia":
                    reply = f"{metric.capitalize()} ପୂର୍ବାନୁମାନ ବର୍ତ୍ତମାନ ଉପଲବ୍ଧ ନାହିଁ। {reason}"
                elif lang == "roman_odia":
                    reply = f"{metric.capitalize()} forecast ebe available nahi. {reason}"
                elif lang == "hinglish":
                    reply = f"{metric.capitalize()} forecast abhi available nahi hai. {reason}"
                else:
                    reply = f"{metric.capitalize()} forecast is currently unavailable. {reason}"
                return reply, "Holt-Winters Forecasting Engine", ["Check current readings", "View anomalies"]

            avg_pred = fc.get("average_predicted")
            trend = fc.get("trend")
            unit = fc.get("unit", "")

            if lang == "odia":
                reply = f"ଆଗାମୀ ୨୪ ଘଣ୍ଟା ପାଇଁ {metric} ର ହାରାହାରି ପୂର୍ବାନୁମାନ {avg_pred} {unit} ଅଛି (ଟ୍ରେଣ୍ଡ: {trend})।"
            elif lang == "roman_odia":
                reply = f"Agami 24 ghanta pain {metric} ra projected average {avg_pred} {unit} achhi (trend: {trend})."
            elif lang == "hinglish":
                reply = f"Agle 24 ghante ke liye {metric} ka projected average {avg_pred} {unit} hai (trend: {trend})."
            else:
                reply = f"The 24-hour forecast projects an average {metric} reading of {avg_pred} {unit} with a {trend} trend."

            data_src = "Statsmodels Holt-Winters Model • 24h Horizon"
            followups = [
                f"What recommendations are active?",
                f"Compare block-wise {metric}",
            ]
            return reply, data_src, followups

        # 6. RECOMMENDATION QUERY
        if intent == "recommendation_query":
            recs_data = tool_data.get("recommendations", {})
            items = recs_data.get("recommendations", [])
            if not items:
                if lang == "odia":
                    reply = "ଏହି ସମୟରେ କୌଣସି ପେଣ୍ଡିଂ ସୁପାରିଶ ନାହିଁ।"
                elif lang == "roman_odia":
                    reply = "Ehi samayare konasi pending recommendation nahi."
                elif lang == "hinglish":
                    reply = "Is samay koi pending recommendation nahi hai."
                else:
                    reply = "There are no pending AI recommendations at this time."
                return reply, "AI Recommendation Engine (0 Pending)", ["Check current metrics", "View forecast"]

            rec = items[0]
            actions_summary = "; ".join(rec["actions"][:2])
            loc = rec["block"]
            prio = rec["priority"]

            if lang == "odia":
                reply = f"{loc} ପାଇଁ {prio} ପ୍ରାଥମିକତା ସୁପାରିଶ: {rec['summary']}। ପଦକ୍ଷେପ: {actions_summary}।"
            elif lang == "roman_odia":
                reply = f"{loc} pain {prio} priority recommendation achhi: {rec['summary']}. Actions: {actions_summary}."
            elif lang == "hinglish":
                reply = f"{loc} ke liye {prio} priority recommendation active hai: {rec['summary']}. Actions: {actions_summary}."
            else:
                reply = f"Active {prio} recommendation for {loc}: {rec['summary']}. Actions: {actions_summary}."

            data_src = "AI Recommendation Engine • Tailored Guidance"
            followups = ["Explain the linked anomaly", "Show all open recommendations"]
            return reply, data_src, followups

        # 7. SUPER ADMIN PLATFORM SUMMARY
        if intent == "platform_summary":
            plat = tool_data.get("platform_summary", {})
            total_orgs = plat.get("total_organisations", 0)
            active_anoms = plat.get("platform_active_anomalies", 0)
            total_users = plat.get("total_users", 0)

            if lang == "odia":
                reply = f"ପ୍ଲାଟଫର୍ମ ସାରାଂଶ: ମୋଟ {total_orgs} ଟି ସଂସ୍ଥା, {total_users} ଟି ୟୁଜର୍ ଏବଂ {active_anoms} ଟି ସକ୍ରିୟ ଆନୋମାଲି ଅଛି।"
            elif lang == "roman_odia":
                reply = f"Platform summary: Total {total_orgs} organisations registered achhi, {total_users} users, o {active_anoms} active anomalies achhi."
            elif lang == "hinglish":
                reply = f"Platform overview: Total {total_orgs} organisations registered hain, {total_users} users, aur {active_anoms} active anomalies hain."
            else:
                reply = f"Platform Overview: {total_orgs} registered organisations with {total_users} users and {active_anoms} active anomalies across all tenants."

            data_src = "Super Admin Platform Engine"
            followups = ["Compare water usage across organisations", "Which organisations have critical anomalies?"]
            return reply, data_src, followups

        # 7B. SCENARIO SIMULATION (WHAT-IF ANALYSIS)
        if intent == "scenario_simulation":
            scenario_data = tool_data.get("scenario_simulation", {})
            baseline = scenario_data.get("baseline_consumption") or scenario_data.get("baseline_generation") or scenario_data.get("baseline_vehicle_volume") or 100.0
            projected = scenario_data.get("projected_consumption") or scenario_data.get("projected_landfill_waste") or scenario_data.get("projected_vehicle_volume") or 90.0
            saved = scenario_data.get("net_savings") or scenario_data.get("diverted_waste") or scenario_data.get("vehicles_diverted") or 10.0
            pct = scenario_data.get("savings_percentage") or scenario_data.get("diversion_percentage") or scenario_data.get("traffic_reduction_pct") or 10.0
            unit = scenario_data.get("unit", "units")
            cost_savings = scenario_data.get("estimated_cost_savings_inr", 0.0)
            co2 = scenario_data.get("co2_avoided_kg", 0.0)
            assumptions = "; ".join(scenario_data.get("assumptions", [])[:2])

            if lang == "odia":
                reply = (
                    f"ଏହି ପରିସ୍ଥିତିରେ (What-If Scenario) ୨୪ ଘଣ୍ଟାରେ ଆନୁମାନିକ **{saved} {unit}** ({pct}%) ସଞ୍ଚୟ ହୋଇପାରିବ।\n\n"
                    f"[Modelled Scenario Estimate]\n"
                    f"- ବେସଲାଇନ୍: {baseline} {unit} → ଅନୁମାନିତ: {projected} {unit}\n"
                    f"- ଆନୁମାନିକ ଖର୍ଚ୍ଚ ସଞ୍ଚୟ: ₹{cost_savings:,.2f} INR\n"
                    f"- ଅଙ୍ଗାରକାମ୍ଳ ହ୍ରାସ: {co2} kg CO2\n"
                    f"- ଧାରଣା (Assumptions): {assumptions}\n\n"
                    f"Disclaimer: ଏହା GreenNexa ତଥ୍ୟ ଏବଂ BEE ନିର୍ଦ୍ଦେଶାବଳୀ ଉପରେ ଆଧାରିତ ଏକ ନିଷ୍ପତ୍ତି-ସହାୟତା ଆକଳନ।"
                )
            elif lang == "roman_odia":
                reply = (
                    f"Ehi What-If scenario re next 24 hours re anumanika **{saved} {unit}** ({pct}%) bachat heba.\n\n"
                    f"[Modelled Scenario Estimate]\n"
                    f"- Baseline: {baseline} {unit} -> Projected: {projected} {unit}\n"
                    f"- Anumanita cost savings: ₹{cost_savings:,.2f} INR\n"
                    f"- CO2 avoided: {co2} kg CO2\n"
                    f"- Key Assumptions: {assumptions}\n\n"
                    f"Disclaimer: GreenNexa telemetry ebong BEE norms upare adharita decision-support estimate."
                )
            elif lang == "hinglish":
                reply = (
                    f"Is What-If scenario mein agle 24 ghanton mein lagbhag **{saved} {unit}** ({pct}%) ki bachat hogi.\n\n"
                    f"[Modelled Scenario Estimate]\n"
                    f"- Baseline: {baseline} {unit} -> Projected: {projected} {unit}\n"
                    f"- Anumanit Kharch Bachat: ₹{cost_savings:,.2f} INR\n"
                    f"- CO2 Bachat: {co2} kg CO2\n"
                    f"- Key Assumptions: {assumptions}\n\n"
                    f"Disclaimer: GreenNexa telemetry aur BEE benchmarks par aadharit decision-support estimate."
                )
            else:
                reply = (
                    f"Under this operational What-If scenario, projected 24-hour savings are approximately **{saved} {unit}** ({pct}% reduction).\n\n"
                    f"[Modelled Scenario Estimate]\n"
                    f"- Baseline: {baseline} {unit} -> Projected: {projected} {unit}\n"
                    f"- Estimated Cost Savings: ₹{cost_savings:,.2f} INR\n"
                    f"- Carbon Avoided: {co2} kg CO2\n"
                    f"- Modeling Assumptions: {assumptions}\n\n"
                    f"Disclaimer: Decision-support estimate based on GreenNexa telemetry and national benchmarks."
                )

            data_src = "GreenNexa What-If Scenario Engine • Modelled Estimate"
            followups = [
                "What if we reduce water usage by 15%?",
                "What is the energy forecast for the next 24 hours?",
                "Show active energy recommendations",
            ]
            return reply, data_src, followups

        # 8. GENERAL / DEFAULT FALLBACK
        org_sum = tool_data.get("organisation_summary", {})
        org_name = org_sum.get("name", "your facility")
        anom_cnt = org_sum.get("active_anomalies", 0)
        rec_cnt = org_sum.get("active_recommendations", 0)

        if lang == "odia":
            reply = (
                f"ନମସ୍କାର! ମୁଁ ଗ୍ରୀନନେକ୍ସା AI ଆସିଷ୍ଟାଣ୍ଟ। {org_name} ରେ ଏବେ {anom_cnt} ଟି ଆକ୍ଟିଭ୍ ଆନୋମାଲି ଓ {rec_cnt} ଟି ସୁପାରିଶ ଅଛି। "
                f"ଆପଣ ବିଜୁଳି, ଜଳ, ଆବର୍ଜନା କିମ୍ବା ବ୍ଲକ-ୱାଇଜ୍ ଆନୋମାଲି ବିଷୟରେ ପ୍ରଶ୍ନ ପଚାରି ପାରିବେ।"
            )
        elif lang == "roman_odia":
            reply = (
                f"Namaskar! Mun GreenNexa AI assistant. {org_name} re ebe {anom_cnt} ti active anomaly o {rec_cnt} ti recommendation achhi. "
                f"Apana energy, water, waste, temperature ba block-wise anomalies bisayare prashna pachari paribe."
            )
        elif lang == "hinglish":
            reply = (
                f"Namaste! Main GreenNexa AI assistant hoon. {org_name} me abhi {anom_cnt} active anomalies aur {rec_cnt} recommendations hain. "
                f"Aap energy, water, waste, temperature ya specific block ke baare me pooch sakte hain."
            )
        else:
            reply = (
                f"Hello! I am GreenNexa AI, your sustainability and telemetry assistant. {org_name} currently has "
                f"{anom_cnt} active anomalies and {rec_cnt} recommendations. "
                f"You can ask about energy, water, waste, indoor climate, forecasts, or specific facility blocks."
            )

        data_src = "GreenNexa Intelligence Hub"
        followups = [
            "Explain today's critical anomalies",
            "Which block has the highest energy usage?",
            "What is the 24h water forecast?",
        ]
        return reply, data_src, followups

    @classmethod
    def _generate_followups(
        cls,
        language: str,
        intent: str,
        metric: Optional[str] = None,
        is_super_admin: bool = False,
    ) -> List[str]:
        """Generate contextual follow-up prompt suggestions."""
        m_label = (metric or "energy").capitalize()
        if is_super_admin:
            return [
                "Show platform-wide telemetry & health overview",
                "Which organisation currently has critical anomalies?",
                "Compare water usage across organisations",
            ]
        if intent == "scenario_simulation":
            return [
                "What if we reduce water usage by 15%?",
                "What is the energy forecast for the next 24 hours?",
                "Show active sustainability recommendations",
            ]
        if intent == "forecast_query":
            return [
                f"What happens if {m_label} consumption increases by 10%?",
                f"Explain today's critical {m_label} anomalies",
                f"Show active recommendations for {m_label}",
            ]
        return [
            f"Which block has the highest {m_label} usage?",
            f"What is the 24h {m_label} forecast?",
            f"Show active recommendations for {m_label}",
        ]
