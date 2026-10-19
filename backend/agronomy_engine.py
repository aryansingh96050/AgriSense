import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple
from models import AdvisoryResult, FertilizerRecommendation

CROPS_FILE = os.path.join(os.path.dirname(__file__), "crops_data.json")

def load_crop_database() -> Dict[str, Any]:
    with open(CROPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

CROPS_DB = load_crop_database()

class AgronomyEngine:
    @staticmethod
    def evaluate(
        crop_key: str,
        stage_key: str,
        moisture: float,
        temperature: float,
        ph: float,
        n: float,
        p: float,
        k: float,
        field_size_acres: float = 2.5,
        farmer_name: str = "Ramesh Kumar"
    ) -> AdvisoryResult:
        crop_data = CROPS_DB.get(crop_key, CROPS_DB["wheat"])
        crop_en = crop_data.get("name_en", "Crop")
        crop_hi = crop_data.get("name_hi", "फसल")
        
        stages = crop_data.get("stages", {})
        stage_data = stages.get(stage_key, next(iter(stages.values())))
        stage_en = stage_data.get("name_en", "Growth Stage")
        stage_hi = stage_data.get("name_hi", "वृद्धि अवस्था")

        # ---------------- 1. IRRIGATION ADVISORY ----------------
        opt_min = crop_data["moisture_optimal_min"]
        opt_max = crop_data["moisture_optimal_max"]
        crit_min = crop_data["moisture_critical_min"]
        base_mins = crop_data.get("recommended_drip_mins", 45)

        irrigation_needed = False
        irrigation_urgency = "NOT_NEEDED"
        rec_pump_mins = 0
        irrig_advice_en = ""
        irrig_advice_hi = ""

        if moisture < crit_min:
            irrigation_needed = True
            irrigation_urgency = "URGENT"
            deficit_ratio = (opt_min - moisture) / opt_min
            rec_pump_mins = int(base_mins * (1.0 + min(deficit_ratio, 0.6)))
            irrig_advice_en = f"CRITICAL: Soil moisture ({moisture:.1f}%) is severely low. Start irrigation immediately for {rec_pump_mins} minutes."
            irrig_advice_hi = f"अति आवश्यक: मिट्टी में नमी ({moisture:.1f}%) बहुत कम है। कृपया तुरंत {rec_pump_mins} मिनट के लिए सिंचाई चालू करें।"
        elif moisture < opt_min:
            irrigation_needed = True
            irrigation_urgency = "NORMAL"
            rec_pump_mins = base_mins
            irrig_advice_en = f"ATTENTION: Soil moisture ({moisture:.1f}%) is below optimal ({opt_min}%). Irrigation recommended for {rec_pump_mins} minutes."
            irrig_advice_hi = f"ध्यान दें: मिट्टी में नमी ({moisture:.1f}%) अनुकूल स्तर ({opt_min}%) से कम है। {rec_pump_mins} मिनट सिंचाई की सलाह दी जाती है।"
        elif moisture <= opt_max:
            irrigation_urgency = "NOT_NEEDED"
            rec_pump_mins = 0
            irrig_advice_en = f"OPTIMAL: Soil moisture ({moisture:.1f}%) is within target range ({opt_min}-{opt_max}%). No irrigation required."
            irrig_advice_hi = f"संतुलित: मिट्टी की नमी ({moisture:.1f}%) एकदम सही है ({opt_min}-{opt_max}%)। अभी पानी देने की आवश्यकता नहीं है।"
        else:
            irrigation_urgency = "WATERLOGGED"
            rec_pump_mins = 0
            irrig_advice_en = f"WARNING: Soil is saturated/waterlogged ({moisture:.1f}%). Stop all watering and inspect drainage."
            irrig_advice_hi = f"चेतावनी: मिट्टी में अत्यधिक पानी ({moisture:.1f}%) जमा है। तुरंत पानी रोकें और जल निकासी की व्यवस्था करें।"

        # ---------------- 2. pH ADVISORY ----------------
        ph_min = crop_data["ph_min"]
        ph_max = crop_data["ph_max"]
        ph_status = "OPTIMAL"
        ph_advice_en = ""
        ph_advice_hi = ""

        if ph < ph_min:
            ph_status = "ACIDIC"
            ph_advice_en = f"Acidic Soil (pH {ph:.1f}). Apply Agricultural Lime at 150 kg/acre to balance pH and improve nutrient uptake."
            ph_advice_hi = f"अम्लीय मिट्टी (pH {ph:.1f})। मिट्टी सुधारने के लिए 150 किलो/एकड़ कृषि चूना (Lime) का प्रयोग करें।"
        elif ph > ph_max:
            ph_status = "ALKALINE"
            ph_advice_en = f"Alkaline Soil (pH {ph:.1f}). Apply Agricultural Gypsum at 200 kg/acre or organic farmyard manure."
            ph_advice_hi = f"क्षारीय मिट्टी (pH {ph:.1f})। क्षारीयता कम करने के लिए 200 किलो/एकड़ कृषि जिप्सम या सड़ी गोबर खाद डालें।"
        else:
            ph_status = "OPTIMAL"
            ph_advice_en = f"Optimal Soil pH ({ph:.1f}). Soil reaction is ideal for healthy root growth and nutrient absorption."
            ph_advice_hi = f"संतुलित मिट्टी pH ({ph:.1f})। मिट्टी की अम्लता-क्षारीयता पौधों की जड़ों और विकास के लिए उपयुक्त है।"

        # ---------------- 3. NPK FERTILIZATION ADVISORY ----------------
        target_n = stage_data.get("target_n", 120)
        target_p = stage_data.get("target_p", 50)
        target_k = stage_data.get("target_k", 40)

        diff_n = max(0.0, target_n - n)
        diff_p = max(0.0, target_p - p)
        diff_k = max(0.0, target_k - k)

        recs: List[FertilizerRecommendation] = []
        fert_action_needed = False

        # Nitrogen (Urea 46% N)
        if diff_n > 15:
            fert_action_needed = True
            dose_acre = round(diff_n * 0.35, 1)
            recs.append(FertilizerRecommendation(
                fertilizer_name_en="Urea (46% N)",
                fertilizer_name_hi="यूरिया (Urea)",
                dose_per_acre_kg=dose_acre,
                total_field_dose_kg=round(dose_acre * field_size_acres, 1),
                timing_guidance="Apply as top-dressing after irrigation or light rainfall",
                priority="HIGH" if diff_n > 35 else "MEDIUM"
            ))

        # Phosphorus (DAP 46% P2O5 / SSP 16% P2O5)
        if diff_p > 10:
            fert_action_needed = True
            dose_acre = round(diff_p * 0.45, 1)
            recs.append(FertilizerRecommendation(
                fertilizer_name_en="DAP / SSP (Phosphorus)",
                fertilizer_name_hi="डीएपी / सिंगल सुपर फॉस्फेट (DAP/SSP)",
                dose_per_acre_kg=dose_acre,
                total_field_dose_kg=round(dose_acre * field_size_acres, 1),
                timing_guidance="Apply near root zone or during soil hoeing",
                priority="HIGH" if diff_p > 25 else "MEDIUM"
            ))

        # Potassium (MOP 60% K2O)
        if diff_k > 10:
            fert_action_needed = True
            dose_acre = round(diff_k * 0.30, 1)
            recs.append(FertilizerRecommendation(
                fertilizer_name_en="Muriate of Potash (MOP)",
                fertilizer_name_hi="म्यूरेट ऑफ पोटाश (MOP)",
                dose_per_acre_kg=dose_acre,
                total_field_dose_kg=round(dose_acre * field_size_acres, 1),
                timing_guidance="Apply before grain/fruit development to boost disease resistance & quality",
                priority="HIGH" if diff_k > 25 else "MEDIUM"
            ))

        if fert_action_needed:
            fert_advice_en = f"Nutrient deficit detected for {stage_en}. Target NPK: {target_n}:{target_p}:{target_k} vs Current: {n:.0f}:{p:.0f}:{k:.0f} mg/kg."
            fert_advice_hi = f"{stage_hi} के लिए पोषक तत्वों की कमी है। लक्ष्य NPK: {target_n}:{target_p}:{target_k} जबकि वर्तमान: {n:.0f}:{p:.0f}:{k:.0f} mg/kg है।"
        else:
            fert_advice_en = f"All soil nutrients (NPK: {n:.0f}:{p:.0f}:{k:.0f} mg/kg) are at healthy target levels for this stage."
            fert_advice_hi = f"वर्तमान अवस्था के लिए मिट्टी में सभी पोषक तत्व (NPK: {n:.0f}:{p:.0f}:{k:.0f} mg/kg) पूर्ण रूप से संतुलित हैं।"

        # ---------------- 4. BILINGUAL MESSAGES (SMS & WHATSAPP) ----------------
        now_str = datetime.now().strftime("%d-%m-%Y %I:%M %p")
        
        # WhatsApp Hindi Message
        wa_hi_lines = [
            f"🌾 *AgriSense - किसान सलाहकार अलर्ट* 🌾",
            f"👤 किसान: *{farmer_name}* | खेत: *{field_size_acres} एकड़*",
            f"🌱 फसल: *{crop_hi} ({stage_hi})*",
            f"🕒 समय: {now_str}",
            "",
            "💧 *सिंचाई रिपोर्ट:*",
            f"• मिट्टी में नमी: *{moisture:.1f}%* (लक्ष्य: {opt_min}-{opt_max}%)",
            f"• फैसला: *{irrig_advice_hi}*",
            "",
            "🧪 *खाद व पोषण (NPK) रिपोर्ट:*",
            f"• वर्तमान स्तर: N={n:.0f}, P={p:.0f}, K={k:.0f} mg/kg",
            f"• pH स्तर: *{ph:.1f}* ({ph_status})"
        ]
        if recs:
            wa_hi_lines.append("\n📦 *अनुशंसित खाद की मात्रा:*")
            for r in recs:
                wa_hi_lines.append(f"  ▪ *{r.fertilizer_name_hi}*: {r.dose_per_acre_kg} किग्रा/एकड़ (खेत हेतु: {r.total_field_dose_kg} किग्रा)")
        else:
            wa_hi_lines.append("\n✅ खाद की स्थिति: कोई अतिरिक्त खाद आवश्यक नहीं है।")

        stage_advice_hi = stage_data.get("advice_hi", "")
        if stage_advice_hi:
            wa_hi_lines.append(f"\n💡 *विशेष सलाह:* {stage_advice_hi}")

        whatsapp_text_hi = "\n".join(wa_hi_lines)

        # WhatsApp English Message
        wa_en_lines = [
            f"🌾 *AgriSense - Smart Farm Advisory* 🌾",
            f"👤 Farmer: *{farmer_name}* | Area: *{field_size_acres} Acres*",
            f"🌱 Crop: *{crop_en} ({stage_en})*",
            f"🕒 Time: {now_str}",
            "",
            "💧 *Irrigation Status:*",
            f"• Soil Moisture: *{moisture:.1f}%* (Target: {opt_min}-{opt_max}%)",
            f"• Action: *{irrig_advice_en}*",
            "",
            "🧪 *Soil Nutrients (NPK) Status:*",
            f"• Current Levels: N={n:.0f}, P={p:.0f}, K={k:.0f} mg/kg",
            f"• pH: *{ph:.1f}* ({ph_status})"
        ]
        if recs:
            wa_en_lines.append("\n📦 *Recommended Fertilizer Doses:*")
            for r in recs:
                wa_en_lines.append(f"  ▪ *{r.fertilizer_name_en}*: {r.dose_per_acre_kg} kg/acre (Total: {r.total_field_dose_kg} kg)")
        else:
            wa_en_lines.append("\n✅ Fertilizer: Soil fertility is optimal.")

        whatsapp_text_en = "\n".join(wa_en_lines)

        # Compact SMS Hindi (160 char limit friendly)
        if irrigation_needed and recs:
            sms_text_hi = f"AgriSense अलर्ट: {crop_hi} में नमी {moisture:.1f}% कम है। {rec_pump_mins} मिनट सिंचाई करें। {recs[0].fertilizer_name_hi}: {recs[0].dose_per_acre_kg} किग्रा/एकड़ डालें।"
        elif irrigation_needed:
            sms_text_hi = f"AgriSense अलर्ट: {crop_hi} में नमी {moisture:.1f}% है। कृपया {rec_pump_mins} मिनट के लिए तुरंत सिंचाई करें।"
        elif recs:
            sms_text_hi = f"AgriSense अलर्ट: {crop_hi} ({stage_hi}) हेतु {recs[0].fertilizer_name_hi} {recs[0].dose_per_acre_kg} किग्रा/एकड़ डालने की सलाह है।"
        else:
            sms_text_hi = f"AgriSense: {crop_hi} खेत में नमी ({moisture:.1f}%) और NPK स्तर एकदम संतुलित हैं। सब सामान्य है।"

        # Compact SMS English
        if irrigation_needed and recs:
            sms_text_en = f"AgriSense Alert: {crop_en} moisture is {moisture:.1f}%. Run pump for {rec_pump_mins}m. Apply {recs[0].fertilizer_name_en} @ {recs[0].dose_per_acre_kg} kg/acre."
        elif irrigation_needed:
            sms_text_en = f"AgriSense Alert: {crop_en} moisture low ({moisture:.1f}%). Start irrigation for {rec_pump_mins} mins."
        elif recs:
            sms_text_en = f"AgriSense: Apply {recs[0].fertilizer_name_en} @ {recs[0].dose_per_acre_kg} kg/acre for {crop_en} {stage_en}."
        else:
            sms_text_en = f"AgriSense: {crop_en} moisture ({moisture:.1f}%) and NPK nutrient balance are optimal."

        return AdvisoryResult(
            timestamp=datetime.utcnow(),
            crop=crop_key,
            crop_name_hi=crop_hi,
            stage=stage_key,
            stage_name_hi=stage_hi,
            moisture_current=moisture,
            moisture_target_min=opt_min,
            moisture_target_max=opt_max,
            irrigation_needed=irrigation_needed,
            irrigation_urgency=irrigation_urgency,
            recommended_pump_run_minutes=rec_pump_mins,
            irrigation_advice_en=irrig_advice_en,
            irrigation_advice_hi=irrig_advice_hi,
            ph_current=ph,
            ph_status=ph_status,
            ph_advice_en=ph_advice_en,
            ph_advice_hi=ph_advice_hi,
            n_current=n,
            n_target=float(target_n),
            p_current=p,
            p_target=float(target_p),
            k_current=k,
            k_target=float(target_k),
            fertilizer_action_needed=fert_action_needed,
            fertilizer_recommendations=recs,
            fertilizer_advice_en=fert_advice_en,
            fertilizer_advice_hi=fert_advice_hi,
            sms_text_hi=sms_text_hi,
            sms_text_en=sms_text_en,
            whatsapp_text_hi=whatsapp_text_hi,
            whatsapp_text_en=whatsapp_text_en
        )
