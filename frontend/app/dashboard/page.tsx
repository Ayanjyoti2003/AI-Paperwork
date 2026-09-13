import Link from "next/link";
import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { SectionTitle } from "@/components/section-title";
import { Icon } from "@/components/icons";
import { ApplicationCard } from "@/components/application-card";
import { DocumentRow } from "@/components/document-row";
import { applications, dashboardStats, recentDocuments } from "@/lib/data";

export default function DashboardPage() {
  return (
    <>
      <PageHeading title="Good afternoon, Arion" description="Here’s where your paperwork stands. One application is almost ready to leave your desk." action={<Link href="/new-request" className="inline-flex items-center gap-2 rounded-xl bg-[#246bfd] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1f61e7]"><Icon name="plus" className="h-4 w-4" />New request</Link>} />

      <div className="grid gap-4 md:grid-cols-3">
        {dashboardStats.map((stat) => (
          <Card key={stat.label} className="p-5">
            <p className="text-sm font-medium text-[#727b8c]">{stat.label}</p>
            <div className="mt-4 flex items-end justify-between gap-3"><p className="text-3xl font-bold tracking-[-0.04em]">{stat.value}</p><p className="pb-1 text-xs text-[#9aa1ad]">{stat.hint}</p></div>
          </Card>
        ))}
      </div>

      <Card className="paper-grid mt-5 overflow-hidden p-6 md:p-7">
        <div className="grid gap-7 xl:grid-cols-[1.25fr_.75fr] xl:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#dce4f4] bg-white px-3 py-1.5 text-xs font-semibold text-[#496485]"><Icon name="spark" className="h-3.5 w-3.5 text-[#246bfd]" />Continue where you left off</div>
            <h2 className="mt-4 max-w-2xl text-2xl font-bold tracking-[-0.035em] md:text-[30px]">Your passport application is 83% ready.</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#687386]">Most evidence has been verified. You still need an accepted birth proof and a quick signature confirmation before the final package can be generated.</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link href="/applications/passport" className="inline-flex items-center gap-2 rounded-xl bg-[#1f2d44] px-4 py-2.5 text-sm font-semibold text-white">Review application <Icon name="arrow" className="h-4 w-4" /></Link>
              <Link href="/documents" className="rounded-xl border border-[#d7d6d1] bg-white px-4 py-2.5 text-sm font-semibold text-[#566174]">Open documents</Link>
            </div>
          </div>
          <div className="rounded-[20px] border border-[#e5e2da] bg-[#fffdf7] p-5 shadow-sm">
            <p className="hand-note text-sm font-semibold text-[#536174]">Before you submit</p>
            <div className="mt-4 space-y-3">
              <div className="flex gap-3"><div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#eaf7f1] text-[#16815d]"><Icon name="check" className="h-3.5 w-3.5" /></div><div><p className="text-sm font-semibold">4 requirements verified</p><p className="text-xs text-[#8c94a1]">Identity, address, photo and application details</p></div></div>
              <div className="flex gap-3"><div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#fff0f1] text-[#c93b4a]"><Icon name="alert" className="h-3.5 w-3.5" /></div><div><p className="text-sm font-semibold">1 document missing</p><p className="text-xs text-[#8c94a1]">Accepted proof of birth</p></div></div>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-7 grid gap-6 xl:grid-cols-[1fr_420px]">
        <div>
          <SectionTitle title="Applications" description="Keep each administrative task in one place." action={<Link href="/applications" className="text-sm font-semibold text-[#246bfd]">View all</Link>} />
          <div className="mt-4 grid gap-4 md:grid-cols-3">{applications.map((item) => <ApplicationCard key={item.title} {...item} />)}</div>
        </div>
        <Card className="p-5">
          <SectionTitle title="Recent documents" description="Latest files in your vault." action={<Link href="/documents" className="text-sm font-semibold text-[#246bfd]">View all</Link>} />
          <div className="mt-3">{recentDocuments.slice(0, 4).map((item) => <DocumentRow key={item.name} {...item} />)}</div>
        </Card>
      </div>
    </>
  );
}
