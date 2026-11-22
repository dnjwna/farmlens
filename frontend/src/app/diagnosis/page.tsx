"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Camera, ChevronRight, History, ImageIcon, RotateCcw, ScanSearch, Sprout } from "lucide-react";
import api, { apiErrorDetail } from "@/lib/api";
import { compressImage, formatBytes } from "@/lib/image";
import { Farm, Diagnosis } from "@/types";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Button, Card, Notice, SelectField, Skeleton } from "@/components/ui";
import { DiagnosisResultView } from "@/components/DiagnosisResult";
import { DiagnosisListItem } from "@/components/DiagnosisListItem";

const RECENT_COUNT = 3;

export default function DiagnosisPage() {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const [farms, setFarms] = useState<Farm[] | null>(null);
  const [recent, setRecent] = useState<Diagnosis[] | null>(null);
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
    api
      .get<Diagnosis[]>(`/diagnoses/?limit=${RECENT_COUNT + 1}`)
      .then((r) => setRecent(r.data))
      .catch(() => setRecent([]));
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
      setRecent((prev) => (prev ? [res.data, ...prev] : [res.data]));
    } catch (err) {
      toast.error(apiErrorDetail(err) || "Gagal memeriksa foto. Coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  const showRecent = !preview && !result && !loading;

  return (
    <PageShell busy={loading}>
      <AppHeader
        title="Periksa tanaman"
        backHref="/dashboard"
        action={
          <Link
            href="/diagnosis/riwayat"
            className="inline-flex min-h-12 items-center gap-1.5 rounded-xl px-3 text-[15px] font-bold text-primary active:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            <History className="size-5" aria-hidden="true" />
            Riwayat
          </Link>
        }
      />

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
            <DiagnosisResultView result={result} />
            <p className="text-center text-sm text-muted-foreground">Hasil ini tersimpan di Riwayat.</p>
            <Button variant="secondary" icon={RotateCcw} onClick={reset}>
              Periksa foto lain
            </Button>
          </div>
        )}

        {showRecent && recent && recent.length > 0 && (
          <section aria-labelledby="recent-heading" className="pt-2">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="recent-heading" className="text-lg font-bold text-foreground">
                Pemeriksaan terakhir
              </h2>
              {recent.length > RECENT_COUNT && (
                <Link
                  href="/diagnosis/riwayat"
                  className="inline-flex min-h-12 items-center gap-0.5 rounded-xl px-3 text-[15px] font-bold text-primary active:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
                >
                  Lihat semua <ChevronRight className="size-5" aria-hidden="true" />
                </Link>
              )}
            </div>
            <ul className="space-y-3">
              {recent.slice(0, RECENT_COUNT).map((d) => (
                <li key={d.id}>
                  <DiagnosisListItem item={d} />
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </PageShell>
  );
}
