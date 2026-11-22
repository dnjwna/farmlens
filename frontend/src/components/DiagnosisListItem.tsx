import Link from "next/link";
import { ChevronRight, Sprout } from "lucide-react";
import type { Diagnosis } from "@/types";
import { formatRelativeDay, isDisplayableImage } from "@/lib/format";
import { Badge } from "./ui";
import { isInvalidPhotoResult, severityToneOf } from "./DiagnosisResult";

export function DiagnosisListItem({ item }: { item: Diagnosis }) {
  const invalid = isInvalidPhotoResult(item);
  return (
    <Link
      href={`/diagnosis/${item.id}`}
      className="flex items-center gap-3 rounded-2xl border border-border bg-card p-3 transition-colors duration-150 active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      {isDisplayableImage(item.image_url) ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={item.image_url} alt="" loading="lazy" className="size-16 shrink-0 rounded-xl bg-muted object-cover" />
      ) : (
        <span className="inline-flex size-16 shrink-0 items-center justify-center rounded-xl bg-muted text-primary" aria-hidden="true">
          <Sprout className="size-7" />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-base font-bold text-foreground">{item.disease_name ?? "Tanpa hasil"}</span>
        <span className="block truncate text-sm text-muted-foreground">
          {[item.farm_name, formatRelativeDay(item.created_at)].filter(Boolean).join(" · ")}
        </span>
        {!invalid && item.severity && (
          <span className="mt-1.5 block">
            <Badge tone={severityToneOf(item.severity)}>{item.severity}</Badge>
          </span>
        )}
      </span>
      <ChevronRight className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
    </Link>
  );
}
