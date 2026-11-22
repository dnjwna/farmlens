"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ScanSearch } from "lucide-react";
import api, { apiErrorDetail } from "@/lib/api";
import type { Diagnosis } from "@/types";
import { formatDateTime, isDisplayableImage } from "@/lib/format";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Card, Notice, Skeleton } from "@/components/ui";
import { DiagnosisResultView } from "@/components/DiagnosisResult";

export default function DiagnosisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [item, setItem] = useState<Diagnosis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Diagnosis>(`/diagnoses/${id}`)
      .then((r) => setItem(r.data))
      .catch((err) => setError(apiErrorDetail(err) || "Gagal memuat hasil pemeriksaan."));
  }, [id]);

  return (
    <PageShell busy={!item && !error}>
      <AppHeader title="Hasil pemeriksaan" backHref="/diagnosis/riwayat" />
      <div className="space-y-4 px-5 pt-5">
        {error && <Notice tone="danger">{error}</Notice>}

        {!item && !error && (
          <div className="space-y-3" role="status">
            <span className="sr-only">Memuat...</span>
            <Skeleton className="aspect-[4/3] w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-2xl" />
            <Skeleton className="h-24 w-full rounded-2xl" />
          </div>
        )}

        {item && (
          <>
            {isDisplayableImage(item.image_url) && (
              <Card className="p-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={item.image_url} alt={`Foto tanaman: ${item.disease_name ?? "hasil pemeriksaan"}`} className="aspect-[4/3] w-full rounded-xl bg-muted object-cover" />
              </Card>
            )}
            <DiagnosisResultView
              result={item}
              meta={[item.farm_name, formatDateTime(item.created_at)].filter(Boolean).join(" · ")}
            />
            <Link
              href="/diagnosis"
              className="flex min-h-13 items-center justify-center gap-2 rounded-xl border-2 border-primary bg-card px-5 font-semibold text-primary active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <ScanSearch className="size-5" aria-hidden="true" /> Periksa tanaman lagi
            </Link>
          </>
        )}
      </div>
    </PageShell>
  );
}
