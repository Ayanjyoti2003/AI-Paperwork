export function Progress({ value, className = "" }: { value: number; className?: string }) {
  return (
    <div className={`h-2 overflow-hidden rounded-full bg-[#ecebe6] ${className}`}>
      <div className="h-full rounded-full bg-[#246bfd] transition-[width] duration-500" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}
