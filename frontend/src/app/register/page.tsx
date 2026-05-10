"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { register, login } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "",
    phone_number: "",
    password: "",
    province: "",
    city: "",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.full_name || !form.phone_number || !form.password) {
      toast.error("Nama, nomor HP, dan password wajib diisi");
      return;
    }
    setLoading(true);
    try {
      await register(form);
      await login(form.phone_number, form.password);
      toast.success("Akun berhasil dibuat!");
      router.replace("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Registrasi gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-green-50 flex flex-col">
      <div className="bg-green-600 px-6 pt-16 pb-10 text-white">
        <div className="text-4xl mb-3">🌱</div>
        <h1 className="text-2xl font-bold">FarmLens</h1>
        <p className="text-green-100 text-sm mt-1">Daftar akun baru</p>
      </div>

      <div className="flex-1 bg-white rounded-t-3xl -mt-4 px-6 pt-8 pb-6">
        <h2 className="text-xl font-bold text-gray-800 mb-6">Buat Akun</h2>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-600 mb-1 block">Nama Lengkap</label>
            <input
              type="text"
              placeholder="Budi Santoso"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

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

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-sm text-gray-600 mb-1 block">Provinsi</label>
              <input
                type="text"
                placeholder="Jawa Barat"
                value={form.province}
                onChange={(e) => setForm({ ...form, province: e.target.value })}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div className="flex-1">
              <label className="text-sm text-gray-600 mb-1 block">Kota</label>
              <input
                type="text"
                placeholder="Bandung"
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-green-600 text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 mt-2"
          >
            {loading ? "Memproses..." : "Buat Akun"}
          </button>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Sudah punya akun?{" "}
          <a href="/login" className="text-green-600 font-medium">
            Masuk
          </a>
        </p>
      </div>
    </div>
  );
}