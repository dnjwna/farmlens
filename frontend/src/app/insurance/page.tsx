"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { CalendarClock, CalendarDays, CloudRain, FlaskConical, MapPinOff, Plus, ShieldCheck, SunDim, Thermometer, X } from "lucide-react";
import api, { apiErrorDetail } from "@/lib/api";
import { parseServerDate } from "@/lib/format";
import { Claim, Farm, Policy } from "@/types";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Badge, Button, Card, Field, Notice, SelectField, Skeleton, formatRupiah } from "@/components/ui";

const CLAIM_LABEL: Record<string, { label: string; unit: string }> = {
  banjir: { label: "Hujan ekstrem", unit: "mm" },
  kekeringan: { label: "Kekeringan", unit: "hari berturut-turut tanpa hujan" },
  suhu_ekstrem: { label: "Suhu ekstrem", unit: "°C" },
};

const formatDate = (iso: string) =>
  parseServerDate(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

type PolicyForm = {
  farm_id: string;
  premium_amount: number;
  coverage_amount: number;
  duration_months: number;
  trigger_rain_mm: number;
  trigger_dry_days: number;
  trigger_temp_max: number;
};

const DEFAULT_FORM: PolicyForm = {
  farm_id: "",
  premium_amount: 50000,
  coverage_amount: 5000000,
  duration_months: 6,
  trigger_rain_mm: 50,
  trigger_dry_days: 7,
  trigger_temp_max: 38,
};

function fetchInsuranceData() {
  return Promise.all([
    api.get<Policy[]>("/insurance/policies").then((r) => r.data),
    api.get<Claim[]>("/insurance/claims").then((r) => r.data),
    api.get<Farm[]>("/farms/").then((r) => r.data),
  ]);
}

export default function InsurancePage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<PolicyForm>(DEFAULT_FORM);

  const applyData = useCallback(([p, c, f]: [Policy[], Claim[], Farm[]]) => {
    setPolicies(p);
    setClaims(c);
    setFarms(f);
    const eligible = f.filter((x) => x.latitude !== null && x.longitude !== null);
    setForm((prev) => (prev.farm_id || eligible.length === 0 ? prev : { ...prev, farm_id: eligible[0].id }));
  }, []);

  const loadData = useCallback(async () => {
    try {
      applyData(await fetchInsuranceData());
    } catch {
      toast.error("Gagal memuat data asuransi.");
    }
  }, [applyData]);

  useEffect(() => {
    fetchInsuranceData()
      .then(applyData)
      .catch(() => toast.error("Gagal memuat data asuransi."))
      .finally(() => setInitialLoading(false));
  }, [applyData]);

  const eligibleFarms = farms.filter((f) => f.latitude !== null && f.longitude !== null);

  const setNum = (key: keyof PolicyForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: Number(e.target.value) }));

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/insurance/policies", form);
      toast.success("Polis berhasil dibuat");
      setShowForm(false);
      await loadData();
    } catch (err) {
      toast.error(apiErrorDetail(err) || "Gagal membuat polis");
    } finally {
      setCreating(false);
    }
  };

  return (
    <PageShell busy={initialLoading}>
      <AppHeader
        title="Asuransi lahan"
        backHref="/dashboard"
        action={
          !showForm && eligibleFarms.length > 0 ? (
            <Button size="md" variant="ghost" fullWidth={false} icon={Plus} onClick={() => setShowForm(true)}>
              Polis baru
            </Button>
          ) : undefined
        }
      />

      <div className="space-y-5 px-5 pt-5">
        <Notice tone="warning" icon={FlaskConical} title="Mode simulasi">
          Polis dan klaim di sini belum terhubung ke perusahaan asuransi berizin, jadi belum ada pembayaran sungguhan.
        </Notice>

        {showForm && (
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Polis baru</h2>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                aria-label="Tutup formulir"
                className="inline-flex size-12 cursor-pointer items-center justify-center rounded-full text-muted-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <SelectField
                label="Lahan"
                value={form.farm_id}
                onChange={(e) => setForm((f) => ({ ...f, farm_id: e.target.value }))}
                options={eligibleFarms.map((f) => ({ value: f.id, label: f.name }))}
              />
              {eligibleFarms.length < farms.length && (
                <p className="-mt-2 flex items-start gap-1.5 text-sm text-muted-foreground">
                  <MapPinOff className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                  Lahan tanpa lokasi tidak bisa diasuransikan karena cuacanya tidak bisa dipantau.
                </p>
              )}
              <div className="grid grid-cols-2 gap-3">
                <Field label="Premi per bulan (Rp)" type="number" inputMode="numeric" min={0} step={1000} value={form.premium_amount} onChange={setNum("premium_amount")} />
                <Field label="Nilai perlindungan (Rp)" type="number" inputMode="numeric" min={0} step={100000} value={form.coverage_amount} onChange={setNum("coverage_amount")} />
              </div>
              <SelectField
                label="Lama perlindungan"
                value={String(form.duration_months)}
                onChange={(e) => setForm((f) => ({ ...f, duration_months: Number(e.target.value) }))}
                options={[3, 6, 12].map((m) => ({ value: String(m), label: `${m} bulan` }))}
              />
              <fieldset className="space-y-3 rounded-xl border border-border p-3">
                <legend className="px-1 text-sm font-semibold text-foreground">Klaim otomatis terpicu jika</legend>
                <Field label="Hujan dalam sehari lebih dari (mm)" type="number" inputMode="numeric" min={1} value={form.trigger_rain_mm} onChange={setNum("trigger_rain_mm")} />
                <Field label="Tidak hujan selama (hari)" type="number" inputMode="numeric" min={1} value={form.trigger_dry_days} onChange={setNum("trigger_dry_days")} />
                <Field label="Suhu lebih dari (°C)" type="number" inputMode="numeric" min={25} value={form.trigger_temp_max} onChange={setNum("trigger_temp_max")} />
              </fieldset>
              <div className="grid grid-cols-2 gap-3">
                <Button variant="secondary" onClick={() => setShowForm(false)} disabled={creating}>
                  Batal
                </Button>
                <Button type="submit" loading={creating}>
                  Buat polis
                </Button>
              </div>
            </form>
          </Card>
        )}

        {policies.some((p) => p.status === "active") && (
          <Notice tone="info" icon={CalendarClock} title="Dipantau otomatis setiap pagi">
            Setiap pagi sistem memeriksa cuaca kemarin di lokasi lahanmu. Kalau hujan, suhu, atau hari kering melewati batas polis,
            klaim dibuat otomatis tanpa perlu lapor.
          </Notice>
        )}

        <section aria-labelledby="policies-heading">
          <h2 id="policies-heading" className="mb-3 text-lg font-bold text-foreground">
            Polis saya
          </h2>
          {initialLoading ? (
            <Skeleton className="h-44 w-full rounded-2xl" />
          ) : policies.length === 0 ? (
            <Card className="flex flex-col items-center px-6 py-8 text-center">
              <span className="inline-flex size-14 items-center justify-center rounded-2xl bg-muted text-primary">
                <ShieldCheck className="size-7" aria-hidden="true" />
              </span>
              <p className="mt-3 text-base font-bold text-foreground">Belum ada polis</p>
              <p className="mt-1 text-[15px] text-muted-foreground">
                {eligibleFarms.length === 0
                  ? "Polis butuh lahan yang sudah punya lokasi. Tambahkan lahan dengan lokasi dulu."
                  : "Lindungi lahanmu dari banjir, kekeringan, dan suhu ekstrem."}
              </p>
              {eligibleFarms.length === 0 ? (
                <Link
                  href="/farms/add"
                  className="mt-5 inline-flex min-h-12 items-center gap-2 rounded-xl bg-primary px-5 font-semibold text-on-primary active:bg-primary-pressed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  <Plus className="size-5" aria-hidden="true" /> Tambah lahan
                </Link>
              ) : (
                !showForm && (
                  <Button className="mt-5" fullWidth={false} icon={Plus} onClick={() => setShowForm(true)}>
                    Buat polis
                  </Button>
                )
              )}
            </Card>
          ) : (
            <ul className="space-y-3">
              {policies.map((p) => {
                const farm = farms.find((f) => f.id === p.farm_id);
                return (
                  <li key={p.id}>
                    <Card>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-muted-foreground">{farm?.name ?? "Lahan"}</p>
                          <p className="text-2xl font-extrabold text-foreground">{formatRupiah(p.coverage_amount)}</p>
                          <p className="text-[15px] text-muted-foreground">Premi {formatRupiah(p.premium_amount)}/bulan</p>
                        </div>
                        <Badge tone={p.status === "active" ? "success" : "info"}>{p.status === "active" ? "Aktif" : p.status}</Badge>
                      </div>
                      <p className="mt-3 flex items-center gap-1.5 text-sm text-muted-foreground">
                        <CalendarDays className="size-4" aria-hidden="true" />
                        {formatDate(p.start_date)} – {formatDate(p.end_date)}
                      </p>
                      <dl className="mt-3 grid grid-cols-3 gap-2 border-t border-border pt-3 text-sm">
                        {[
                          { icon: CloudRain, label: "Hujan", value: `> ${p.trigger_rain_mm} mm` },
                          { icon: SunDim, label: "Kering", value: `${p.trigger_dry_days} hari` },
                          { icon: Thermometer, label: "Suhu", value: `> ${p.trigger_temp_max}°C` },
                        ].map(({ icon: Icon, label, value }) => (
                          <div key={label} className="flex flex-col">
                            <dt className="order-2 text-[13px] text-muted-foreground">{label}</dt>
                            <Icon className="order-1 size-5 text-primary" aria-hidden="true" />
                            <dd className="order-1 mt-1 font-bold text-foreground">{value}</dd>
                          </div>
                        ))}
                      </dl>
                    </Card>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {claims.length > 0 && (
          <section aria-labelledby="claims-heading">
            <h2 id="claims-heading" className="mb-3 text-lg font-bold text-foreground">
              Riwayat klaim
            </h2>
            <ul className="space-y-3">
              {claims.map((c) => {
                const meta = CLAIM_LABEL[c.trigger_type] ?? { label: c.trigger_type, unit: "" };
                return (
                  <li key={c.id}>
                    <Card className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-base font-bold text-foreground">{meta.label}</p>
                        <p className="text-[15px] text-muted-foreground">
                          Tercatat {c.trigger_value} {meta.unit}, batas {c.trigger_threshold} {meta.unit}
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">Cuaca tanggal {formatDate(c.weather_date)}</p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="text-base font-bold text-success-strong">{formatRupiah(c.claim_amount)}</p>
                        <p className="text-sm capitalize text-muted-foreground">{c.status === "approved" ? "Disetujui" : c.status}</p>
                      </div>
                    </Card>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </div>
    </PageShell>
  );
}
