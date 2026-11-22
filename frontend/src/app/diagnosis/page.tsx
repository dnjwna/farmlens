"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  AlarmClock,
  Camera,
  Eye,
  ImageIcon,
  Lightbulb,
  ListChecks,
  RotateCcw,
  ScanSearch,
  ShieldCheck,
  Sprout,
  TrendingDown,
  UserRound,
} from "lucide-react";
import api, { apiErrorDetail } from "@/lib/api";
import { compressImage, formatBytes } from "@/lib/image";
import { Farm, Diagnosis } from "@/types";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Badge, Button, Card, Notice, Section, SelectField, Skeleton, type Tone } from "@/components/ui";

const LOW_CONFIDENCE = 0.7;

const severityTone: Record<string, Tone> = { sehat: "success", ringan: "info", sedang: "warning", parah: "danger" };

function urgencyTone(u: string): Tone {
  const l = u.toLowerCase();
  if (l.includes("segera")) return "danger";
  if (l.includes("minggu")) return "warning";
  return "success";
}

function parseSteps(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [String(parsed)];
  } catch {
    return [raw];
  }
}

export default function DiagnosisPage() {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const [farms, setFarms] = useState<Farm[] | null>(null);
  const [selectedFarm, setSelectedFarm] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [sizeInfo, setSizeInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Diagnosis | null>(null);

  useEffect(() => {
    api
      .get<Farm[]>("/farms/")
      .then((r) => {
        setFarms(r.data);
        if (r.data.length > 0) setSelectedFarm(r.data[0].id);
      })
      .catch(() => {
        setFarms([]);
        toast.error("Gagal memuat daftar lahan.");
      });
  }, []);

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [result]);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setResult(null);
    setPreparing(true);
    try {
      const out = await compressImage(f);
      setFile(out.file);
      setPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(out.file);
      });
      setSizeInfo(
        out.compressed
          ? `Foto dikecilkan ${formatBytes(out.originalBytes)} → ${formatBytes(out.compressedBytes)}`
          : `Ukuran foto ${formatBytes(out.originalBytes)}`
      );
    } finally {
      setPreparing(false);
    }
  };

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setFile(null);
    setSizeInfo(null);
    setResult(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSubmit = async () => {
    if (!file || !selectedFarm) return;
    setLoading(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post<Diagnosis>(`/diagnoses/?farm_id=${selectedFarm}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
    } catch (err) {
      toast.error(apiErrorDetail(err) || "Gagal memeriksa foto. Coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  const confidence = Math.round((result?.confidence_score ?? 0) * 100);
  const steps = parseSteps(result?.action_steps ?? null);
  const isInvalidPhoto = result?.disease_name?.toLowerCase().includes("tidak valid");

  return (
    <PageShell busy={loading}>
      <AppHeader title="Periksa tanaman" backHref="/dashboard" />

      <div className="space-y-5 px-5 pt-5">
        {farms === null ? (
          <Skeleton className="h-20 w-full rounded-2xl" />
        ) : farms.length === 0 ? (
          <Notice tone="warning" title="Belum ada lahan">
            Tambahkan lahan dulu supaya AI tahu jenis tanamanmu.{" "}
            <Link href="/farms/add" className="font-bold underline underline-offset-4">
              Tambah lahan
            </Link>
          </Notice>
        ) : (
          <SelectField
            label="Lahan"
            value={selectedFarm}
            onChange={(e) => setSelectedFarm(e.target.value)}
            options={farms.map((f) => ({ value: f.id, label: `${f.name} — ${f.crop_type}` }))}
          />
        )}

        {/* Hidden inputs: one opens the camera directly, one opens the gallery */}
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={handleFile} />
        <input ref={galleryRef} type="file" accept="image/*" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={handleFile} />

        {preview ? (
          <Card className="p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={preview} alt="Foto tanaman yang akan diperiksa" className="aspect-[4/3] w-full rounded-xl object-cover" />
            <div className="mt-3 flex items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">{sizeInfo}</p>
              <Button variant="ghost" size="md" fullWidth={false} icon={RotateCcw} onClick={() => galleryRef.current?.click()} disabled={loading}>
                Ganti
              </Button>
            </div>
          </Card>
        ) : (
          <Card className="border-2 border-dashed border-input text-center">
            <span className="mx-auto inline-flex size-16 items-center justify-center rounded-2xl bg-muted text-primary">
              <Sprout className="size-8" aria-hidden="true" />
            </span>
            <p className="mt-3 text-base font-bold text-foreground">Foto bagian tanaman yang sakit</p>
            <ul className="mx-auto mt-2 max-w-xs space-y-1 text-left text-[15px] text-muted-foreground">
              <li>• Dekatkan kamera ke 1–2 daun yang bergejala</li>
              <li>• Foto di tempat terang, jangan melawan matahari</li>
              <li>• Pastikan gambar tidak buram</li>
            </ul>
          </Card>
        )}

        {!preview && (
          <div className="grid grid-cols-1 gap-3">
            <Button icon={Camera} onClick={() => cameraRef.current?.click()} loading={preparing} disabled={!farms?.length}>
              Ambil foto
            </Button>
            <Button variant="secondary" icon={ImageIcon} onClick={() => galleryRef.current?.click()} disabled={preparing || !farms?.length}>
              Pilih dari galeri
            </Button>
          </div>
        )}

        {preview && !result && (
          <Button icon={ScanSearch} onClick={handleSubmit} loading={loading} disabled={preparing || !selectedFarm}>
            {loading ? "AI sedang memeriksa..." : "Periksa sekarang"}
          </Button>
        )}

        {loading && (
          <div className="space-y-3" role="status" aria-live="polite">
            <p className="text-center text-[15px] text-muted-foreground">Mohon tunggu, AI sedang memeriksa fotomu.</p>
            <Skeleton className="h-32 w-full rounded-2xl" />
            <Skeleton className="h-24 w-full rounded-2xl" />
            <Skeleton className="h-36 w-full rounded-2xl" />
          </div>
        )}

        {result && (
          <div ref={resultRef} className="scroll-mt-20 space-y-4 pb-2" aria-live="polite">
            <Card>
              <p className="text-sm font-semibold text-muted-foreground">Hasil pemeriksaan</p>
              <h2 className="mt-1 text-2xl font-extrabold leading-tight text-foreground">{result.disease_name}</h2>

              {!isInvalidPhoto && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {result.severity && (
                    <Badge tone={severityTone[result.severity] ?? "info"}>
                      Keparahan: {result.severity}
                    </Badge>
                  )}
                  {result.urgency && (
                    <Badge tone={urgencyTone(result.urgency)} icon={AlarmClock}>
                      {result.urgency}
                    </Badge>
                  )}
                </div>
              )}

              <div className="mt-4 border-t border-border pt-4">
                <div className="flex items-baseline justify-between">
                  <span id="confidence-label" className="text-[15px] font-semibold text-foreground">
                    Keyakinan AI
                  </span>
                  <span className="text-lg font-bold text-foreground">{confidence}%</span>
                </div>
                <div
                  role="meter"
                  aria-labelledby="confidence-label"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={confidence}
                  className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-muted"
                >
                  <div
                    className={confidence >= LOW_CONFIDENCE * 100 ? "h-full rounded-full bg-primary" : "h-full rounded-full bg-caution"}
                    style={{ width: `${confidence}%` }}
                  />
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  Perkiraan AI dari foto, bukan hasil uji laboratorium.
                </p>
              </div>
            </Card>

            {!isInvalidPhoto && confidence < LOW_CONFIDENCE * 100 && (
              <Notice tone="warning" icon={UserRound} title="AI belum yakin">
                Sebaiknya tunjukkan tanaman ini ke penyuluh pertanian (PPL) sebelum membeli obat.
              </Notice>
            )}

            {result.warning_signs && result.warning_signs !== "-" && (
              <Section icon={Eye} title="Yang terlihat di foto">
                {result.warning_signs}
              </Section>
            )}

            {!isInvalidPhoto && result.cause_explanation && (
              <Section icon={Lightbulb} title="Kenapa ini terjadi" tone="warning">
                {result.cause_explanation}
              </Section>
            )}

            {!isInvalidPhoto && steps.length > 0 && (
              <Section icon={ListChecks} title="Yang perlu kamu lakukan" tone="success">
                <ol className="mt-1 space-y-3">
                  {steps.map((step, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-on-primary" aria-hidden="true">
                        {i + 1}
                      </span>
                      <span className="pt-0.5">{step}</span>
                    </li>
                  ))}
                </ol>
              </Section>
            )}

            {!isInvalidPhoto && result.estimated_yield_impact && result.estimated_yield_impact !== "-" && (
              <Section icon={TrendingDown} title="Kalau tidak ditangani" tone="danger">
                {result.estimated_yield_impact}
              </Section>
            )}

            {!isInvalidPhoto && result.recommendation && (
              <Section icon={ShieldCheck} title="Pencegahan musim depan" tone="info">
                {result.recommendation}
              </Section>
            )}

            <Button variant="secondary" icon={RotateCcw} onClick={reset}>
              Periksa foto lain
            </Button>
          </div>
        )}
      </div>
    </PageShell>
  );
}
