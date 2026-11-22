import { Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSun, Sun } from "lucide-react";

type Kind = "storm" | "rain" | "drizzle" | "fog" | "overcast" | "partly" | "clear";

/** Maps the Indonesian weather description from the backend to an icon kind. */
export function weatherKind(description: string): Kind {
  const d = description.toLowerCase();
  if (d.includes("badai")) return "storm";
  if (d.includes("hujan")) return "rain";
  if (d.includes("gerimis")) return "drizzle";
  if (d.includes("kabut")) return "fog";
  if (d.includes("mendung")) return "overcast";
  if (d.includes("berawan")) return "partly";
  if (d.includes("cerah")) return "clear";
  return "partly";
}

export function WeatherIcon({ description, className }: { description: string; className?: string }) {
  const props = { className, "aria-hidden": true as const };
  switch (weatherKind(description)) {
    case "storm":
      return <CloudLightning {...props} />;
    case "rain":
      return <CloudRain {...props} />;
    case "drizzle":
      return <CloudDrizzle {...props} />;
    case "fog":
      return <CloudFog {...props} />;
    case "overcast":
      return <Cloud {...props} />;
    case "clear":
      return <Sun {...props} />;
    default:
      return <CloudSun {...props} />;
  }
}
