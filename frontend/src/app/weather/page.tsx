"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CloudRain, Droplets, Lightbulb, MapPinOff, Wind } from "lucide-react";
import api, { apiErrorDetail } from "@/lib/api";
import { Farm, WeatherData } from "@/types";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Card, Notice, SelectField, Skeleton } from "@/components/ui";
import { WeatherIcon } from "@/components/WeatherIcon";

function dayLabel(date: string, index: number) {
  if (index === 0) return "Hari ini";
  if (index === 1) return "Besok";
  return new Date(`${date}T00:00:00`).toLocaleDateString("id-ID", { weekday: "long" });
}

function dateLabel(date: string) {
  return new Date(`${date}T00:00:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

export default function WeatherPage() {
  const [farms, setFarms] = useState<Farm[] | null>(null);
  const [selectedFarm, setSelectedFarm] = useState("");
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = useCallback(async (farmId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<WeatherData>(`/weather/farm/${farmId}`);
      setWeather(res.data);
    } catch (err) {
      setWeather(null);
      setError(apiErrorDetail(err) || "Gagal memuat cuaca. Periksa koneksi internet.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api
      .get<Farm[]>("/farms/")
      .then((r) => {
        setFarms(r.data);
        const first = r.data.find((f) => f.latitude !== null && f.longitude !== null) ?? r.data[0];
        if (first) {
          setSelectedFarm(first.id);
          fetchWeather(first.id);
        }
      })
      .catch(() => {
        setFarms([]);
        setError("Gagal memuat daftar lahan.");
      });
  }, [fetchWeather]);

  return (
    <PageShell busy={loading}>
      <AppHeader title="Cuaca lahan" backHref="/dashboard" />

      <div className="space-y-5 px-5 pt-5">
        {farms && farms.length > 1 && (
          <SelectField
            label="Lahan"
            value={selectedFarm}
            onChange={(e) => {
              setSelectedFarm(e.target.value);
              fetchWeather(e.target.value);
            }}
            options={farms.map((f) => ({ value: f.id, label: f.name }))}
          />
        )}

        {farms && farms.length === 0 && (
          <Notice tone="warning" title="Belum ada lahan">
            Tambahkan lahan dengan lokasi untuk melihat cuacanya.{" "}
            <Link href="/farms/add" className="font-bold underline underline-offset-4">
              Tambah lahan
            </Link>
          </Notice>
        )}

        {error && (
          <Notice tone="warning" icon={MapPinOff}>
            {error}
          </Notice>
        )}

        {(loading || farms === null) && (
          <div className="space-y-4" role="status">
            <span className="sr-only">Memuat cuaca...</span>
            <Skeleton className="h-44 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-80 w-full rounded-2xl" />
          </div>
        )}

        {weather && !loading && (
          <>
            <section className="rounded-2xl bg-primary p-5 text-on-primary" aria-label="Cuaca sekarang">
              <p className="text-sm text-on-primary-muted">Sekarang di {weather.farm_name}</p>
              <div className="mt-3 flex items-center gap-4">
                <WeatherIcon description={weather.current.weather} className="size-14" />
                <div>
                  <p className="text-5xl font-extrabold leading-none">{Math.round(weather.current.temperature)}°C</p>
                  <p className="mt-1 text-base font-semibold">{weather.current.weather}</p>
                </div>
              </div>
              <dl className="mt-5 grid grid-cols-3 gap-2">
                {[
                  { icon: Droplets, label: "Kelembapan", value: `${weather.current.humidity}%` },
                  { icon: Wind, label: "Angin", value: `${weather.current.wind_speed} km/j` },
                  { icon: CloudRain, label: "Hujan", value: `${weather.current.precipitation} mm` },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="flex flex-col rounded-xl bg-primary-pressed p-3">
                    <dt className="order-3 text-[13px] text-on-primary-muted">{label}</dt>
                    <Icon className="order-1 size-5" aria-hidden="true" />
                    <dd className="order-2 mt-1 text-base font-bold">{value}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <Notice tone="info" icon={Lightbulb} title="Saran untuk minggu ini">
              {weather.farming_advice}
            </Notice>

            <Card className="p-0">
              <h2 className="px-4 pb-2 pt-4 text-lg font-bold text-foreground">Prakiraan 7 hari</h2>
              <ul>
                {weather.forecast_7_days.map((day, i) => (
                  <li key={day.date} className="flex min-h-16 items-center gap-3 border-t border-border px-4 py-3">
                    <div className="w-24 shrink-0">
                      <p className="text-[15px] font-bold capitalize text-foreground">{dayLabel(day.date, i)}</p>
                      <p className="text-sm text-muted-foreground">{dateLabel(day.date)}</p>
                    </div>
                    <WeatherIcon description={day.weather} className="size-7 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[15px] text-foreground">{day.weather}</p>
                      {day.rain_mm > 0 && (
                        <p className="flex items-center gap-1 text-sm text-info-strong">
                          <CloudRain className="size-4" aria-hidden="true" />
                          {day.rain_mm} mm
                        </p>
                      )}
                    </div>
                    <p className="shrink-0 text-right">
                      <span className="text-base font-bold text-foreground">{Math.round(day.temp_max)}°</span>
                      <span className="sr-only"> tertinggi, </span>
                      <span className="ml-1.5 text-[15px] text-muted-foreground">{Math.round(day.temp_min)}°</span>
                      <span className="sr-only"> terendah</span>
                    </p>
                  </li>
                ))}
              </ul>
            </Card>

            <p className="pb-2 text-center text-sm text-muted-foreground">Data cuaca: Open-Meteo</p>
          </>
        )}
      </div>
    </PageShell>
  );
}
