import { Icon } from "./icons";
import { StatusPill } from "./ui/status-pill";

export function DocumentRow({
  name,
  type,
  status,
  date,
  extractionMethod,
}: {
  name: string;
  type: string;
  status: string;
  date: string;
  extractionMethod?: string | null;
}) {
  const methodLabel =
    extractionMethod === "textract"
      ? "Textract"
      : extractionMethod === "local_ocr" || extractionMethod === "ocr"
      ? "OCR"
      : "Native text";

  const isOcr = methodLabel !== "Native text";

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-[#eeece7] py-3.5 last:border-0 md:grid-cols-[1.5fr_1fr_auto_auto]">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f0f3f8] text-[#506078]">
          <Icon name="file" className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#283346]">{name}</p>
          <div className="flex items-center gap-2 mt-0.5 md:hidden">
            <span className="text-xs text-[#9097a3]">{type}</span>
            <span className="rounded-md bg-[#edf2f7] px-1.5 py-0.5 text-[10px] font-medium text-[#4a5568]">
              {methodLabel}
            </span>
          </div>
        </div>
      </div>
      <div className="hidden items-center gap-2 md:flex">
        <span className="text-sm text-[#697386]">{type}</span>
        <span
          className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${
            isOcr
              ? "bg-[#e8f2ff] text-[#246bfd] border border-[#d0e2ff]"
              : "bg-[#f1f3f6] text-[#606b7d] border border-[#e2e6ec]"
          }`}
        >
          {methodLabel}
        </span>
      </div>
      <StatusPill tone="success">{status}</StatusPill>
      <p className="hidden w-16 text-right text-xs text-[#979eaa] md:block">{date}</p>
    </div>
  );
}
