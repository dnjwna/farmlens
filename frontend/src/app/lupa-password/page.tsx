"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { ArrowLeft, KeyRound, MessageCircle } from "lucide-react";
import { apiErrorDetail } from "@/lib/api";
import { requestPasswordReset, resetPassword } from "@/lib/auth";
import { AuthLayout, isValidPhone, normalizePhone } from "@/components/AuthLayout";
import { Button, Field, Notice, PasswordField } from "@/components/ui";

const RESEND_SECONDS = 60;

type Step = "phone" | "code";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{ phone?: string; code?: string; password?: string; confirm?: string }>({});
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const sendCode = async () => {
    setSending(true);
    try {
      await requestPasswordReset(normalizePhone(phone));
      setStep("code");
      setCooldown(RESEND_SECONDS);
      setErrors({});
      return true;
    } catch (err) {
      setErrors({ phone: apiErrorDetail(err) || "Gagal mengirim kode. Coba lagi." });
      return false;
    } finally {
      setSending(false);
    }
  };

  const handlePhoneSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!isValidPhone(phone)) {
      setErrors({ phone: "Masukkan nomor HP yang diawali 08 atau +62." });
      return;
    }
    await sendCode();
  };

  const handleResend = async () => {
    if (cooldown > 0 || sending) return;
    if (await sendCode()) toast.success("Kode baru dikirim. Kode sebelumnya tidak berlaku lagi.");
    else toast.error("Gagal mengirim ulang kode.");
  };

  const handleResetSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const next: typeof errors = {};
    if (!/^\d{6}$/.test(code)) next.code = "Kode terdiri dari 6 angka.";
    if (password.length < 8) next.password = "Password minimal 8 karakter.";
    if (confirm !== password) next.confirm = "Password tidak sama.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      await resetPassword(normalizePhone(phone), code, password);
      toast.success("Password berhasil diganti");
      router.replace("/dashboard");
    } catch (err) {
      setErrors({ code: apiErrorDetail(err) || "Gagal mengganti password. Coba lagi." });
    } finally {
      setSaving(false);
    }
  };

  if (step === "phone") {
    return (
      <AuthLayout title="Lupa password" subtitle="Kami kirim kode lewat WhatsApp ke nomor yang kamu daftarkan.">
        <form onSubmit={handlePhoneSubmit} noValidate className="space-y-5">
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
          <Button type="submit" loading={sending} icon={MessageCircle}>
            {sending ? "Mengirim..." : "Kirim kode"}
          </Button>
        </form>
        <BackToLogin />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Masukkan kode" subtitle={`Cek WhatsApp di nomor ${normalizePhone(phone)}.`}>
      <Notice tone="info" className="mb-5">
        Kode berlaku 10 menit. Jangan berikan kode ini ke siapa pun. Kalau WhatsApp tidak masuk, minta bantuan
        penyuluh atau admin FarmLens untuk kode cadangan.
      </Notice>

      <form onSubmit={handleResetSubmit} noValidate className="space-y-5">
        <Field
          label="Kode 6 angka"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="123456"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
          error={errors.code}
          className="[&_input]:tracking-[0.4em] [&_input]:text-lg [&_input]:font-bold"
        />
        <PasswordField
          label="Password baru"
          autoComplete="new-password"
          hint="Minimal 8 karakter."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        <PasswordField
          label="Ulangi password baru"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={errors.confirm}
        />
        <Button type="submit" loading={saving} icon={KeyRound}>
          {saving ? "Menyimpan..." : "Simpan password baru"}
        </Button>
      </form>

      <div className="mt-6 flex flex-col items-center gap-1 text-[15px]">
        <button
          type="button"
          onClick={handleResend}
          disabled={cooldown > 0 || sending}
          className="cursor-pointer py-2 font-semibold text-primary disabled:cursor-not-allowed disabled:text-muted-foreground"
        >
          {cooldown > 0 ? `Kirim ulang kode dalam ${cooldown} detik` : "Kirim ulang kode"}
        </button>
        <button
          type="button"
          onClick={() => {
            setStep("phone");
            setCode("");
            setErrors({});
          }}
          className="cursor-pointer py-2 text-muted-foreground underline-offset-4 hover:underline"
        >
          Ganti nomor HP
        </button>
      </div>
    </AuthLayout>
  );
}

function BackToLogin() {
  return (
    <p className="mt-8 text-center text-[15px]">
      <Link
        href="/login"
        className="inline-flex items-center gap-1.5 py-2 font-bold text-primary underline-offset-4 hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Kembali ke halaman masuk
      </Link>
    </p>
  );
}
