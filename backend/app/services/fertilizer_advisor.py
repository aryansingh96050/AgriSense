import math
from typing import List, Dict
from sqlalchemy.orm import Session
from ..models.db_models import TelemetryReading, ActuatorState, CropProfile
from ..models.schemas import FertilizerAdviceResponse

class FertilizerAdvisor:
    # Benchmark agronomic NPK recommendations (kg/hectare baseline)
    CROP_RECOMMENDATIONS: Dict[str, Dict] = {
        "Wheat": {
            "n_req": 120.0, "p_req": 60.0, "k_req": 40.0,
            "stages": "Basal (50% N + 100% P & K), 1st Top Dress at CRI 21-25 DAS (25% N), 2nd Top Dress at Tillering (25% N)",
            "precautions": ["Avoid applying urea during rain to prevent leaching", "Irrigate field within 24 hours of urea top-dressing"]
        },
        "Rice": {
            "n_req": 150.0, "p_req": 60.0, "k_req": 60.0,
            "stages": "Basal (50% N + full P & K), Tillering (25% N), Panicle Initiation (25% N)",
            "precautions": ["Maintain 2-3 cm standing water during top dressing", "Use Neem-Coated Urea to reduce volatilization losses"]
        },
        "Maize": {
            "n_req": 140.0, "p_req": 65.0, "k_req": 50.0,
            "stages": "Basal (1/3rd N + full P & K), Knee-high stage (1/3rd N), Tasseling stage (1/3rd N)",
            "precautions": ["Place fertilizer 5cm away from plant base to prevent salt injury"]
        },
        "Cotton": {
            "n_req": 120.0, "p_req": 60.0, "k_req": 60.0,
            "stages": "Basal (full P & K), Squaring (50% N), Peak Flowering (50% N)",
            "precautions": ["Excess Nitrogen causes vegetative overgrowth; monitor canopy carefully"]
        },
        "Tomato": {
            "n_req": 150.0, "p_req": 100.0, "k_req": 120.0,
            "stages": "Basal (full P + 30% N & K), Fertigation split weekly during vegetative and fruit set",
            "precautions": ["Ensure steady Potassium for fruit firmness and color development", "Calcium supplement helps prevent blossom end rot"]
        },
        "Potato": {
            "n_req": 180.0, "p_req": 100.0, "k_req": 150.0,
            "stages": "Basal (50% N + full P & K), Earthing up / Tuber initiation 30 DAS (50% N)",
            "precautions": ["Use Sulfate of Potash (SOP) instead of MOP for chip/crisp grade potatoes"]
        },
        "Sugarcane": {
            "n_req": 250.0, "p_req": 100.0, "k_req": 120.0,
            "stages": "Split across 4 doses: Germination, Tillering, Grand Growth, and Earthing Up",
            "precautions": ["Apply in furrows and cover immediately with soil to maximize absorption"]
        }
    }

    def evaluate(self, db: Session, device_id: str = "ESP32_NODE_01") -> FertilizerAdviceResponse:
        # Fetch latest sensor reading
        latest_telemetry = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.device_id == device_id)
            .order_by(TelemetryReading.timestamp.desc())
            .first()
        )

        # Fetch active actuator & crop settings
        actuator = (
            db.query(ActuatorState)
            .filter(ActuatorState.device_id == device_id)
            .first()
        )
        crop_name = actuator.active_crop if actuator else "Wheat"
        acres = actuator.field_area_acres if actuator and actuator.field_area_acres else 1.0

        # Sensor readings (with fallback values)
        soil_n = latest_telemetry.nitrogen if (latest_telemetry and latest_telemetry.nitrogen) else 45.0
        soil_p = latest_telemetry.phosphorus if (latest_telemetry and latest_telemetry.phosphorus) else 25.0
        soil_k = latest_telemetry.potassium if (latest_telemetry and latest_telemetry.potassium) else 140.0
        soil_ph = latest_telemetry.ph_level if (latest_telemetry and latest_telemetry.ph_level) else 6.8

        crop_profile = self.CROP_RECOMMENDATIONS.get(crop_name, self.CROP_RECOMMENDATIONS["Wheat"])
        
        # 1 Hectare = 2.471 Acres. Convert recommendations to per-acre values
        acre_conversion = acres / 2.471
        
        target_n = round(crop_profile["n_req"] * acre_conversion, 1)
        target_p = round(crop_profile["p_req"] * acre_conversion, 1)
        target_k = round(crop_profile["k_req"] * acre_conversion, 1)

        # Approximate soil test conversion: standard soil test rating (Low, Medium, High)
        # N: < 280 kg/ha is Low, 280-560 Medium. Sensor ppm ~ approx conversion factor
        n_deficit_kg = max(0.0, target_n - (soil_n * 0.4 * acres))
        p_deficit_kg = max(0.0, target_p - (soil_p * 0.6 * acres))
        k_deficit_kg = max(0.0, target_k - (soil_k * 0.3 * acres))

        # Commercial Fertilizer Calculations:
        # 1. DAP supplies 46% P2O5 and 18% N
        dap_kg = round(p_deficit_kg / 0.46, 1) if p_deficit_kg > 0 else 0.0
        n_supplied_by_dap = dap_kg * 0.18
        
        # 2. Remaining Nitrogen supplied by Urea (46% N)
        remaining_n = max(0.0, n_deficit_kg - n_supplied_by_dap)
        urea_kg = round(remaining_n / 0.46, 1) if remaining_n > 0 else 0.0

        # 3. MOP supplies 60% K2O
        mop_kg = round(k_deficit_kg / 0.60, 1) if k_deficit_kg > 0 else 0.0

        # Bags (Urea = 45 kg/bag in India/Subcontinent; DAP/MOP = 50 kg/bag)
        urea_bags = round(urea_kg / 45.0, 1)
        dap_bags = round(dap_kg / 50.0, 1)
        mop_bags = round(mop_kg / 50.0, 1)

        # Status categorization
        def categorize(current, target):
            ratio = current / max(1.0, target)
            if ratio < 0.6:
                return "Deficient (Needs Replenishment)"
            elif ratio <= 1.2:
                return "Adequate (Optimal Range)"
            else:
                return "Surplus (Do not add excess)"

        n_status = categorize(soil_n * 0.4 * acres, target_n)
        p_status = categorize(soil_p * 0.6 * acres, target_p)
        k_status = categorize(soil_k * 0.3 * acres, target_k)

        # Soil pH diagnosis
        if soil_ph < 6.0:
            ph_status = "Acidic (pH < 6.0)"
            ph_note = f"Soil pH is {soil_ph:.1f}. Apply 200-300 kg/acre Agricultural Lime or Dolomite to neutralize acidity and unlock locked phosphorus."
        elif soil_ph > 7.8:
            ph_status = "Alkaline (pH > 7.8)"
            ph_note = f"Soil pH is {soil_ph:.1f}. Apply Gypsum (150-250 kg/acre) or elemental sulfur, and use organic matter/FYM to lower pH and increase micronutrient uptake."
        else:
            ph_status = "Neutral / Optimal (pH 6.0 - 7.5)"
            ph_note = f"Soil pH is {soil_ph:.1f}, perfectly in the ideal range for maximum nutrient bioavailability."

        # Organic alternatives
        organic_options = [
            f"Well-decomposed Farmyard Manure (FYM): Apply ~{round(2.5 * acres, 1)} to {round(4.0 * acres, 1)} Tons/acre before sowing",
            f"Vermicompost: ~{round(800 * acres, 0):,.0f} kg/acre for enriched organic carbon and microbial flora",
            "Bio-fertilizers: Seed treatment with Azotobacter (fixes atmospheric N) & PSB (Phosphate Solubilizing Bacteria) @ 250g/10kg seed",
            "Green Manuring: Dhaincha (Sesbania) or Sunnhemp incorporated into soil 45 days prior to main crop"
        ]

        precautions = crop_profile.get("precautions", []) + [ph_note]

        return FertilizerAdviceResponse(
            crop_name=crop_name,
            growth_stage="Vegetative / Active Growth",
            field_area_acres=acres,
            soil_ph=soil_ph,
            ph_status=ph_status,
            current_n=soil_n,
            target_n=target_n,
            n_status=n_status,
            current_p=soil_p,
            target_p=target_p,
            p_status=p_status,
            current_k=soil_k,
            target_k=target_k,
            k_status=k_status,
            urea_kg=urea_kg,
            urea_bags=urea_bags,
            dap_kg=dap_kg,
            dap_bags=dap_bags,
            mop_kg=mop_kg,
            mop_bags=mop_bags,
            organic_options=organic_options,
            split_application_guide=crop_profile.get("stages", "Apply as per local agricultural university guidelines."),
            key_precautions=precautions
        )

fertilizer_advisor = FertilizerAdvisor()
