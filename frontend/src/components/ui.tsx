"use client";

import { useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { AlertTriangle, CheckCircle2, Eye, EyeOff, Info, Loader2, XCircle, type LucideIcon } from "lucide-react";

export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

/* ------------------------------------------------------------------ Button */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-primary text-on-primary active:bg-primary-pressed",
  secondary: "bg-card text-primary border-2 border-primary active:bg-muted",
  ghost: "text-primary active:bg-muted",
  danger: "bg-destructive text-on-primary active:bg-danger-strong",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "md" | "lg";
  loading?: boolean;
  icon?: LucideIcon;
  fullWidth?: boolean;
}

export function Button({
  variant = "primary",
  size = "lg",
  loading = false,
  icon: Icon,
  fullWidth = true,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl font-semibold transition-colors duration-150",
        "disabled:cursor-not-allowed disabled:opacity-55",
        focusRing,
        size === "lg" ? "min-h-13 px-5 text-base" : "min-h-12 px-4 text-[15px]",
        fullWidth && "w-full",
        buttonVariants[variant],
        className
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 className="size-5 motion-safe:animate-spin" aria-hidden="true" />
      ) : (
        Icon && <Icon className="size-5" aria-hidden="true" />
      )}
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ Card */

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-2xl border border-border bg-card p-4 shadow-[0_1px_2px_rgb(15_23_42/0.05)]", className)}>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ Form fields */

const inputBase =
  "block w-full min-h-12 rounded-xl border border-input bg-card px-4 text-base text-foreground placeholder:text-muted-foreground/80 " +
  "transition-colors duration-150 focus:border-primary focus:outline-2 focus:outline-offset-0 focus:outline-ring/30 " +
  "aria-[invalid=true]:border-destructive";

function FieldMessage({ id, error, hint }: { id: string; error?: string; hint?: string }) {
  if (!error && !hint) return null;
  return (
    <p id={id} className={cn("mt-1.5 text-sm", error ? "font-medium text-destructive" : "text-muted-foreground")}>
      {error || hint}
    </p>
  );
}

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

export function Field({ label, hint, error, id, className, ...rest }: FieldProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const msgId = `${inputId}-msg`;
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-foreground">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? msgId : undefined}
        className={inputBase}
        {...rest}
      />
      <FieldMessage id={msgId} error={error} hint={hint} />
    </div>
  );
}

export function PasswordField({ label, hint, error, id, className, ...rest }: FieldProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const msgId = `${inputId}-msg`;
  const [visible, setVisible] = useState(false);
  return (
    <div className={className}>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-foreground">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={visible ? "text" : "password"}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || hint ? msgId : undefined}
          className={cn(inputBase, "pr-14")}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Sembunyikan password" : "Tampilkan password"}
          aria-pressed={visible}
          className={cn(
            "absolute inset-y-0 right-0 inline-flex w-12 cursor-pointer items-center justify-center rounded-r-xl text-muted-foreground active:bg-muted",
            focusRing
          )}
        >
          {visible ? <EyeOff className="size-5" aria-hidden="true" /> : <Eye className="size-5" aria-hidden="true" />}
        </button>
      </div>
      <FieldMessage id={msgId} error={error} hint={hint} />
    </div>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export function SelectField({ label, hint, error, id, options, className, ...rest }: SelectFieldProps) {
  const autoId = useId();
  const selectId = id ?? autoId;
  const msgId = `${selectId}-msg`;
  return (
    <div className={className}>
      <label htmlFor={selectId} className="mb-1.5 block text-sm font-semibold text-foreground">
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? msgId : undefined}
        className={cn(inputBase, "cursor-pointer")}
        {...rest}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <FieldMessage id={msgId} error={error} hint={hint} />
    </div>
  );
}

/* ------------------------------------------------------------------ Status: Notice, Badge */

export type Tone = "info" | "success" | "warning" | "danger";

const toneStyles: Record<Tone, { box: string; text: string; icon: LucideIcon }> = {
  info: { box: "bg-info-soft border-info-border", text: "text-info-strong", icon: Info },
  success: { box: "bg-success-soft border-success-border", text: "text-success-strong", icon: CheckCircle2 },
  warning: { box: "bg-warning-soft border-warning-border", text: "text-warning-strong", icon: AlertTriangle },
  danger: { box: "bg-danger-soft border-danger-border", text: "text-danger-strong", icon: XCircle },
};

export function Notice({
  tone = "info",
  title,
  icon,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
}) {
  const s = toneStyles[tone];
  const Icon = icon ?? s.icon;
  return (
    <div className={cn("flex gap-3 rounded-2xl border p-4", s.box, s.text, className)}>
      <Icon className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 text-[15px] leading-relaxed">
        {title && <p className="font-bold">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
}

export function Badge({
  tone = "info",
  icon: Icon,
  children,
}: {
  tone?: Tone;
  icon?: LucideIcon;
  children: ReactNode;
}) {
  const s = toneStyles[tone];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold", s.box, s.text)}>
      {Icon && <Icon className="size-4" aria-hidden="true" />}
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ Confirm dialog */

/**
 * Native <dialog> modal: focus is trapped and returned by the browser, Esc closes it,
 * and the safe action ("Batal") receives initial focus.
 */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel = "Batal",
  loading = false,
  confirmDisabled = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  loading?: boolean;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        if (!loading) onCancel();
      }}
      onClick={(e) => {
        if (e.target === ref.current && !loading) onCancel();
      }}
      className="m-auto w-[calc(100%-2.5rem)] max-w-sm rounded-2xl bg-card p-0 text-foreground shadow-xl backdrop:bg-black/55"
    >
      <div className="p-5">
        <h2 id={titleId} className="text-lg font-bold">
          {title}
        </h2>
        <div className="mt-2 text-[15px] leading-relaxed text-muted-foreground">{children}</div>
        <div className="mt-6 grid grid-cols-2 gap-3">
          <Button variant="secondary" size="md" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant="danger" size="md" onClick={onConfirm} loading={loading} disabled={confirmDisabled}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}

/* ------------------------------------------------------------------ Skeleton */

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("rounded-xl bg-skeleton motion-safe:animate-pulse", className)} aria-hidden="true" />;
}

/* ------------------------------------------------------------------ Section with icon heading */

export function Section({
  icon: Icon,
  title,
  tone,
  children,
}: {
  icon: LucideIcon;
  title: string;
  tone?: Tone;
  children: ReactNode;
}) {
  const s = tone ? toneStyles[tone] : null;
  return (
    <section
      className={cn(
        "rounded-2xl border p-4",
        s ? cn(s.box, s.text) : "border-border bg-card text-foreground"
      )}
    >
      <h3 className="mb-2 flex items-center gap-2 text-base font-bold">
        <Icon className="size-5 shrink-0" aria-hidden="true" />
        {title}
      </h3>
      <div className="text-[15px] leading-relaxed">{children}</div>
    </section>
  );
}

export const formatRupiah = (n: number) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n);
