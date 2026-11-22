"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  Camera,
  ChevronRight,
  CloudRain,
  Droplets,
  Lightbulb,
  LogOut,
  MapPin,
  MapPinOff,
  Plus,
  Sprout,
  Trash2,
  Wind,
} from "lucide-react";
import { getMe, logout } from "@/lib/auth";
import api, { apiErrorDetail } from "@/lib/api";
import { Farmer, Farm, WeatherData } from "@/types";
import { PageShell } from "@/components/AppShell";
import { Badge, Card, ConfirmDialog, Notice, Skeleton } from "@/components/ui";
import { WeatherIcon } from "@/components/WeatherIcon";

const hasLocation = (f: Farm) => f.latitude !== null && f.longitude !== null;

function greeting() {
  const h = new Date().getHours();
  if (h < 11) return "Selamat pagi";
  if (h < 15) return "Selamat siang";
  if (h < 18) return "Selamat sore";
  return "Selamat malam";
}

export default function DashboardPage() {
  const [farmer, setFarmer] = useState<Farmer | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [weatherFarmId, setWeatherFarmId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingDelete, setPendingDelete] = useState<Farm | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadWeatherFor = async (list: Farm[]) => {
    const target = list.find(hasLocation);
    setWeatherFarmId(target?.id ?? null);
    if (!target) {
      setWeather(null);
      return;
    }
    const w = await api.get<WeatherData>(`/weather/farm/${target.id}`);
    setWeather(w.data);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const farm = pendingDelete;
    setDeleting(true);
    try {
      await api.delete(`/farms/${farm.id}`);
      const remaining = farms.filter((f) => f.id !== farm.id);
      setFarms(remaining);
      setPendingDelete(null);
      toast.success(`Lahan "${farm.name}" dihapus`);
      if (farm.id === weatherFarmId) {
        loadWeatherFor(remaining).catch(() => setWeather(null));
      }
    } catch (err) {
      toast.error(apiErrorDetail(err) || "Gagal menghapus lahan. Coba lagi.");
      setPendingDelete(null);
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [farmerData, farmsData] = await Promise.all([
          getMe(),
          api.get<Farm[]>("/farms/").then((r) => r.data),
        ]);
        if (!active) return;
        setFarmer(farmerData);
        setFarms(farmsData);

        const withLocation = farmsData.find(hasLocation);
        if (withLocation) {
          const w = await api.get<WeatherData>(`/weather/farm/${withLocation.id}`);
          if (active) {
            setWeather(w.data);
            setWeatherFarmId(withLocation.id);
          }
        }
      } catch {
        if (active) toast.error("Gagal memuat data. Periksa koneksi internet.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <PageShell busy>
        <div className="bg-primary px-5 pb-8 pt-[calc(env(safe-area-inset-top)+2rem)]">
          <Skeleton className="h-4 w-28 bg-white/25" />
          <Skeleton className="mt-3 h-7 w-48 bg-white/25" />
          <Skeleton className="mt-6 h-28 w-full rounded-2xl bg-white/15" />
        </div>
        <div className="space-y-4 px-5 pt-6">
          <Skeleton className="h-24 w-full rounded-2xl" />
          <Skeleton className="h-20 w-full rounded-2xl" />
          <Skeleton className="h-20 w-full rounded-2xl" />
        </div>
        <p className="sr-only" role="status">Memuat data...</p>
      </PageShell>
    );
  }

  const location = [farmer?.city, farmer?.province].filter(Boolean).join(", ");
  const farmsWithoutLocation = farms.filter((f) => !hasLocation(f));

  return (
    <PageShell>
      {/* Header */}
      <header className="rounded-b-3xl bg-primary px-5 pb-6 pt-[calc(env(safe-area-inset-top)+1.75rem)] text-on-primary">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[15px] text-on-primary-muted">{greeting()},</p>
            <h1 className="truncate text-2xl font-extrabold tracking-tight">{farmer?.full_name}</h1>
            {location && (
              <p className="mt-1 flex items-center gap-1 text-sm text-on-primary-muted">
                <MapPin className="size-4" aria-hidden="true" />
                {location}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={logout}
            aria-label="Keluar dari akun"
            className="inline-flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full bg-white/15 transition-colors duration-150 active:bg-white/25 focus-visible:outline-2 focus-visible:outline-on-primary"
          >
            <LogOut className="size-5" aria-hidden="true" />
          </button>
        </div>

        {weather && (
          <Link
            href="/weather"
            className="mt-5 block rounded-2xl bg-primary-pressed p-4 transition-colors duration-150 active:bg-primary-deep focus-visible:outline-2 focus-visible:outline-on-primary"
          >
            <div className="flex items-center justify-between text-sm text-on-primary-muted">
              <span className="truncate">Cuaca di {weather.farm_name}</span>
              <span className="flex items-center gap-0.5 font-semibold">
                7 hari <ChevronRight className="size-4" aria-hidden="true" />
              </span>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <WeatherIcon description={weather.current.weather} className="size-11" />
              <div>
                <p className="text-4xl font-extrabold leading-none">{Math.round(weather.current.temperature)}°C</p>
                <p className="mt-1 text-[15px] font-medium">{weather.current.weather}</p>
              </div>
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-sm">
              <div className="flex items-center gap-1.5">
                <Droplets className="size-4 shrink-0" aria-hidden="true" />
                <dt className="sr-only">Kelembapan</dt>
                <dd>{weather.current.humidity}%</dd>
              </div>
              <div className="flex items-center gap-1.5">
                <Wind className="size-4 shrink-0" aria-hidden="true" />
                <dt className="sr-only">Angin</dt>
                <dd>{weather.current.wind_speed} km/j</dd>
              </div>
              <div className="flex items-center gap-1.5">
                <CloudRain className="size-4 shrink-0" aria-hidden="true" />
                <dt className="sr-only">Hujan</dt>
                <dd>{weather.current.precipitation} mm</dd>
              </div>
            </dl>
          </Link>
        )}
      </header>

      <div className="space-y-6 px-5 pt-6">
        {/* Primary action */}
        <Link
          href="/diagnosis"
          className="flex items-center gap-4 rounded-2xl bg-card p-4 shadow-[0_1px_2px_rgb(15_23_42/0.05)] ring-2 ring-primary transition-colors duration-150 active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          <span className="inline-flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary text-on-primary">
            <Camera className="size-7" aria-hidden="true" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-lg font-bold text-foreground">Periksa tanaman</span>
            <span className="block text-[15px] text-muted-foreground">Foto daun yang sakit, AI bantu kenali masalahnya.</span>
          </span>
          <ChevronRight className="size-6 shrink-0 text-primary" aria-hidden="true" />
        </Link>

        {weather && (
          <Notice tone="info" title="Saran hari ini" icon={Lightbulb}>
            {weather.farming_advice}
          </Notice>
        )}

        {farms.length > 0 && farmsWithoutLocation.length === farms.length && (
          <Notice tone="warning" icon={MapPinOff} title="Lokasi lahan belum diisi">
            Cuaca dan saran harian butuh lokasi lahan. Tambahkan lahan dengan lokasi saat kamu berada di sawah/kebun.
          </Notice>
        )}

        {/* Farms */}
        <section aria-labelledby="farms-heading">
          <div className="mb-3 flex items-center justify-between">
            <h2 id="farms-heading" className="text-lg font-bold text-foreground">
              Lahan saya
            </h2>
            <Link
              href="/farms/add"
              className="inline-flex min-h-12 items-center gap-1 rounded-xl px-3 text-[15px] font-bold text-primary active:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            >
              <Plus className="size-5" aria-hidden="true" /> Tambah
            </Link>
          </div>

          {farms.length === 0 ? (
            <Card className="flex flex-col items-center px-6 py-8 text-center">
              <span className="inline-flex size-14 items-center justify-center rounded-2xl bg-muted text-primary">
                <Sprout className="size-7" aria-hidden="true" />
              </span>
              <p className="mt-3 text-base font-bold text-foreground">Belum ada lahan</p>
              <p className="mt-1 text-[15px] text-muted-foreground">Tambahkan lahan dulu supaya bisa memeriksa tanaman dan melihat cuaca.</p>
              <Link
                href="/farms/add"
                className="mt-5 inline-flex min-h-12 items-center gap-2 rounded-xl bg-primary px-5 font-semibold text-on-primary active:bg-primary-pressed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <Plus className="size-5" aria-hidden="true" /> Tambah lahan
              </Link>
            </Card>
          ) : (
            <ul className="space-y-3">
              {farms.map((farm) => (
                <li key={farm.id}>
                  <Card className="flex items-center gap-3 py-3 pr-2">
                    <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-xl bg-muted text-primary">
                      <Sprout className="size-6" aria-hidden="true" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-base font-bold text-foreground">{farm.name}</p>
                      <p className="text-[15px] capitalize text-muted-foreground">
                        {farm.crop_type} · {farm.area_hectares} ha
                      </p>
                      {!hasLocation(farm) && (
                        <div className="mt-1.5">
                          <Badge tone="warning" icon={MapPinOff}>
                            Tanpa lokasi
                          </Badge>
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => setPendingDelete(farm)}
                      aria-label={`Hapus lahan ${farm.name}`}
                      className="inline-flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground transition-colors duration-150 active:bg-danger-soft active:text-destructive focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <Trash2 className="size-5" aria-hidden="true" />
                    </button>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title={`Hapus lahan "${pendingDelete?.name ?? ""}"?`}
        confirmLabel="Hapus"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      >
        Lahan akan hilang dari daftar dan tidak bisa dipilih lagi. Riwayat pemeriksaan dan klaim asuransinya tetap disimpan.
        Lahan yang masih punya polis aktif tidak bisa dihapus.
      </ConfirmDialog>
    </PageShell>
  );
}
