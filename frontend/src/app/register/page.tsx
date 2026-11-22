"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { UserPlus } from "lucide-react";
import { apiErrorDetail } from "@/lib/api";
import { login, register } from "@/lib/auth";
import { AuthLayout, isValidPhone, normalizePhone } from "@/components/AuthLayout";
import { Button, Field, PasswordField } from "@/components/ui";

type FormState = { full_name: string; phone_number: string; password: string; province: string; city: string };
type Errors = Partial<Record<keyof FormState, string>>;

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>({ full_name: "", phone_number: "", password: "", province: "", city: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [loading, setLoading] = useState(false);

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const next: Errors = {};
    if (form.full_name.trim().length < 2) next.full_name = "Masukkan nama lengkap.";
    if (!isValidPhone(form.phone_number)) next.phone_number = "Masukkan nomor HP yang diawali 08 atau +62.";
    if (form.password.length < 8) next.password = "Password minimal 8 karakter.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setLoading(true);
    try {
      const payload = { ...form, full_name: form.full_name.trim(), phone_number: normalizePhone(form.phone_number) };
      await register(payload);
      await login(payload.phone_number, payload.password);
      toast.success("Akun berhasil dibuat");
      router.replace("/dashboard");
    } catch (err) {
      const detail = apiErrorDetail(err);
      if (typeof detail === "string" && detail.toLowerCase().includes("nomor")) {
        setErrors({ phone_number: detail });
      } else {
        toast.error(typeof detail === "string" ? detail : "Pendaftaran gagal. Periksa data lalu coba lagi.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Buat akun" subtitle="Cukup sekali. Data ini dipakai untuk lahan dan cuacamu.">
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Field label="Nama lengkap" autoComplete="name" value={form.full_name} onChange={set("full_name")} error={errors.full_name} />
        <Field
          label="Nomor HP"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="0812 3456 7890"
          value={form.phone_number}
          onChange={set("phone_number")}
          error={errors.phone_number}
        />
        <PasswordField
          label="Password"
          autoComplete="new-password"
          hint="Minimal 8 karakter."
          value={form.password}
          onChange={set("password")}
          error={errors.password}
        />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Provinsi" autoComplete="address-level1" placeholder="Jawa Barat" value={form.province} onChange={set("province")} />
          <Field label="Kota/Kab." autoComplete="address-level2" placeholder="Bandung" value={form.city} onChange={set("city")} />
        </div>
        <Button type="submit" loading={loading} icon={UserPlus}>
          {loading ? "Membuat akun..." : "Buat akun"}
        </Button>
      </form>

      <p className="mt-8 text-center text-[15px] text-muted-foreground">
        Sudah punya akun?{" "}
        <Link href="/login" className="inline-block py-2 font-bold text-primary underline-offset-4 hover:underline">
          Masuk
        </Link>
      </p>
    </AuthLayout>
  );
}
