import { Icon } from "./icons";
import { StatusPill } from "./ui/status-pill";

export function DocumentRow({ name, type, status, date }: { name: string; type: string; status: string; date: string }) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-[#eeece7] py-3.5 last:border-0 md:grid-cols-[1.5fr_1fr_auto_auto]">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f0f3f8] text-[#506078]"><Icon name="file" className="h-4 w-4" /></div>
        <div className="min-w-0"><p className="truncate text-sm font-semibold text-[#283346]">{name}</p><p className="mt-0.5 text-xs text-[#9097a3] md:hidden">{type}</p></div>
      </div>
      <p className="hidden text-sm text-[#697386] md:block">{type}</p>
      <StatusPill tone="success">{status}</StatusPill>
      <p className="hidden w-16 text-right text-xs text-[#979eaa] md:block">{date}</p>
    </div>
  );
}
