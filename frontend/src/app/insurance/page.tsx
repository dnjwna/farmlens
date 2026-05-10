"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Policy, Claim, Farm } from "@/types";
import { ArrowLeft, Shield, Plus } from "lucide-react";

export default function InsurancePage() {
  const router = useRouter();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    farm_id: "",
    premium_amount: 50000,
    coverage_amount: 5000000,
    duration_months: 6,
    trigger_rain_mm: 50,
    trigger_dry_days: 7,
    trigger_temp_max: 38,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const [p, c, f] = await Promise.all([
      api.get("/insurance/policies").then((r) => r.data),
      api.get("/insurance/claims").then((r) => r.data),
      api.get("/farms/").then((r) => r.data),
    ]);
    setPolicies(p);
    setClaims(c);
    setFarms(f);
    if (f.length > 0) setForm((prev) => ({ ...prev, farm_id: f[0].id }));
  };

  const handleCreate = async () => {
    setLoading(true);
    try {
      await api.post("/insurance/policies", form);
      toast.success("Polis berhasil dibuat!");
      setShowForm(false);
      loadData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Gagal membuat polis");
    } finally {
      setLoading(false);
    }
  };

  const triggerCheck = async () => {
    setLoading(true);
    try {
      const res = await api.post("/insurance/check-triggers");
      toast.success(res.data.message);
      loadData();
    } finally {
      setLoading(false);
    }
  };

  const formatRupiah = (n: number) =>
    new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      <div className="bg-purple-600 px-5 pt-12 pb-5 text-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()}><ArrowLeft size={22} /></button>
          <h1 className="text-lg font-bold">Asuransi Lahan</h1>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="bg-purple-500 p-2 rounded-xl">
          <Plus size={20} />
        </button>
      </div>

      <div className="px-5 pt-5 space-y-4">
        {/* Form buat polis */}
        {showForm && (
          <div className="bg-white rounded-2xl p-4 border border-gray-100 space-y-3">
            <h2 className="font-bold text-gray-800">Buat Polis Baru</h2>
            <select
              value={form.farm_id}
              onChange={(e) => setForm({ ...form, farm_id: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm"
            >
              {farms.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Premi/bulan (Rp)</label>
                <input type="number" value={form.premium_amount}
                  onChange={(e) => setForm({ ...form, premium_amount: +e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm mt-1" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Coverage (Rp)</label>
                <input type="number" value={form.coverage_amount}
                  onChange={(e) => setForm({ ...form, coverage_amount: +e.target.value })}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm mt-1" />
              </div>
            </div>
            <button onClick={handleCreate} disabled={loading}
              className="w-full bg-purple-600 text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50">
              {loading ? "Memproses..." : "Buat Polis"}
            </button>
          </div>
        )}

        {/* Cek trigger */}
        <button onClick={triggerCheck} disabled={loading}
          className="w-full bg-white border border-purple-200 text-purple-600 py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2">
          <Shield size={16} />
          {loading ? "Mengecek..." : "Cek Kondisi Cuaca Sekarang"}
        </button>

        {/* Daftar polis */}
        <div>
          <h2 className="font-bold text-gray-800 mb-3">Polis Aktif ({policies.length})</h2>
          {policies.length === 0 ? (
            <div className="bg-white rounded-2xl p-6 text-center text-gray-400 text-sm border border-gray-100">
              Belum ada polis. Tap + untuk membuat polis baru.
            </div>
          ) : (
            policies.map((p) => (
              <div key={p.id} className="bg-white rounded-2xl p-4 border border-gray-100 mb-3">
                <div className="flex justify-between items-center mb-2">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${p.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {p.status === "active" ? "Aktif" : p.status}
                  </span>
                  <span className="text-xs text-gray-400">
                    s/d {new Date(p.end_date).toLocaleDateString("id-ID")}
                  </span>
                </div>
                <p className="font-semibold text-gray-800">{formatRupiah(p.coverage_amount)}</p>
                <p className="text-xs text-gray-500 mt-1">Coverage • Premi {formatRupiah(p.premium_amount)}/bln</p>
                <div className="mt-2 flex gap-2 text-xs text-gray-400">
                  <span>🌧 {p.trigger_rain_mm}mm</span>
                  <span>☀️ {p.trigger_dry_days} hari kering</span>
                  <span>🌡 {p.trigger_temp_max}°C</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Riwayat klaim */}
        {claims.length > 0 && (
          <div>
            <h2 className="font-bold text-gray-800 mb-3">Riwayat Klaim ({claims.length})</h2>
            {claims.map((c) => (
              <div key={c.id} className="bg-white rounded-2xl p-4 border border-gray-100 mb-3">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-semibold text-gray-800 capitalize">{c.trigger_type.replace("_", " ")}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {c.trigger_value} {">"} threshold {c.trigger_threshold}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-green-600">{formatRupiah(c.claim_amount)}</p>
                    <p className="text-xs text-gray-400 mt-1 capitalize">{c.status}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}