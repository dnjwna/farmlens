export interface Farmer {
  id: string;
  full_name: string;
  phone_number: string;
  province: string | null;
  city: string | null;
  created_at: string;
}

export interface Farm {
  id: string;
  farmer_id: string;
  name: string;
  area_hectares: number;
  crop_type: string;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
}

export interface Diagnosis {
  id: string;
  farmer_id: string;
  farm_id: string;
  image_url: string;
  disease_name: string | null;
  confidence_score: number | null;
  recommendation: string | null;
  created_at: string;
}

export interface WeatherCurrent {
  temperature: number;
  humidity: number;
  precipitation: number;
  weather: string;
  wind_speed: number;
}

export interface WeatherDay {
  date: string;
  weather: string;
  temp_max: number;
  temp_min: number;
  rain_mm: number;
  humidity_max: number;
  humidity_min: number;
}

export interface WeatherData {
  farm_name: string;
  crop_type: string;
  location: { latitude: number; longitude: number };
  current: WeatherCurrent;
  forecast_7_days: WeatherDay[];
  farming_advice: string;
}

export interface Policy {
  id: string;
  farmer_id: string;
  farm_id: string;
  status: string;
  premium_amount: number;
  coverage_amount: number;
  start_date: string;
  end_date: string;
  trigger_rain_mm: number;
  trigger_dry_days: number;
  trigger_temp_max: number;
  created_at: string;
}

export interface Claim {
  id: string;
  policy_id: string;
  farmer_id: string;
  trigger_type: string;
  trigger_value: number;
  trigger_threshold: number;
  claim_amount: number;
  status: string;
  weather_date: string;
  created_at: string;
}