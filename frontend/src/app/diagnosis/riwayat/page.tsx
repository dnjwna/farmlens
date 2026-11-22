"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ScanSearch } from "lucide-react";
import api from "@/lib/api";
import type { Diagnosis } from "@/types";
import { AppHeader, PageShell } from "@/components/AppShell";
import { Card, Notice, Skeleton } from "@/components/ui";
import { DiagnosisListItem } from "@/components/DiagnosisListItem";

const LIMIT = 100;

export default function DiagnosisHistoryPage() {
  const [items, setItems] = useState<Diagnosis[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api
      .get<Diagnosis[]>(`/diagnoses/?limit=${LIMIT}`)
      .then((r) => setItems(r.data))
      .catch(() => setFailed(true));
  }, []);

  return (
    <PageShell busy={items === null && !failed}>
      <AppHeader title="Riwayat pemeriksaan" backHref="/diagnosis" />
      <div className="space-y-3 px-5 pt-5">
        {failed && <Notice tone="danger">Gagal memuat riwayat. Periksa koneksi internet lalu coba lagi.</Notice>}

        {items === null && !failed && (
          <div className="space-y-3" role="status">
            <span className="sr-only">Memuat riwayat...</span>
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[5.5rem] w-full rounded-2xl" />
            ))}
          </div>
        )}

        {items && items.length === 0 && (
          <Card className="flex flex-col items-center px-6 py-8 text-center">
            <span className="inline-flex size-14 items-center justify-center rounded-2xl bg-muted text-primary">
              <ScanSearch className="size-7" aria-hidden="true" />
            </span>
            <p className="mt-3 text-base font-bold text-foreground">Belum ada pemeriksaan</p>
            <p className="mt-1 text-[15px] text-muted-foreground">Hasil setiap pemeriksaan tanaman akan tersimpan di sini.</p>
            <Link
              href="/diagnosis"
              className="mt-5 inline-flex min-h-12 items-center gap-2 rounded-xl bg-primary px-5 font-semibold text-on-primary active:bg-primary-pressed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <ScanSearch className="size-5" aria-hidden="true" /> Periksa tanaman
            </Link>
          </Card>
        )}

        {items && items.length > 0 && (
          <>
            <ul className="space-y-3">
              {items.map((d) => (
                <li key={d.id}>
                  <DiagnosisListItem item={d} />
                </li>
              ))}
            </ul>
            {items.length === LIMIT && (
              <p className="pb-2 text-center text-sm text-muted-foreground">Menampilkan {LIMIT} pemeriksaan terbaru.</p>
            )}
          </>
        )}
      </div>
    </PageShell>
  );
}
