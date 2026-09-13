import { Icon } from "./icons";
import type { Requirement } from "@/lib/types";

const tone = {
  verified: { shell: "bg-[#ebf8f2] text-[#16815d]", icon: "check" as const, button: "border-[#d7e8df] text-[#287158]" },
  missing: { shell: "bg-[#fff0f1] text-[#c93b4a]", icon: "alert" as const, button: "border-[#efcbd0] text-[#b62f3e]" },
  review: { shell: "bg-[#fff6e8] text-[#b86f12]", icon: "alert" as const, button: "border-[#ead5b5] text-[#9e6215]" },
};

export function RequirementRow({ item }: { item: Requirement }) {
  const style = tone[item.status];
  return (
    <div className="flex items-center gap-3 border-b border-[#eeece7] py-3.5 last:border-0">
      <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${style.shell}`}><Icon name={style.icon} className="h-4 w-4" /></div>
      <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-[#253044]">{item.label}</p><p className="mt-0.5 truncate text-xs text-[#89919e]">{item.detail}</p></div>
      <button className={`rounded-lg border bg-white px-3 py-1.5 text-xs font-semibold transition hover:bg-[#fafafa] ${style.button}`}>{item.action}</button>
    </div>
  );
}
