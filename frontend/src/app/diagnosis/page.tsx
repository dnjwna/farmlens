"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { Farm, Diagnosis } from "@/types";
import { ArrowLeft, Camera, Upload } from "lucide-react";
import { useEffect } from "react";

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
            <img
              src={preview}
              alt="preview"
              className="w-full max-h-60 object-cover rounded-xl"
            />
          ) : (
            <div>
              <Camera size={40} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm font-medium">
                Foto daun atau bagian tanaman
              </p>
              <p className="text-gray-400 text-xs mt-1">JPG, PNG, WebP — max 10MB</p>
            </div>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFile}
          />
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
          <div className="bg-white rounded-2xl p-4 border border-gray-100 space-y-3">
            <h2 className="font-bold text-gray-800">Hasil Diagnosis</h2>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs text-gray-500">Kondisi Tanaman</p>
                <p className="font-semibold text-gray-800 text-lg">
                  {result.disease_name}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Akurasi</p>
                <p className={`font-bold text-lg ${confidenceColor(result.confidence_score || 0)}`}>
                  {Math.round((result.confidence_score || 0) * 100)}%
                </p>
              </div>
            </div>

            <div className="bg-green-50 rounded-xl p-3">
              <p className="text-xs font-semibold text-green-800 mb-1">
                💊 Rekomendasi
              </p>
              <p className="text-green-700 text-sm leading-relaxed">
                {result.recommendation}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}