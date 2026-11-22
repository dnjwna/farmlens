/**
 * Client-side image compression before upload.
 *
 * Phone photos are often 3-5 MB; rural connections are slow and the model
 * does not need more than ~1024px to see leaf symptoms. We downscale the
 * longest side to `maxDimension` and re-encode as JPEG.
 *
 * Modern browsers apply EXIF orientation when drawing an <img> to a canvas,
 * so portrait photos stay upright. Any failure (e.g. an undecodable HEIC)
 * falls back to the original file rather than blocking the upload.
 */

export interface CompressionResult {
  file: File;
  originalBytes: number;
  compressedBytes: number;
  compressed: boolean;
}

const SKIP_BELOW_BYTES = 300 * 1024;

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Gambar tidak bisa dibaca"));
    };
    img.src = url;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Gagal mengompres gambar"))),
      "image/jpeg",
      quality
    );
  });
}

export async function compressImage(
  file: File,
  maxDimension = 1024,
  quality = 0.8
): Promise<CompressionResult> {
  const unchanged: CompressionResult = {
    file,
    originalBytes: file.size,
    compressedBytes: file.size,
    compressed: false,
  };

  try {
    const img = await loadImage(file);
    const longest = Math.max(img.naturalWidth, img.naturalHeight);

    if (file.size <= SKIP_BELOW_BYTES && longest <= maxDimension) {
      return unchanged;
    }

    const scale = Math.min(1, maxDimension / longest);
    const width = Math.round(img.naturalWidth * scale);
    const height = Math.round(img.naturalHeight * scale);

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return unchanged;

    // JPEG has no alpha: paint white first so transparent PNGs don't turn black.
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);
    ctx.drawImage(img, 0, 0, width, height);

    const blob = await canvasToBlob(canvas, quality);
    if (blob.size >= file.size) return unchanged;

    const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
    return {
      file: new File([blob], name, { type: "image/jpeg", lastModified: Date.now() }),
      originalBytes: file.size,
      compressedBytes: blob.size,
      compressed: true,
    };
  } catch {
    return unchanged;
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
