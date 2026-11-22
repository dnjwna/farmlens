"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sprout } from "lucide-react";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("farmlens_token");
    router.replace(token ? "/dashboard" : "/login");
  }, [router]);

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-3" aria-busy="true">
      <span className="inline-flex size-16 items-center justify-center rounded-2xl bg-primary text-on-primary">
        <Sprout className="size-9" aria-hidden="true" />
      </span>
      <p className="text-lg font-bold text-primary">FarmLens</p>
    </main>
  );
}
