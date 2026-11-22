import type { ReactNode } from "react";
import { Sprout } from "lucide-react";

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <main className="flex min-h-dvh flex-col">
      <div className="bg-primary px-6 pb-12 pt-[calc(env(safe-area-inset-top)+3rem)] text-on-primary">
        <span className="inline-flex size-14 items-center justify-center rounded-2xl bg-on-primary text-primary">
          <Sprout className="size-8" aria-hidden="true" />
        </span>
        <p className="mt-4 text-2xl font-extrabold tracking-tight">FarmLens</p>
        <p className="mt-1 text-base text-on-primary-muted">Kenali penyakit tanaman, baca cuaca lahan, lindungi panen.</p>
      </div>
      <div className="-mt-6 flex-1 rounded-t-3xl bg-card px-6 pb-10 pt-8">
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}

export { isValidPhone, normalizePhone } from "@/lib/phone";
