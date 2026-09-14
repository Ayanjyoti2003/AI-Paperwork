"use client";

import { useEffect, useState, useCallback } from "react";
import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { SectionTitle } from "@/components/section-title";
import { DocumentRow } from "@/components/document-row";
import { UploadZone } from "@/components/upload-zone";
import { Icon } from "@/components/icons";
import { fetchDocuments, deleteDocument } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoStr?: string | null): string {
  if (!isoStr) return "Stored";
  try {
    const d = new Date(isoStr);
    const now = new Date();
    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();
    if (isToday) return "Today";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return "Stored";
  }
}

function getDocumentTypeLabel(filename: string, fileType: string): string {
  const lower = filename.toLowerCase();
  if (lower.includes("identity") || lower.includes("aadhaar") || lower.includes("passport") || lower.includes("id")) {
    return "Identity proof";
  }
  if (lower.includes("address") || lower.includes("utility") || lower.includes("bill") || lower.includes("statement")) {
    return "Address proof";
  }
  if (lower.includes("cert") || lower.includes("degree") || lower.includes("diploma") || lower.includes("education")) {
    return "Education credential";
  }
  if (lower.includes("photo") || lower.includes("picture") || lower.includes("image")) {
    return "Photograph";
  }
  if (["png", "jpg", "jpeg"].includes(fileType.toLowerCase())) {
    return "Scanned Image";
  }
  return `${fileType ? fileType.toUpperCase() : "FILE"} Document`;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchDocuments();
      setDocuments(res.documents || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load documents from backend.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    fetchDocuments()
      .then((res) => {
        if (!ignore) {
          setDocuments(res.documents || []);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load documents from backend.";
          setError(msg);
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  const handleDelete = async (docId: string) => {
    if (!confirm("Are you sure you want to remove this document from your vault?")) {
      return;
    }
    try {
      await deleteDocument(docId);
      await loadDocuments();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete document.");
    }
  };

  const filteredDocs = documents.filter((doc) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const typeLabel = getDocumentTypeLabel(doc.filename, doc.file_type).toLowerCase();
    return (
      doc.filename.toLowerCase().includes(q) ||
      doc.file_type.toLowerCase().includes(q) ||
      typeLabel.includes(q)
    );
  });

  return (
    <>
      <PageHeading
        title="My documents"
        description="A private document vault the agent searches when verifying requirements for your requests."
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card className="p-5 md:p-6">
          <SectionTitle
            title="Document vault"
            description="Each extracted fact keeps verifiable evidence provenance to its source file."
            action={
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowSearch((prev) => !prev)}
                  className="flex items-center gap-1.5 rounded-xl border border-[#dddcd6] bg-white px-3 py-1.5 text-xs font-semibold text-[#5f697b] hover:bg-[#f6f5f2]"
                >
                  <Icon name="search" className="h-3.5 w-3.5" />
                  {showSearch ? "Hide search" : "Search"}
                </button>
                <button
                  onClick={loadDocuments}
                  className="flex items-center gap-1.5 rounded-xl border border-[#dddcd6] bg-white px-3 py-1.5 text-xs font-semibold text-[#5f697b] hover:bg-[#f6f5f2]"
                >
                  Refresh
                </button>
              </div>
            }
          />

          {showSearch && (
            <div className="mt-4">
              <input
                type="text"
                placeholder="Filter by filename, format, or type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-[#d8d6d0] bg-white px-3 py-2 text-xs text-[#283346] placeholder:text-[#9aa1ad] focus:border-[#246bfd] focus:outline-none focus:ring-1 focus:ring-[#246bfd]"
                autoFocus
              />
            </div>
          )}

          <div className="mt-4">
            {loading && documents.length === 0 ? (
              <div className="flex items-center justify-center py-12 text-sm text-[#7a8393]">
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-[#246bfd] border-t-transparent" />
                Loading documents from vault...
              </div>
            ) : error && documents.length === 0 ? (
              <div className="rounded-xl border border-[#f5c6cb] bg-[#fff3f4] p-4 text-xs text-[#c93b4a]">
                <p className="font-semibold">Unable to connect to backend vault</p>
                <p className="mt-1">{error}</p>
                <button
                  onClick={loadDocuments}
                  className="mt-2 text-xs font-bold text-[#246bfd] underline"
                >
                  Retry
                </button>
              </div>
            ) : filteredDocs.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[#dcdad4] py-12 text-center text-sm text-[#88909f]">
                {searchQuery ? (
                  <p>No documents match &ldquo;{searchQuery}&rdquo;</p>
                ) : (
                  <div>
                    <p className="font-semibold text-[#374151]">Your vault is empty</p>
                    <p className="mt-1 text-xs text-[#8c94a1]">
                      Upload your identity, address, or educational documents to get started.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              filteredDocs.map((doc) => (
                <DocumentRow
                  key={doc.document_id}
                  docId={doc.document_id}
                  name={doc.filename}
                  type={getDocumentTypeLabel(doc.filename, doc.file_type)}
                  status="Available"
                  size={formatBytes(doc.size_bytes)}
                  date={formatDate(doc.modified_at)}
                  extractionMethod={doc.extraction_method}
                  onDelete={handleDelete}
                />
              ))
            )}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-5">
            <SectionTitle
              title="Add a document"
              description="Files are stored in your controlled local documents store."
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
                <p className="text-sm font-bold">Evidence-First by Design</p>
                <p className="mt-1 text-xs leading-5 text-[#7f8795]">
                  Documents stay stored locally. The agent uses targeted search and fact extraction to retrieve only the specific evidence required for each rule check, keeping verifiable provenance.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
