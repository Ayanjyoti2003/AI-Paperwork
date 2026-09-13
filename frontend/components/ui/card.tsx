import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-[22px] border border-[#e6e4de] bg-[var(--paper)] soft-shadow ${className}`}>{children}</section>;
}
