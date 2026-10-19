from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models.db_models import TelemetryReading, ActuatorState, CropProfile, IrrigationLog, AdvisoryLog
from ..models.schemas import IrrigationAdviceResponse
from .weather_service import weather_service

class IrrigationAdvisor:
    def evaluate(self, db: Session, device_id: str = "ESP32_NODE_01") -> IrrigationAdviceResponse:
        # 1. Fetch latest telemetry
        latest_telemetry = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.device_id == device_id)
            .order_by(TelemetryReading.timestamp.desc())
            .first()
        )
        
        # 2. Fetch current actuator state
        actuator = (
            db.query(ActuatorState)
            .filter(ActuatorState.device_id == device_id)
            .first()
        )
        if not actuator:
            actuator = ActuatorState(device_id=device_id, pump_on=False, auto_mode=True, active_crop="Wheat")
            db.add(actuator)
            db.commit()
            db.refresh(actuator)

        # 3. Fetch crop profile
        crop_profile = (
            db.query(CropProfile)
            .filter(CropProfile.crop_name == actuator.active_crop)
            .first()
        )
        if not crop_profile:
            # Fallback default crop profile
            crop_profile = CropProfile(
                crop_name="Wheat",
                category="Cereal",
                optimal_moisture_min=50.0,
                optimal_moisture_max=70.0,
                wilting_point=30.0,
                temp_min=15.0,
                temp_max=32.0,
                kc_factor=1.05,
                growth_stage="Vegetative"
            )

        # Fallback values if no sensor telemetry exists yet
        current_moisture = latest_telemetry.soil_moisture if latest_telemetry else 48.0
        ambient_temp = latest_telemetry.temperature if latest_telemetry else 27.0
        ambient_humidity = latest_telemetry.humidity if latest_telemetry else 55.0

        # 4. Fetch Weather and Evapotranspiration
        forecast = weather_service.get_forecast()
        rain_prob = forecast.get("rain_probability", 15.0)
        expected_rain_mm = forecast.get("expected_rain_mm", 0.0)
        et0 = weather_service.calculate_et0(ambient_temp, ambient_humidity)
        etc = round(et0 * crop_profile.kc_factor, 2) # Crop evapotranspiration in mm/day

        # 5. Core Agronomic Logic
        min_moist = crop_profile.optimal_moisture_min
        max_moist = crop_profile.optimal_moisture_max
        wilt_pt = crop_profile.wilting_point

        status = "OPTIMAL"
        urgency = "NONE"
        pump_recommended = False
        duration_minutes = 0.0
        estimated_liters = 0.0
        advice_text = ""
        auto_executed = False

        # Water deficit calculation
        # 1% soil moisture deficit in top 30cm root zone ~ 3 mm water equivalent
        moisture_deficit_pct = max(0.0, ((min_moist + max_moist) / 2.0) - current_moisture)
        water_depth_mm = moisture_deficit_pct * 0.45 + (etc * 0.5)

        # 1 mm of water depth over 1 acre (4046.86 m2) = 4,046.86 Liters
        # Typical 1 HP pump delivers ~ 200 Liters/min (12,000 L/hr)
        acres = actuator.field_area_acres or 1.0
        liters_needed = water_depth_mm * 4046.86 * acres
        pump_flow_rate_lpm = 220.0 # Liters per minute for standard drip/sprinkler line

        if current_moisture >= max_moist + 5.0:
            status = "SATURATED"
            urgency = "NONE"
            pump_recommended = False
            advice_text = (
                f"Soil moisture ({current_moisture:.1f}%) is above optimal field capacity ({max_moist}%). "
                "Do NOT irrigate. Ensure adequate drainage to avoid root hypoxia."
            )
            # If pump is running in auto mode, shut it off
            if actuator.auto_mode and actuator.pump_on:
                actuator.pump_on = False
                actuator.last_switched = datetime.now(timezone.utc)
                db.add(IrrigationLog(
                    device_id=device_id,
                    event_type="AUTO_OFF",
                    trigger_reason="Soil saturation threshold reached"
                ))
                auto_executed = True

        elif rain_prob >= 60.0 and expected_rain_mm >= 6.0 and current_moisture > wilt_pt:
            status = "RAIN_PREDICTED_SKIP"
            urgency = "LOW"
            pump_recommended = False
            advice_text = (
                f"Heavy rain expected ({expected_rain_mm} mm, {rain_prob}% prob). "
                f"Irrigation deferred to conserve water. Current moisture ({current_moisture:.1f}%) is safe."
            )
            if actuator.auto_mode and actuator.pump_on:
                actuator.pump_on = False
                actuator.last_switched = datetime.now(timezone.utc)
                db.add(IrrigationLog(
                    device_id=device_id,
                    event_type="RAIN_ABORT",
                    trigger_reason=f"Aborted due to forecast rain: {expected_rain_mm}mm"
                ))
                auto_executed = True

        elif current_moisture < wilt_pt:
            status = "CRITICAL_DROUGHT"
            urgency = "CRITICAL"
            pump_recommended = True
            estimated_liters = round(liters_needed, 0)
            duration_minutes = round(min(60.0, liters_needed / pump_flow_rate_lpm), 1)
            advice_text = (
                f"CRITICAL: Soil moisture ({current_moisture:.1f}%) has breached Wilting Point ({wilt_pt}%). "
                f"Crop stress imminent! Immediate irrigation required: ~{estimated_liters:,.0f} L ({duration_minutes} mins)."
            )
            if actuator.auto_mode and not actuator.pump_on:
                actuator.pump_on = True
                actuator.last_switched = datetime.now(timezone.utc)
                db.add(IrrigationLog(
                    device_id=device_id,
                    event_type="AUTO_ON",
                    water_liters=estimated_liters,
                    duration_seconds=int(duration_minutes * 60),
                    trigger_reason="Critical drought threshold triggered"
                ))
                auto_executed = True

        elif current_moisture < min_moist:
            status = "DRY_NEEDS_WATER"
            urgency = "HIGH" if current_moisture < (min_moist - 5) else "MEDIUM"
            pump_recommended = True
            estimated_liters = round(liters_needed, 0)
            duration_minutes = round(min(45.0, liters_needed / pump_flow_rate_lpm), 1)
            advice_text = (
                f"Soil moisture ({current_moisture:.1f}%) is below optimal target ({min_moist}-{max_moist}%). "
                f"Recommended irrigation: ~{estimated_liters:,.0f} L ({duration_minutes} mins) to restore field capacity."
            )
            if actuator.auto_mode and not actuator.pump_on:
                actuator.pump_on = True
                actuator.last_switched = datetime.now(timezone.utc)
                db.add(IrrigationLog(
                    device_id=device_id,
                    event_type="AUTO_ON",
                    water_liters=estimated_liters,
                    duration_seconds=int(duration_minutes * 60),
                    trigger_reason="Soil moisture dropped below target threshold"
                ))
                auto_executed = True

        else:
            status = "OPTIMAL"
            urgency = "NONE"
            pump_recommended = False
            advice_text = (
                f"Soil moisture ({current_moisture:.1f}%) is within the optimal zone ({min_moist}-{max_moist}%) "
                f"for {crop_profile.crop_name} ({crop_profile.growth_stage} stage). No irrigation needed."
            )
            if actuator.auto_mode and actuator.pump_on and current_moisture >= ((min_moist + max_moist) / 2):
                actuator.pump_on = False
                actuator.last_switched = datetime.now(timezone.utc)
                db.add(IrrigationLog(
                    device_id=device_id,
                    event_type="AUTO_OFF",
                    trigger_reason="Target soil moisture restored"
                ))
                auto_executed = True

        db.commit()

        return IrrigationAdviceResponse(
            device_id=device_id,
            timestamp=datetime.now(timezone.utc),
            active_crop=crop_profile.crop_name,
            growth_stage=crop_profile.growth_stage,
            current_moisture=round(current_moisture, 1),
            target_min=min_moist,
            target_max=max_moist,
            status=status,
            urgency=urgency,
            pump_recommended=pump_recommended,
            recommended_duration_minutes=duration_minutes,
            estimated_water_liters=estimated_liters,
            rain_probability_pct=rain_prob,
            forecast_summary=forecast.get("summary", "Normal"),
            advice_text=advice_text,
            auto_executed=auto_executed
        )

irrigation_advisor = IrrigationAdvisor()
