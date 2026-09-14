import { Icon } from "./icons";
import { StatusPill } from "./ui/status-pill";

interface DocumentRowProps {
  name: string;
  type: string;
  status: string;
  date: string;
  size?: string;
  docId?: string;
  onDelete?: (id: string) => void;
}

export function DocumentRow({
  name,
  type,
  status,
  date,
  size,
  docId,
  onDelete,
}: DocumentRowProps) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-[#eeece7] py-3.5 last:border-0 md:grid-cols-[1.5fr_1fr_auto_auto_auto]">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f0f3f8] text-[#506078]">
          <Icon name="file" className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#283346]">{name}</p>
          <p className="mt-0.5 text-xs text-[#9097a3] md:hidden">
            {type} {size ? `· ${size}` : ""}
          </p>
        </div>
      </div>
      <div className="hidden md:block">
        <p className="text-sm text-[#697386]">{type}</p>
        {size && <p className="text-[11px] text-[#98a1b0]">{size}</p>}
      </div>
      <StatusPill tone={status.toLowerCase() === "expired" ? "danger" : "success"}>
        {status}
      </StatusPill>
      <p className="hidden w-20 text-right text-xs text-[#979eaa] md:block">{date}</p>
      {onDelete && docId && (
        <button
          onClick={() => onDelete(docId)}
          title="Delete document"
          className="grid h-7 w-7 place-items-center rounded-lg text-[#9aa1b0] transition hover:bg-[#fff0f1] hover:text-[#c93b4a]"
        >
          <Icon name="alert" className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
