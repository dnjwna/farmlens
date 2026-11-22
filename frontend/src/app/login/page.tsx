"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { describeLoadError } from "@/lib/api";
import { login } from "@/lib/auth";
import { AuthLayout, isValidPhone, normalizePhone } from "@/components/AuthLayout";
import { Button, Field, Notice, PasswordField } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ phone?: string; password?: string }>({});
  const [loading, setLoading] = useState(false);
  const [sessionEnded, setSessionEnded] = useState(false);

  // Read the query string on the client only (avoids a Suspense boundary for useSearchParams).
  useEffect(() => {
    const ended = new URLSearchParams(window.location.search).get("sesi") === "berakhir";
    if (ended) setSessionEnded(true); // eslint-disable-line react-hooks/set-state-in-effect
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const next: typeof errors = {};
    if (!isValidPhone(phone)) next.phone = "Masukkan nomor HP yang diawali 08 atau +62.";
    if (!password) next.password = "Masukkan password.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setLoading(true);
    try {
      await login(normalizePhone(phone), password);
      router.replace("/dashboard");
    } catch (err) {
      console.error("[FarmLens] login failed", err);
      setErrors({ password: describeLoadError(err, "Login gagal. Coba lagi.") });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Masuk" subtitle="Gunakan nomor HP yang kamu daftarkan.">
      {sessionEnded && (
        <Notice tone="warning" className="mb-5">
          Sesi kamu berakhir. Silakan masuk lagi.
        </Notice>
      )}
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <Field
          label="Nomor HP"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="0812 3456 7890"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          error={errors.phone}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        <div className="-mt-2 text-right">
          <Link
            href="/lupa-password"
            className="inline-block py-2 text-[15px] font-semibold text-primary underline-offset-4 hover:underline"
          >
            Lupa password?
          </Link>
        </div>
        <Button type="submit" loading={loading} icon={LogIn}>
          {loading ? "Memeriksa..." : "Masuk"}
        </Button>
      </form>

      <p className="mt-8 text-center text-[15px] text-muted-foreground">
        Belum punya akun?{" "}
        <Link href="/register" className="inline-block py-2 font-bold text-primary underline-offset-4 hover:underline">
          Daftar sekarang
        </Link>
      </p>
    </AuthLayout>
  );
}
