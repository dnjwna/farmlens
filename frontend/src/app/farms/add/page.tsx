"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { ArrowLeft } from "lucide-react";

const CROP_TYPES = ["padi", "jagung", "cabai", "tomat", "kedelai", "singkong", "ubi", "lainnya"];

export default function AddFarmPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    area_hectares: "",
    crop_type: "padi",
    latitude: "",
    longitude: "",
  });
  const [loading, setLoading] = useState(false);

  const getLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Browser tidak mendukung geolokasi");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm({
          ...form,
          latitude: pos.coords.latitude.toFixed(6),
          longitude: pos.coords.longitude.toFixed(6),
        });
        toast.success("Lokasi berhasil didapat!");
      },
      () => toast.error("Gagal mendapatkan lokasi")
    );
  };

  const handleSubmit = async () => {
    if (!form.name || !form.area_hectares || !form.crop_type) {
      toast.error("Isi semua kolom wajib");
      return;
    }
    setLoading(true);
    try {
      await api.post("/farms/", {
        ...form,
        area_hectares: parseFloat(form.area_hectares),
        latitude: form.latitude ? parseFloat(form.latitude) : null,
        longitude: form.longitude ? parseFloat(form.longitude) : null,
      });
      toast.success("Lahan berhasil ditambahkan!");
      router.replace("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Gagal menambah lahan");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      <div className="bg-green-600 px-5 pt-12 pb-5 text-white flex items-center gap-3">
        <button onClick={() => router.back()}><ArrowLeft size={22} /></button>
        <h1 className="text-lg font-bold">Tambah Lahan</h1>
      </div>

      <div className="px-5 pt-5 space-y-4">
        <div className="bg-white rounded-2xl p-4 border border-gray-100 space-y-4">
          <div>
            <label className="text-sm text-gray-600 mb-1 block">Nama Lahan *</label>
            <input type="text" placeholder="Sawah Utara"
              value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>

          <div>
            <label className="text-sm text-gray-600 mb-1 block">Jenis Tanaman *</label>
            <select value={form.crop_type} onChange={(e) => setForm({ ...form, crop_type: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500">
              {CROP_TYPES.map((c) => <option key={c} value={c} className="capitalize">{c}</option>)}
            </select>
          </div>

          <div>
            <label className="text-sm text-gray-600 mb-1 block">Luas Lahan (hektar) *</label>
            <input type="number" placeholder="2.5" step="0.1"
              value={form.area_hectares} onChange={(e) => setForm({ ...form, area_hectares: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
          </div>

          <div>
            <label className="text-sm text-gray-600 mb-1 block">Lokasi Lahan</label>
            <button onClick={getLocation}
              className="w-full border border-green-200 text-green-600 rounded-xl px-4 py-3 text-sm font-medium mb-2">
              📍 Gunakan Lokasi Saat Ini
            </button>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" placeholder="Latitude" step="any"
                value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none" />
              <input type="number" placeholder="Longitude" step="any"
                value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none" />
            </div>
          </div>
        </div>

        <button onClick={handleSubmit} disabled={loading}
          className="w-full bg-green-600 text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50">
          {loading ? "Menyimpan..." : "Simpan Lahan"}
        </button>
      </div>
    </div>
  );
}