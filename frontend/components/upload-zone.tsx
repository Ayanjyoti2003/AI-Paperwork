"use client";

import { useState } from "react";
import { Icon } from "./icons";
import { uploadDocument } from "@/lib/api";
import type { DocumentUploadResponse } from "@/lib/types";

export function UploadZone({
  onUploadSuccess,
}: {
  onUploadSuccess?: (doc: DocumentUploadResponse) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const handleFile = async (file: File) => {
    setUploading(true);
    setFeedback(null);
    try {
      const result = await uploadDocument(file);
      setFeedback({
        type: "success",
        message: `Successfully uploaded ${result.filename} (${(
          result.size_bytes / 1024
        ).toFixed(1)} KB)`,
      });
      onUploadSuccess?.(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to upload document.";
      setFeedback({ type: "error", message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <label
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-5 py-8 text-center transition ${
          uploading
            ? "border-[#246bfd] bg-[#f2f7ff] opacity-75 cursor-wait"
            : "border-[#cfd3dc] bg-[#fbfbf9] hover:border-[#8aaaf0] hover:bg-[#f8fbff]"
        }`}
      >
        <input
          type="file"
          accept=".txt,.md,.json,.pdf,.png,.jpg,.jpeg"
          disabled={uploading}
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              handleFile(file);
            }
          }}
        />
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]">
          {uploading ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#246bfd] border-t-transparent" />
          ) : (
            <Icon name="upload" className="h-5 w-5" />
          )}
        </div>
        <p className="mt-3 text-sm font-semibold text-[#253044]">
          {uploading ? "Uploading safely to vault..." : "Drop a document here or browse"}
        </p>
        <p className="mt-1 text-xs text-[#8c94a1]">
          TXT, MD, JSON, PDF or Images (PNG, JPG) · up to 10 MB
        </p>
      </label>

      {feedback ? (
        <div
          className={`rounded-xl px-3.5 py-2.5 text-xs font-medium ${
            feedback.type === "success"
              ? "border border-[#cde8d7] bg-[#eef9f2] text-[#137452]"
              : "border border-[#f8d7da] bg-[#fff3f4] text-[#b32b39]"
          }`}
        >
          {feedback.message}
        </div>
      ) : null}
    </div>
  );
}

