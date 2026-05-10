"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ phone_number: "", password: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.phone_number || !form.password) {
      toast.error("Isi semua kolom");
      return;
    }
    setLoading(true);
    try {
      await login(form.phone_number, form.password);
      toast.success("Login berhasil!");
      router.replace("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Login gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-green-50 flex flex-col">
      {/* Header */}
      <div className="bg-green-600 px-6 pt-16 pb-10 text-white">
        <div className="text-4xl mb-3">🌱</div>
        <h1 className="text-2xl font-bold">FarmLens</h1>
        <p className="text-green-100 text-sm mt-1">
          Platform AI untuk petani Indonesia
        </p>
      </div>

      {/* Form */}
      <div className="flex-1 bg-white rounded-t-3xl -mt-4 px-6 pt-8 pb-6">
        <h2 className="text-xl font-bold text-gray-800 mb-6">Masuk</h2>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-600 mb-1 block">Nomor HP</label>
            <input
              type="tel"
              placeholder="081234567890"
              value={form.phone_number}
              onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div>
            <label className="text-sm text-gray-600 mb-1 block">Password</label>
            <input
              type="password"
              placeholder="Minimal 8 karakter"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-green-600 text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 mt-2"
          >
            {loading ? "Memproses..." : "Masuk"}
          </button>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Belum punya akun?{" "}
          <a href="/register" className="text-green-600 font-medium">
            Daftar sekarang
          </a>
        </p>
      </div>
    </div>
  );
}