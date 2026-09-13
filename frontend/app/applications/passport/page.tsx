import Link from "next/link";
import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { StatusPill } from "@/components/ui/status-pill";
import { RequirementRow } from "@/components/requirement-row";
import { SectionTitle } from "@/components/section-title";
import { Icon } from "@/components/icons";
import { passportRequirements } from "@/lib/data";

export default function PassportApplicationPage() {
  return (
    <>
      <PageHeading eyebrow="Application" title="Passport application" description="Prepared from your documents and checked against the current workflow requirements." action={<button className="rounded-xl border border-[#d8d6d0] bg-white px-4 py-2.5 text-sm font-semibold text-[#566174]">More actions</button>} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_390px]">
        <div className="space-y-6">
          <Card className="p-5 md:p-6">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
              <div><StatusPill tone="warning" dot>Needs attention</StatusPill><h2 className="mt-3 text-xl font-bold tracking-[-0.03em]">Almost ready for final review</h2><p className="mt-1 text-sm text-[#748092]">4 of 6 requirements are fully verified.</p></div>
              <div className="sm:w-52"><div className="mb-2 flex items-center justify-between text-xs font-semibold text-[#727b8c]"><span>Readiness</span><span>83%</span></div><Progress value={83} /></div>
            </div>
          </Card>

          <Card className="p-5 md:p-6">
            <SectionTitle title="Requirements" description="Evidence is checked item by item so you can see exactly what still needs work." />
            <div className="mt-3">{passportRequirements.map((item) => <RequirementRow key={item.label} item={item} />)}</div>
          </Card>

          <Card className="overflow-hidden">
            <div className="border-b border-[#ebe9e4] px-5 py-5 md:px-6"><SectionTitle title="Evidence check" description="The values below came from your files, not from model memory." /></div>
            <div className="grid gap-px bg-[#ebe9e4] md:grid-cols-2">
              <div className="bg-[var(--paper)] p-5 md:p-6"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d95a1]">Full name</p><p className="mt-2 text-base font-bold">Arion Dutta</p><div className="mt-4 space-y-2 text-xs text-[#697386]"><p>aadhaar.pdf · Page 1</p><p>degree_certificate.pdf · Page 1</p></div><div className="mt-4"><StatusPill tone="success">Verified across 2 sources</StatusPill></div></div>
              <div className="bg-[var(--paper)] p-5 md:p-6"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d95a1]">Date of birth</p><p className="mt-2 text-base font-bold">12 March 2000</p><div className="mt-4 space-y-2 text-xs text-[#697386]"><p>aadhaar.pdf · Page 1</p><p>degree_certificate.pdf · Page 1</p></div><div className="mt-4"><StatusPill tone="success">Verified across 2 sources</StatusPill></div></div>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex items-start gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#fff0f1] text-[#c93b4a]"><Icon name="alert" className="h-5 w-5" /></div><div><p className="font-bold">One item is missing</p><p className="mt-1 text-sm leading-6 text-[#737d8e]">I could not find an accepted proof of birth in your document vault.</p></div></div>
            <button className="mt-4 w-full rounded-xl border border-[#e4c8cc] bg-[#fff9f9] px-4 py-2.5 text-sm font-semibold text-[#b73341]">Add birth proof</button>
          </Card>
          <Card className="p-5">
            <div className="flex items-start gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#fff6e8] text-[#a96716]"><Icon name="user" className="h-5 w-5" /></div><div><p className="font-bold">Your confirmation needed</p><p className="mt-1 text-sm leading-6 text-[#737d8e]">The signature appears usable, but this check is better confirmed by you.</p></div></div>
            <button className="mt-4 w-full rounded-xl border border-[#e5d2b1] bg-[#fffaf2] px-4 py-2.5 text-sm font-semibold text-[#946019]">Review signature</button>
          </Card>
          <Card className="p-5">
            <p className="hand-note text-sm font-semibold text-[#566174]">A small but important rule</p><p className="mt-3 text-sm leading-6 text-[#737d8e]">The package is prepared first. Submission remains a separate, explicit approval step.</p>
            <div className="mt-5 border-t border-[#eceae5] pt-5"><button disabled className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1f2d44] px-4 py-3 text-sm font-semibold text-white opacity-45"><Icon name="download" className="h-4 w-4" />Generate final package</button><p className="mt-2 text-center text-[11px] text-[#949ba7]">Available when required items are resolved</p></div>
          </Card>
        </div>
      </div>
    </>
  );
}
