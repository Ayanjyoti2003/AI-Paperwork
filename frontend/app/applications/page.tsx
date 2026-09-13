import Link from "next/link";
import { PageHeading } from "@/components/page-heading";
import { ApplicationCard } from "@/components/application-card";
import { applications } from "@/lib/data";
import { Icon } from "@/components/icons";

export default function ApplicationsPage() {
  return (
    <>
      <PageHeading title="Applications" description="Every request becomes a traceable workspace with requirements, evidence, checks and approvals." action={<Link href="/new-request" className="inline-flex items-center gap-2 rounded-xl bg-[#246bfd] px-4 py-2.5 text-sm font-semibold text-white"><Icon name="plus" className="h-4 w-4" />New request</Link>} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{applications.map((item) => <ApplicationCard key={item.title} {...item} />)}</div>
    </>
  );
}
