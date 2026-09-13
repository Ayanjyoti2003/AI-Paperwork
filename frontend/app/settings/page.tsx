import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { Icon } from "@/components/icons";

const rows = [
  ["Private document processing", "Keep document access scoped to the current workspace and only expose relevant content to the agent.", true],
  ["Approval before consequential actions", "Always require an explicit human approval before any future submission or external action.", true],
  ["Show evidence provenance", "Display document and page references beside extracted facts.", true],
];

export default function SettingsPage() {
  return (
    <>
      <PageHeading title="Settings" description="Simple controls for how your administrative workspace behaves." />
      <Card className="max-w-3xl p-5 md:p-6">
        <div className="flex items-center gap-3 border-b border-[#eceae5] pb-5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]"><Icon name="shield" className="h-5 w-5" /></div><div><p className="font-bold">Privacy & approvals</p><p className="mt-0.5 text-sm text-[#7a8393]">Defaults chosen for sensitive paperwork.</p></div></div>
        <div>{rows.map(([title, copy]) => <div key={String(title)} className="flex gap-5 border-b border-[#eceae5] py-5 last:border-0"><div className="flex-1"><p className="text-sm font-semibold">{title}</p><p className="mt-1 text-xs leading-5 text-[#7c8594]">{copy}</p></div><div className="relative mt-1 h-6 w-11 rounded-full bg-[#246bfd]"><span className="absolute right-1 top-1 h-4 w-4 rounded-full bg-white shadow" /></div></div>)}</div>
      </Card>
    </>
  );
}
