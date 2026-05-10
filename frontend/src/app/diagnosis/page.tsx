"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Farm, Diagnosis } from "@/types";
import { ArrowLeft, Camera, Upload } from "lucide-react";

export default function DiagnosisPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selectedFarm, setSelectedFarm] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Diagnosis | null>(null);

  useEffect(() => {
    api.get("/farms/").then((r) => {
      setFarms(r.data);
      if (r.data.length > 0) setSelectedFarm(r.data[0].id);
    });
  }, []);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
  };

  const handleSubmit = async () => {
    if (!file || !selectedFarm) {
      toast.error("Pilih lahan dan upload foto terlebih dahulu");
      return;
    }
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post(
        `/diagnoses/?farm_id=${selectedFarm}`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResult(res.data);
      toast.success("Diagnosis selesai!");
    } catch {
      toast.error("Gagal menganalisis foto");
    } finally {
      setLoading(false);
    }
  };

  const parseSteps = (raw: string | null): string[] => {
    if (!raw) return [];
    try { return JSON.parse(raw); } catch { return [raw]; }
  };

  const urgencyStyle = (u: string | null) => {
  if (!u) return "bg-gray-100 text-gray-600";
  const lower = u.toLowerCase();
  if (lower.includes("segera") || lower.includes("24")) return "bg-red-100 text-red-700";
  if (lower.includes("minggu")) return "bg-amber-100 text-amber-700";
  return "bg-green-100 text-green-700";
};

  const confidenceColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.5) return "text-amber-600";
    return "text-red-600";
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      {/* Header */}
      <div className="bg-green-600 px-5 pt-12 pb-5 text-white flex items-center gap-3">
        <button onClick={() => router.back()} className="p-1">
          <ArrowLeft size={22} />
        </button>
        <h1 className="text-lg font-bold">Cek Penyakit Tanaman</h1>
      </div>

      <div className="px-5 pt-5 space-y-4">
        {/* Pilih lahan */}
        <div className="bg-white rounded-2xl p-4 border border-gray-100">
          <label className="text-sm text-gray-600 mb-2 block font-medium">
            Pilih Lahan
          </label>
          <select
            value={selectedFarm}
            onChange={(e) => setSelectedFarm(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} — {f.crop_type}
              </option>
            ))}
          </select>
        </div>

        {/* Upload foto */}
        <div
          onClick={() => fileRef.current?.click()}
          className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-6 text-center cursor-pointer"
        >
          {preview ? (
            <img src={preview} alt="preview" className="w-full max-h-60 object-cover rounded-xl"/>
          ) : (
            <div>
              <Camera size={40} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm font-medium">Foto daun atau bagian tanaman</p>
              <p className="text-gray-400 text-xs mt-1">JPG, PNG, WebP — max 10MB</p>
            </div>
          )}
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile}/>
        </div>

        {preview && (
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-green-600 text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Upload size={18} />
            {loading ? "Menganalisis dengan AI..." : "Analisis Sekarang"}
          </button>
        )}

        {/* Hasil diagnosis */}
        {result && (
          <div className="space-y-3 pb-6">
            {/* Header hasil */}
            <div className="bg-white rounded-2xl p-4 border border-gray-100">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Kondisi Tanaman</p>
                  <p className="font-bold text-gray-800 text-xl">{result.disease_name}</p>
                  {result.severity && (
                    <p className="text-xs text-gray-500 mt-1 capitalize">Tingkat keparahan: {result.severity}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500 mb-1">Akurasi AI</p>
                  <p className={`font-bold text-xl ${confidenceColor(result.confidence_score || 0)}`}>
                    {Math.round((result.confidence_score || 0) * 100)}%
                  </p>
                </div>
              </div>
              {result.urgency && !['tinggal','segera','lainnya'].includes(result.urgency.toLowerCase().trim()) && (
                <span className={`text-xs px-3 py-1 rounded-full font-medium ${urgencyStyle(result.urgency)}`}>
                  ⏰ {result.urgency}
                </span>
              )}    
            </div>

            {/* Yang terlihat */}
            {result.warning_signs && result.warning_signs !== '-' && (
              <div className="bg-white rounded-2xl p-4 border border-gray-100">
                <p className="text-xs font-semibold text-gray-500 mb-2">🔍 Yang terlihat di tanamanmu</p>
                <p className="text-gray-700 text-sm leading-relaxed">{result.warning_signs}</p>
              </div>
            )}

            {/* Kenapa terjadi */}
            {result.cause_explanation && (
              <div className="bg-amber-50 rounded-2xl p-4 border border-amber-100">
                <p className="text-xs font-semibold text-amber-700 mb-2">💡 Kenapa ini terjadi?</p>
                <p className="text-amber-800 text-sm leading-relaxed">{result.cause_explanation}</p>
              </div>
            )}

            {/* Langkah tindakan */}
            {parseSteps(result.action_steps).length > 0 && (
              <div className="bg-green-50 rounded-2xl p-4 border border-green-100">
                <p className="text-xs font-semibold text-green-700 mb-3">✅ Yang harus kamu lakukan</p>
                <div className="space-y-2">
                  {parseSteps(result.action_steps).map((step, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="bg-green-600 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <p className="text-green-800 text-sm leading-relaxed">{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Dampak ke panen */}
            {result.estimated_yield_impact && result.estimated_yield_impact !== '-' && (
              <div className="bg-red-50 rounded-2xl p-4 border border-red-100">
                <p className="text-xs font-semibold text-red-700 mb-2">📉 Dampak ke hasil panen</p>
                <p className="text-red-800 text-sm leading-relaxed">{result.estimated_yield_impact}</p>
              </div>
            )}

            {/* Pencegahan */}
            {result.recommendation && (
              <div className="bg-blue-50 rounded-2xl p-4 border border-blue-100">
                <p className="text-xs font-semibold text-blue-700 mb-2">🛡 Pencegahan ke depan</p>
                <p className="text-blue-800 text-sm leading-relaxed">{result.recommendation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}