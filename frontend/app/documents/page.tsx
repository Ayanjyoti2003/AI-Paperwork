"use client";

import { useEffect, useState, useCallback } from "react";
import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { SectionTitle } from "@/components/section-title";
import { DocumentRow } from "@/components/document-row";
import { UploadZone } from "@/components/upload-zone";
import { Icon } from "@/components/icons";
import { fetchDocuments } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";

function getDocumentTypeLabel(filename: string, fileType: string): string {
  const lower = filename.toLowerCase();
  if (lower.includes("identity") || lower.includes("aadhaar") || lower.includes("passport")) {
    return "Identity proof";
  }
  if (lower.includes("address") || lower.includes("utility") || lower.includes("bill")) {
    return "Address proof";
  }
  if (lower.includes("cert") || lower.includes("degree") || lower.includes("diploma")) {
    return "Education credential";
  }
  if (lower.includes("photo")) {
    return "Photograph";
  }
  return `${fileType.toUpperCase()} Document`;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchDocuments();
      setDocuments(res.documents || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load documents";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  return (
    <>
      <PageHeading
        title="My documents"
        description="A private document vault the agent can search when you start a new request."
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card className="p-5 md:p-6">
          <SectionTitle
            title="Document vault"
            description="Each extracted fact keeps a reference to its source document."
            action={
              <button
                onClick={loadDocuments}
                className="flex items-center gap-2 rounded-xl border border-[#dddcd6] bg-white px-3 py-2 text-xs font-semibold text-[#5f697b] hover:bg-[#f7f6f2]"
              >
                <Icon name="search" className="h-4 w-4" />
                Refresh
              </button>
            }
          />

          <div className="mt-4">
            {loading && documents.length === 0 ? (
              <div className="flex items-center justify-center py-10 text-sm text-[#768092]">
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-[#246bfd] border-t-transparent" />
                Loading vault documents...
              </div>
            ) : error && documents.length === 0 ? (
              <div className="rounded-xl border border-[#f8d7da] bg-[#fff3f4] p-4 text-xs text-[#b32b39]">
                <p className="font-semibold">Unable to connect to backend vault</p>
                <p className="mt-1">{error}</p>
                <button
                  onClick={loadDocuments}
                  className="mt-2 text-xs font-bold text-[#246bfd] underline"
                >
                  Retry
                </button>
              </div>
            ) : documents.length === 0 ? (
              <p className="py-8 text-center text-sm text-[#8c94a1]">
                No documents found in vault. Upload one on the right to get started.
              </p>
            ) : (
              documents.map((doc) => (
                <DocumentRow
                  key={doc.document_id}
                  name={doc.filename}
                  type={getDocumentTypeLabel(doc.filename, doc.file_type)}
                  status="Available"
                  date={`${(doc.size_bytes / 1024).toFixed(1)} KB`}
                />
              ))
            )}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-5">
            <SectionTitle
              title="Add a document"
              description="Files stay associated with your workspace."
            />
            <div className="mt-4">
              <UploadZone onUploadSuccess={loadDocuments} />
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex gap-3">
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]">
                <Icon name="shield" className="h-4.5 w-4.5" />
              </div>
              <div>
                <p className="text-sm font-bold">Private by design</p>
                <p className="mt-1 text-xs leading-5 text-[#7f8795]">
                  Only the relevant document content is extracted for evidence verification. The UI is designed around evidence snippets with strict document provenance.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

