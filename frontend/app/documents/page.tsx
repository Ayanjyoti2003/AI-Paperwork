import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { SectionTitle } from "@/components/section-title";
import { DocumentRow } from "@/components/document-row";
import { UploadZone } from "@/components/upload-zone";
import { recentDocuments } from "@/lib/data";
import { Icon } from "@/components/icons";

const moreDocuments = [
  { name: "class_10_certificate.pdf", type: "Education", status: "Verified", date: "8 Sep" },
  { name: "signature.png", type: "Signature", status: "Verified", date: "7 Sep" },
  { name: "old_bank_statement.pdf", type: "Address proof", status: "Expired", date: "2 Sep" },
];

export default function DocumentsPage() {
  return (
    <>
      <PageHeading title="My documents" description="A private document vault the agent can search when you start a new request." />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card className="p-5 md:p-6">
          <SectionTitle title="Document vault" description="Each extracted fact keeps a reference to its source document." action={<button className="flex items-center gap-2 rounded-xl border border-[#dddcd6] bg-white px-3 py-2 text-xs font-semibold text-[#5f697b]"><Icon name="search" className="h-4 w-4" />Search</button>} />
          <div className="mt-4">{[...recentDocuments, ...moreDocuments].map((item) => <DocumentRow key={item.name} {...item} />)}</div>
        </Card>
        <div className="space-y-5">
          <Card className="p-5"><SectionTitle title="Add a document" description="Files stay associated with your workspace." /><div className="mt-4"><UploadZone /></div></Card>
          <Card className="p-5">
            <div className="flex gap-3"><div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]"><Icon name="shield" className="h-4.5 w-4.5" /></div><div><p className="text-sm font-bold">Private by design</p><p className="mt-1 text-xs leading-5 text-[#7f8795]">Only the relevant document content should be passed into an AI task. The UI is designed around evidence snippets rather than dumping entire folders into a model.</p></div></div>
          </Card>
        </div>
      </div>
    </>
  );
}
