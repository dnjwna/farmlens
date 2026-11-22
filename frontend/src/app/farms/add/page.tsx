"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { CheckCircle2, LocateFixed, Save } from "lucide-react";
import api, { apiErrorDetail } from "@/lib/api";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Button, Card, Field, Notice, SelectField } from "@/components/ui";

const CROP_TYPES = ["padi", "jagung", "cabai", "tomat", "kedelai", "singkong", "ubi", "lainnya"];

type FormState = { name: string; area_hectares: string; crop_type: string; latitude: string; longitude: string };
type Errors = Partial<Record<keyof FormState | "location", string>>;

export default function AddFarmPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>({ name: "", area_hectares: "", crop_type: "padi", latitude: "", longitude: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [locating, setLocating] = useState(false);
  const [saving, setSaving] = useState(false);

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const hasLocation = form.latitude !== "" && form.longitude !== "";

  const getLocation = () => {
    if (!navigator.geolocation) {
      setErrors((e) => ({ ...e, location: "HP ini tidak mendukung GPS di browser. Isi koordinat manual." }));
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((f) => ({ ...f, latitude: pos.coords.latitude.toFixed(6), longitude: pos.coords.longitude.toFixed(6) }));
        setErrors((e) => ({ ...e, location: undefined }));
        setLocating(false);
      },
      (err) => {
        setErrors((e) => ({
          ...e,
          location:
            err.code === err.PERMISSION_DENIED
              ? "Izin lokasi ditolak. Aktifkan izin lokasi untuk situs ini di pengaturan browser."
              : "Lokasi belum didapat. Coba di tempat terbuka, atau isi koordinat manual.",
        }));
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const next: Errors = {};
    const area = parseFloat(form.area_hectares);
    if (!form.name.trim()) next.name = "Beri nama lahan, misalnya Sawah Utara.";
    if (!(area > 0)) next.area_hectares = "Isi luas lahan dalam hektar, misalnya 0.5.";
    const lat = form.latitude === "" ? null : parseFloat(form.latitude);
    const lon = form.longitude === "" ? null : parseFloat(form.longitude);
    if ((lat === null) !== (lon === null)) next.location = "Isi latitude dan longitude dua-duanya.";
    else if (lat !== null && lon !== null && (Math.abs(lat) > 90 || Math.abs(lon) > 180 || isNaN(lat) || isNaN(lon)))
      next.location = "Koordinat tidak valid.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      await api.post("/farms/", {
        name: form.name.trim(),
        crop_type: form.crop_type,
        area_hectares: area,
        latitude: lat,
        longitude: lon,
      });
      toast.success("Lahan berhasil ditambahkan");
      router.replace("/dashboard");
    } catch (err) {
      toast.error(apiErrorDetail(err) || "Gagal menyimpan lahan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell withNav={false}>
      <AppHeader title="Tambah lahan" backHref="/dashboard" />

      <form onSubmit={handleSubmit} noValidate className="space-y-5 px-5 pt-5">
        <Field label="Nama lahan" placeholder="Sawah Utara" value={form.name} onChange={set("name")} error={errors.name} />
        <SelectField
          label="Jenis tanaman"
          value={form.crop_type}
          onChange={set("crop_type")}
          options={CROP_TYPES.map((c) => ({ value: c, label: c.charAt(0).toUpperCase() + c.slice(1) }))}
        />
        <Field
          label="Luas lahan (hektar)"
          type="number"
          inputMode="decimal"
          step="0.1"
          min="0"
          placeholder="0.5"
          hint="1 hektar = 10.000 m² (sekitar 100 × 100 meter)."
          value={form.area_hectares}
          onChange={set("area_hectares")}
          error={errors.area_hectares}
        />

        <Card>
          <h2 className="text-base font-bold text-foreground">Lokasi lahan</h2>
          <p className="mt-1 text-[15px] text-muted-foreground">
            Dipakai untuk cuaca, saran harian, dan membantu AI memeriksa tanaman. Paling akurat jika diisi saat kamu berada di lahan.
          </p>

          <div className="mt-4">
            {hasLocation ? (
              <Notice tone="success" icon={CheckCircle2} title="Lokasi tersimpan">
                {form.latitude}, {form.longitude}
              </Notice>
            ) : null}
            <Button variant="secondary" icon={LocateFixed} loading={locating} onClick={getLocation} className={hasLocation ? "mt-3" : ""}>
              {locating ? "Mencari lokasi..." : hasLocation ? "Ambil ulang lokasi" : "Gunakan lokasi saat ini"}
            </Button>
          </div>

          <details className="mt-4 group">
            <summary className="flex min-h-12 cursor-pointer list-none items-center text-[15px] font-semibold text-primary focus-visible:outline-2 focus-visible:outline-ring">
              Isi koordinat manual
            </summary>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Field label="Latitude" type="number" inputMode="decimal" step="any" placeholder="-6.9175" value={form.latitude} onChange={set("latitude")} />
              <Field label="Longitude" type="number" inputMode="decimal" step="any" placeholder="107.6191" value={form.longitude} onChange={set("longitude")} />
            </div>
          </details>

          {errors.location && (
            <p className="mt-3 text-sm font-medium text-destructive" role="alert">
              {errors.location}
            </p>
          )}
        </Card>

        <Button type="submit" icon={Save} loading={saving}>
          {saving ? "Menyimpan..." : "Simpan lahan"}
        </Button>
      </form>
    </PageShell>
  );
}
