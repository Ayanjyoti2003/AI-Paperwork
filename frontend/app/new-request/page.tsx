import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { RequestComposer } from "@/components/request-composer";
import { Icon } from "@/components/icons";

const steps = [
  ["1", "Understand your goal", "I’ll work out the exact administrative process and requirements."],
  ["2", "Check your documents", "Relevant files are searched and supporting facts are extracted with sources."],
  ["3", "Find gaps and conflicts", "Missing evidence, outdated files and mismatched details are surfaced clearly."],
  ["4", "Prepare for your approval", "You get a checklist and prepared package. Nothing consequential happens without you."],
];

export default function NewRequestPage() {
  return (
    <>
      <PageHeading eyebrow="New request" title="What are you trying to get done?" description="Describe the outcome in your own words. You do not need to know the form name or exact requirements." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_420px]">
        <Card className="p-5 md:p-7">
          <div className="mb-6 flex items-start gap-3 rounded-2xl bg-[#f6f7f9] p-4">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-[#246bfd] shadow-sm"><Icon name="spark" className="h-4.5 w-4.5" /></div>
            <div><p className="text-sm font-semibold">Start with the goal, not the paperwork.</p><p className="mt-1 text-sm leading-6 text-[#768092]">For example: “I want to apply for a passport” or “Help me prepare my scholarship application.”</p></div>
          </div>
          <RequestComposer />
        </Card>
        <Card className="p-5 md:p-6">
          <h2 className="text-base font-bold">What happens next</h2>
          <div className="mt-5 space-y-5">
            {steps.map(([number, title, copy], index) => (
              <div key={number} className="relative flex gap-3.5">
                {index < steps.length - 1 ? <div className="absolute left-[15px] top-8 h-[calc(100%+4px)] w-px bg-[#e3e2dd]" /> : null}
                <div className="z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-[#d7dce8] bg-white text-xs font-bold text-[#52627c]">{number}</div>
                <div className="pb-1"><p className="text-sm font-semibold text-[#283346]">{title}</p><p className="mt-1 text-xs leading-5 text-[#7d8696]">{copy}</p></div>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-2xl border border-[#dce6df] bg-[#f3faf6] p-4 text-xs leading-5 text-[#5d766a]"><span className="font-bold">You stay in control.</span> The agent can prepare and verify, but a final approval step comes before any consequential action.</div>
        </Card>
      </div>
    </>
  );
}
