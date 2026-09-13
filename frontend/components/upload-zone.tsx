"use client";

import { useState } from "react";
import { Icon } from "./icons";

export function UploadZone() {
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-[#cfd3dc] bg-[#fbfbf9] px-5 py-8 text-center transition hover:border-[#8aaaf0] hover:bg-[#f8fbff]">
      <input type="file" className="hidden" onChange={(event) => setFileName(event.target.files?.[0]?.name ?? null)} />
      <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]"><Icon name="upload" className="h-5 w-5" /></div>
      <p className="mt-3 text-sm font-semibold text-[#253044]">{fileName ? fileName : "Drop a document here or browse"}</p>
      <p className="mt-1 text-xs text-[#8c94a1]">PDF, JPG, PNG or DOCX · up to 20 MB</p>
    </label>
  );
}
