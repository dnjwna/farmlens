"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { getMe, logout } from "@/lib/auth";
import api from "@/lib/api";
import { Farmer, Farm, WeatherData } from "@/types";
import { Cloud, Leaf, Shield, LogOut, Plus, Camera } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [farmer, setFarmer] = useState<Farmer | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [farmerData, farmsData] = await Promise.all([
        getMe(),
        api.get("/farms/").then((r) => r.data),
      ]);
      setFarmer(farmerData);
      setFarms(farmsData);

      // Ambil cuaca lahan pertama kalau ada
      if (farmsData.length > 0 && farmsData[0].latitude) {
        const w = await api.get(`/weather/farm/${farmsData[0].id}`);
        setWeather(w.data);
      }
    } catch {
      toast.error("Gagal memuat data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-green-50">
        <div className="text-center">
          <div className="text-4xl mb-2">🌱</div>
          <p className="text-green-700">Memuat data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {/* Header */}
      <div className="bg-green-600 px-5 pt-12 pb-6 text-white">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-green-200 text-sm">Selamat datang,</p>
            <h1 className="text-xl font-bold">{farmer?.full_name}</h1>
            <p className="text-green-200 text-xs mt-1">
              {farmer?.city}, {farmer?.province}
            </p>
          </div>
          <button onClick={logout} className="p-2 rounded-full bg-green-700">
            <LogOut size={18} />
          </button>
        </div>

        {/* Cuaca ringkas */}
        {weather && (
          <div className="mt-4 bg-green-700 rounded-2xl p-4">
            <p className="text-green-200 text-xs mb-1">{weather.farm_name}</p>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-3xl font-bold">
                  {weather.current.temperature}°C
                </span>
                <p className="text-green-200 text-sm">{weather.current.weather}</p>
              </div>
              <div className="text-right text-sm text-green-200">
                <p>💧 {weather.current.humidity}%</p>
                <p>💨 {weather.current.wind_speed} km/h</p>
                <p>🌧 {weather.current.precipitation}mm</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="px-5 pt-5 space-y-5">
        {/* Farming advice */}
        {weather && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
            <p className="text-amber-800 text-xs font-semibold mb-1">
              💡 Rekomendasi Hari Ini
            </p>
            <p className="text-amber-700 text-sm leading-relaxed">
              {weather.farming_advice}
            </p>
          </div>
        )}

        {/* Menu utama */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => router.push("/diagnosis")}
            className="bg-white rounded-2xl p-4 text-left shadow-sm border border-gray-100"
          >
            <div className="bg-green-100 w-10 h-10 rounded-xl flex items-center justify-center mb-3">
              <Camera size={20} className="text-green-600" />
            </div>
            <p className="font-semibold text-gray-800 text-sm">Cek Penyakit</p>
            <p className="text-gray-500 text-xs mt-1">Foto tanaman kamu</p>
          </button>

          <button
            onClick={() => router.push("/weather")}
            className="bg-white rounded-2xl p-4 text-left shadow-sm border border-gray-100"
          >
            <div className="bg-blue-100 w-10 h-10 rounded-xl flex items-center justify-center mb-3">
              <Cloud size={20} className="text-blue-600" />
            </div>
            <p className="font-semibold text-gray-800 text-sm">Cuaca 7 Hari</p>
            <p className="text-gray-500 text-xs mt-1">Prakiraan lahan kamu</p>
          </button>

          <button
            onClick={() => router.push("/farms")}
            className="bg-white rounded-2xl p-4 text-left shadow-sm border border-gray-100"
          >
            <div className="bg-emerald-100 w-10 h-10 rounded-xl flex items-center justify-center mb-3">
              <Leaf size={20} className="text-emerald-600" />
            </div>
            <p className="font-semibold text-gray-800 text-sm">Lahan Saya</p>
            <p className="text-gray-500 text-xs mt-1">{farms.length} lahan terdaftar</p>
          </button>

          <button
            onClick={() => router.push("/insurance")}
            className="bg-white rounded-2xl p-4 text-left shadow-sm border border-gray-100"
          >
            <div className="bg-purple-100 w-10 h-10 rounded-xl flex items-center justify-center mb-3">
              <Shield size={20} className="text-purple-600" />
            </div>
            <p className="font-semibold text-gray-800 text-sm">Asuransi</p>
            <p className="text-gray-500 text-xs mt-1">Polis & klaim otomatis</p>
          </button>
        </div>

        {/* Daftar lahan */}
        <div>
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-bold text-gray-800">Lahan Saya</h2>
            <button
              onClick={() => router.push("/farms/add")}
              className="flex items-center gap-1 text-green-600 text-sm font-medium"
            >
              <Plus size={16} /> Tambah
            </button>
          </div>

          {farms.length === 0 ? (
            <div className="bg-white rounded-2xl p-6 text-center border border-gray-100">
              <p className="text-gray-400 text-sm">Belum ada lahan terdaftar</p>
              <button
                onClick={() => router.push("/farms/add")}
                className="mt-3 bg-green-600 text-white px-4 py-2 rounded-xl text-sm font-medium"
              >
                Tambah Lahan
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {farms.map((farm) => (
                <div
                  key={farm.id}
                  className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-semibold text-gray-800">{farm.name}</p>
                      <p className="text-gray-500 text-xs mt-1 capitalize">
                        {farm.crop_type} • {farm.area_hectares} ha
                      </p>
                    </div>
                    <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full">
                      Aktif
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}