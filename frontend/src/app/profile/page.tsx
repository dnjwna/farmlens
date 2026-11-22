"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { KeyRound, LogOut, Phone, Save, Trash2, UserRound } from "lucide-react";
import { apiErrorDetail } from "@/lib/api";
import { changePassword, deleteAccount, getMe, logout, updateMe } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { formatPhone } from "@/lib/phone";
import type { Farmer } from "@/types";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Button, Card, ConfirmDialog, Field, PasswordField, Skeleton } from "@/components/ui";

export default function ProfilePage() {
  const router = useRouter();
  const [farmer, setFarmer] = useState<Farmer | null>(null);

  // Edit profile
  const [profile, setProfile] = useState({ full_name: "", province: "", city: "" });
  const [profileError, setProfileError] = useState<string | undefined>();
  const [savingProfile, setSavingProfile] = useState(false);

  // Change password
  const [pw, setPw] = useState({ current: "", next: "" });
  const [pwErrors, setPwErrors] = useState<{ current?: string; next?: string }>({});
  const [savingPw, setSavingPw] = useState(false);

  // Delete account
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePw, setDeletePw] = useState("");
  const [deleteError, setDeleteError] = useState<string | undefined>();
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    getMe()
      .then((f) => {
        setFarmer(f);
        setProfile({ full_name: f.full_name, province: f.province ?? "", city: f.city ?? "" });
      })
      .catch(() => toast.error("Gagal memuat profil."));
  }, []);

  const profileChanged =
    !!farmer &&
    (profile.full_name.trim() !== farmer.full_name ||
      profile.province.trim() !== (farmer.province ?? "") ||
      profile.city.trim() !== (farmer.city ?? ""));

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    if (profile.full_name.trim().length < 2) {
      setProfileError("Nama minimal 2 karakter.");
      return;
    }
    setProfileError(undefined);
    setSavingProfile(true);
    try {
      const updated = await updateMe({
        full_name: profile.full_name.trim(),
        province: profile.province.trim() || null,
        city: profile.city.trim() || null,
      });
      setFarmer(updated);
      setProfile({ full_name: updated.full_name, province: updated.province ?? "", city: updated.city ?? "" });
      toast.success("Profil disimpan");
    } catch (err) {
      toast.error(apiErrorDetail(err) || "Gagal menyimpan profil.");
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    const errs: typeof pwErrors = {};
    if (!pw.current) errs.current = "Masukkan password saat ini.";
    if (pw.next.length < 8) errs.next = "Password baru minimal 8 karakter.";
    else if (pw.next === pw.current) errs.next = "Password baru harus berbeda dari yang lama.";
    setPwErrors(errs);
    if (Object.keys(errs).length) return;

    setSavingPw(true);
    try {
      await changePassword(pw.current, pw.next);
      setPw({ current: "", next: "" });
      toast.success("Password diganti. Perangkat lain otomatis keluar.");
    } catch (err) {
      const detail = apiErrorDetail(err);
      if (detail?.toLowerCase().includes("lama")) setPwErrors({ current: detail });
      else toast.error(detail || "Gagal mengganti password.");
    } finally {
      setSavingPw(false);
    }
  };

  const confirmDeleteAccount = async () => {
    setDeleting(true);
    setDeleteError(undefined);
    try {
      await deleteAccount(deletePw);
      toast.success("Akun dan semua datamu sudah dihapus");
      router.replace("/login");
    } catch (err) {
      setDeleteError(apiErrorDetail(err) || "Gagal menghapus akun. Coba lagi.");
      setDeleting(false);
    }
  };

  return (
    <PageShell busy={!farmer}>
      <AppHeader title="Akun saya" backHref="/dashboard" />

      <div className="space-y-5 px-5 pt-5">
        {!farmer ? (
          <div className="space-y-4" role="status">
            <span className="sr-only">Memuat profil...</span>
            <Skeleton className="h-24 w-full rounded-2xl" />
            <Skeleton className="h-72 w-full rounded-2xl" />
          </div>
        ) : (
          <>
            {/* Identity */}
            <Card className="flex items-center gap-4">
              <span className="inline-flex size-14 shrink-0 items-center justify-center rounded-full bg-primary text-xl font-extrabold text-on-primary" aria-hidden="true">
                {farmer.full_name.charAt(0).toUpperCase()}
              </span>
              <div className="min-w-0">
                <p className="truncate text-lg font-bold text-foreground">{farmer.full_name}</p>
                <p className="flex items-center gap-1.5 text-[15px] text-muted-foreground">
                  <Phone className="size-4" aria-hidden="true" />
                  {formatPhone(farmer.phone_number)}
                </p>
                <p className="text-sm text-muted-foreground">Bergabung {formatDate(farmer.created_at)}</p>
              </div>
            </Card>

            {/* Edit profile */}
            <Card>
              <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-foreground">
                <UserRound className="size-5 text-primary" aria-hidden="true" /> Data diri
              </h2>
              <form onSubmit={saveProfile} noValidate className="space-y-4">
                <Field
                  label="Nama lengkap"
                  autoComplete="name"
                  value={profile.full_name}
                  onChange={(e) => setProfile((p) => ({ ...p, full_name: e.target.value }))}
                  error={profileError}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Provinsi" autoComplete="address-level1" value={profile.province} onChange={(e) => setProfile((p) => ({ ...p, province: e.target.value }))} />
                  <Field label="Kota/Kab." autoComplete="address-level2" value={profile.city} onChange={(e) => setProfile((p) => ({ ...p, city: e.target.value }))} />
                </div>
                <p className="text-sm text-muted-foreground">Nomor HP dipakai untuk masuk, jadi tidak bisa diubah di sini.</p>
                <Button type="submit" size="md" icon={Save} loading={savingProfile} disabled={!profileChanged}>
                  Simpan perubahan
                </Button>
              </form>
            </Card>

            {/* Change password */}
            <Card>
              <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-foreground">
                <KeyRound className="size-5 text-primary" aria-hidden="true" /> Ganti password
              </h2>
              <form onSubmit={savePassword} noValidate className="space-y-4">
                <PasswordField
                  label="Password saat ini"
                  autoComplete="current-password"
                  value={pw.current}
                  onChange={(e) => setPw((p) => ({ ...p, current: e.target.value }))}
                  error={pwErrors.current}
                />
                <PasswordField
                  label="Password baru"
                  autoComplete="new-password"
                  hint="Minimal 8 karakter."
                  value={pw.next}
                  onChange={(e) => setPw((p) => ({ ...p, next: e.target.value }))}
                  error={pwErrors.next}
                />
                <Button type="submit" size="md" variant="secondary" icon={KeyRound} loading={savingPw}>
                  Ganti password
                </Button>
              </form>
            </Card>

            <Button variant="secondary" icon={LogOut} onClick={logout}>
              Keluar
            </Button>

            {/* Danger zone */}
            <section aria-labelledby="danger-heading" className="rounded-2xl border border-danger-border bg-danger-soft p-4 text-danger-strong">
              <h2 id="danger-heading" className="text-base font-bold">
                Hapus akun
              </h2>
              <p className="mt-1 text-[15px] leading-relaxed">
                Semua datamu dihapus permanen: lahan, riwayat pemeriksaan beserta fotonya, polis, dan klaim asuransi. Tindakan ini
                tidak bisa dibatalkan.
              </p>
              <Button
                variant="danger"
                size="md"
                icon={Trash2}
                className="mt-4"
                onClick={() => {
                  setDeletePw("");
                  setDeleteError(undefined);
                  setDeleteOpen(true);
                }}
              >
                Hapus akun saya
              </Button>
            </section>

            <p className="pb-2 text-center text-sm text-muted-foreground">FarmLens · versi uji coba</p>
          </>
        )}
      </div>

      <ConfirmDialog
        open={deleteOpen}
        title="Hapus akun secara permanen?"
        confirmLabel="Hapus akun"
        loading={deleting}
        confirmDisabled={!deletePw}
        onConfirm={confirmDeleteAccount}
        onCancel={() => setDeleteOpen(false)}
      >
        <p>Masukkan password untuk memastikan ini benar kamu.</p>
        <PasswordField
          className="mt-3 text-foreground"
          label="Password"
          autoComplete="current-password"
          value={deletePw}
          onChange={(e) => setDeletePw(e.target.value)}
          error={deleteError}
        />
      </ConfirmDialog>
    </PageShell>
  );
}
