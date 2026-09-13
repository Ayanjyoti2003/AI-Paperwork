import { Icon } from "@/components/icons";
import type { Tone } from "@/lib/types";

const styles: Record<Tone, string> = {
  success: "bg-[var(--green-soft)] text-[var(--green)]",
  warning: "bg-[var(--amber-soft)] text-[var(--amber)]",
  danger: "bg-[var(--red-soft)] text-[var(--red)]",
  info: "bg-[var(--blue-soft)] text-[var(--blue)]",
  neutral: "bg-[#f0efeb] text-[#667085]",
};

export function StatusPill({ children, tone = "neutral", dot = false }: { children: React.ReactNode; tone?: Tone; dot?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${styles[tone]}`}>
      {dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : tone === "success" ? <Icon name="check" className="h-3.5 w-3.5" /> : null}
      {children}
    </span>
  );
}
