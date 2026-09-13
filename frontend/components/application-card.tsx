import Link from "next/link";
import { Icon } from "./icons";
import { Progress } from "./ui/progress";

export function ApplicationCard({ title, status, progress, updated, href }: { title: string; status: string; progress: number; updated: string; href: string }) {
  return (
    <Link href={href} className="group block rounded-2xl border border-[#e6e4de] bg-white p-5 transition hover:-translate-y-0.5 hover:border-[#cdd9f2] hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]"><Icon name="file" className="h-5 w-5" /></div>
        <Icon name="arrow" className="h-4 w-4 text-[#a5acb8] transition group-hover:translate-x-0.5 group-hover:text-[#246bfd]" />
      </div>
      <h3 className="mt-5 font-bold tracking-[-0.02em] text-[#263043]">{title}</h3>
      <p className="mt-1 text-sm text-[#737c8e]">{status}</p>
      <div className="mt-5 flex items-center justify-between text-xs text-[#87909f]"><span>{progress}% complete</span><span>{updated}</span></div>
      <Progress value={progress} className="mt-2.5" />
    </Link>
  );
}
