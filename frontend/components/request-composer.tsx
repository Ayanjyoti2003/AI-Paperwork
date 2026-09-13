"use client";

import { useState } from "react";
import { Icon } from "./icons";

const suggestions = ["Apply for a passport", "Prepare a scholarship application", "Check my admission documents"];

export function RequestComposer() {
  const [value, setValue] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <button key={suggestion} onClick={() => { setValue(suggestion); setSubmitted(false); }} className="rounded-full border border-[#dddcd6] bg-white px-3 py-1.5 text-xs font-medium text-[#667085] transition hover:border-[#b9c9ea] hover:text-[#245fce]">
            {suggestion}
          </button>
        ))}
      </div>
      <div className="mt-5 rounded-2xl border border-[#dfddd7] bg-white p-2 shadow-sm focus-within:border-[#9ebaf3] focus-within:ring-4 focus-within:ring-[#edf4ff]">
        <textarea value={value} onChange={(event) => { setValue(event.target.value); setSubmitted(false); }} rows={4} placeholder="Tell me what you need to get done…" className="w-full resize-none bg-transparent px-3 py-2 text-[15px] leading-6 outline-none placeholder:text-[#a2a8b2]" />
        <div className="flex items-center justify-between gap-3 border-t border-[#efede8] px-2 pt-2">
          <button className="flex items-center gap-2 rounded-lg px-2 py-2 text-xs font-semibold text-[#768092] hover:bg-[#f5f4f0]"><Icon name="upload" className="h-4 w-4" />Attach files</button>
          <button disabled={!value.trim()} onClick={() => setSubmitted(true)} className="flex items-center gap-2 rounded-xl bg-[#246bfd] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f61e7] disabled:cursor-not-allowed disabled:opacity-40">
            Start request <Icon name="send" className="h-4 w-4" />
          </button>
        </div>
      </div>
      {submitted ? (
        <div className="mt-5 rounded-2xl border border-[#d6e5dd] bg-[#f2faf6] p-4 text-sm leading-6 text-[#43685a]">
          <div className="flex gap-3"><div className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-[#16815d]"><Icon name="check" className="h-4 w-4" /></div><p>I’ve got it. Next I’d identify the exact requirements, search your document vault, and show you what is ready, missing, or inconsistent before preparing anything for approval.</p></div>
        </div>
      ) : null}
    </div>
  );
}
