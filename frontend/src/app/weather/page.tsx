"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { Farm, WeatherData } from "@/types";
import { ArrowLeft } from "lucide-react";

export default function WeatherPage() {
  const router = useRouter();
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarm, setSelectedFarm] = useState("");
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/farms/").then((r) => {
      setFarms(r.data);
      if (r.data.length > 0) {
        setSelectedFarm(r.data[0].id);
        fetchWeather(r.data[0].id);
      }
    });
  }, []);

  const fetchWeather = async (farmId: string) => {
    setLoading(true);
    try {
      const res = await api.get(`/weather/farm/${farmId}`);
      setWeather(res.data);
    } finally {
      setLoading(false);
    }
  };

  const weatherEmoji = (desc: string) => {
    if (desc.includes("Cerah")) return "☀️";
    if (desc.includes("Berawan") || desc.includes("Mendung")) return "⛅";
    if (desc.includes("Hujan") || desc.includes("Gerimis")) return "🌧️";
    if (desc.includes("Badai")) return "⛈️";
    return "🌤️";
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      <div className="bg-blue-600 px-5 pt-12 pb-5 text-white flex items-center gap-3">
        <button onClick={() => router.back()} className="p-1">
          <ArrowLeft size={22} />
        </button>
        <h1 className="text-lg font-bold">Cuaca Lahan</h1>
      </div>

      <div className="px-5 pt-5 space-y-4">
        {/* Pilih lahan */}
        <select
          value={selectedFarm}
          onChange={(e) => { setSelectedFarm(e.target.value); fetchWeather(e.target.value); }}
          className="w-full bg-white border border-gray-200 rounded-xl px-3 py-3 text-sm focus:outline-none"
        >
          {farms.map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>

        {loading && (
          <div className="text-center py-10 text-gray-400">Memuat data cuaca...</div>
        )}

        {weather && !loading && (
          <>
            {/* Cuaca sekarang */}
            <div className="bg-blue-600 rounded-2xl p-5 text-white">
              <p className="text-blue-200 text-xs">{weather.farm_name} — Sekarang</p>
              <div className="flex items-center justify-between mt-2">
                <div>
                  <p className="text-5xl font-bold">{weather.current.temperature}°</p>
                  <p className="text-blue-200 mt-1">{weather.current.weather}</p>
                </div>
                <div className="text-right text-sm text-blue-200 space-y-1">
                  <p>💧 Kelembaban {weather.current.humidity}%</p>
                  <p>💨 Angin {weather.current.wind_speed} km/h</p>
                  <p>🌧 Hujan {weather.current.precipitation}mm</p>
                </div>
              </div>
            </div>

            {/* Rekomendasi */}
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
              <p className="text-amber-800 text-xs font-semibold mb-1">💡 Rekomendasi</p>
              <p className="text-amber-700 text-sm leading-relaxed">{weather.farming_advice}</p>
            </div>

            {/* Forecast 7 hari */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              <p className="font-bold text-gray-800 px-4 pt-4 pb-2">Prakiraan 7 Hari</p>
              {weather.forecast_7_days.map((day, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-3 border-t border-gray-50">
                  <div className="flex items-center gap-3 w-24">
                    <span className="text-xl">{weatherEmoji(day.weather)}</span>
                    <span className="text-xs text-gray-500">
                      {i === 0 ? "Hari ini" : new Date(day.date).toLocaleDateString("id-ID", { weekday: "short" })}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400 flex-1 text-center">{day.weather}</span>
                  <div className="flex gap-2 text-sm">
                    <span className="font-semibold text-gray-800">{day.temp_max}°</span>
                    <span className="text-gray-400">{day.temp_min}°</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}