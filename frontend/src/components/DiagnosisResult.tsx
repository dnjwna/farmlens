"use client";

import { AlarmClock, Eye, Lightbulb, ListChecks, ShieldCheck, TrendingDown, UserRound } from "lucide-react";
import type { Diagnosis } from "@/types";
import { Badge, Card, Notice, Section, type Tone } from "./ui";

export const LOW_CONFIDENCE = 0.7;

const severityTone: Record<string, Tone> = { sehat: "success", ringan: "info", sedang: "warning", parah: "danger" };

export function severityToneOf(severity: string | null | undefined): Tone {
  return (severity && severityTone[severity]) || "info";
}

export function urgencyTone(u: string): Tone {
  const l = u.toLowerCase();
  if (l.includes("segera")) return "danger";
  if (l.includes("minggu")) return "warning";
  return "success";
}

export function parseSteps(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [String(parsed)];
  } catch {
    return [raw];
  }
}

export const isInvalidPhotoResult = (d: Diagnosis) => !!d.disease_name?.toLowerCase().includes("tidak valid");

/** Full explainable diagnosis result, shared by the new-check flow and the history detail page. */
export function DiagnosisResultView({ result, meta }: { result: Diagnosis; meta?: string }) {
  const confidence = Math.round((result.confidence_score ?? 0) * 100);
  const steps = parseSteps(result.action_steps);
  const invalid = isInvalidPhotoResult(result);

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-sm font-semibold text-muted-foreground">{meta ?? "Hasil pemeriksaan"}</p>
        <h2 className="mt-1 text-2xl font-extrabold leading-tight text-foreground">{result.disease_name}</h2>

        {!invalid && (
          <div className="mt-3 flex flex-wrap gap-2">
            {result.severity && <Badge tone={severityToneOf(result.severity)}>Keparahan: {result.severity}</Badge>}
            {result.urgency && (
              <Badge tone={urgencyTone(result.urgency)} icon={AlarmClock}>
                {result.urgency}
              </Badge>
            )}
          </div>
        )}

        <div className="mt-4 border-t border-border pt-4">
          <div className="flex items-baseline justify-between">
            <span id={`conf-${result.id}`} className="text-[15px] font-semibold text-foreground">
              Keyakinan AI
            </span>
            <span className="text-lg font-bold text-foreground">{confidence}%</span>
          </div>
          <div
            role="meter"
            aria-labelledby={`conf-${result.id}`}
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
          <p className="mt-2 text-sm text-muted-foreground">Perkiraan AI dari foto, bukan hasil uji laboratorium.</p>
        </div>
      </Card>

      {!invalid && confidence < LOW_CONFIDENCE * 100 && (
        <Notice tone="warning" icon={UserRound} title="AI belum yakin">
          Sebaiknya tunjukkan tanaman ini ke penyuluh pertanian (PPL) sebelum membeli obat.
        </Notice>
      )}

      {result.warning_signs && result.warning_signs !== "-" && (
        <Section icon={Eye} title="Yang terlihat di foto">
          {result.warning_signs}
        </Section>
      )}

      {!invalid && result.cause_explanation && (
        <Section icon={Lightbulb} title="Kenapa ini terjadi" tone="warning">
          {result.cause_explanation}
        </Section>
      )}

      {!invalid && steps.length > 0 && (
        <Section icon={ListChecks} title="Yang perlu kamu lakukan" tone="success">
          <ol className="mt-1 space-y-3">
            {steps.map((step, i) => (
              <li key={i} className="flex gap-3">
                <span
                  className="inline-flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-on-primary"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <span className="pt-0.5">{step}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {!invalid && result.estimated_yield_impact && result.estimated_yield_impact !== "-" && (
        <Section icon={TrendingDown} title="Kalau tidak ditangani" tone="danger">
          {result.estimated_yield_impact}
        </Section>
      )}

      {!invalid && result.recommendation && (
        <Section icon={ShieldCheck} title="Pencegahan musim depan" tone="info">
          {result.recommendation}
        </Section>
      )}
    </div>
  );
}
