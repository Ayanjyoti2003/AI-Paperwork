"use client";

import { useState, useRef, type DragEvent, type ChangeEvent } from "react";
import { Icon } from "./icons";
import { uploadDocument } from "@/lib/api";
import type { DocumentUploadResponse } from "@/lib/types";

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".json"];
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

interface UploadZoneProps {
  onUploadSuccess?: (doc: DocumentUploadResponse) => void;
}

export function UploadZone({ onUploadSuccess }: UploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (selectedFile: File): boolean => {
    setError(null);
    setSuccess(null);

    const ext = "." + selectedFile.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file type (${ext}). Please select a PDF, TXT, MD, or JSON file.`);
      return false;
    }

    if (selectedFile.size === 0) {
      setError("The selected file is empty.");
      return false;
    }

    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      setError(`File is too large (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB). Limit is ${MAX_FILE_SIZE_MB} MB.`);
      return false;
    }

    return true;
  };

  const handleFile = async (selectedFile: File) => {
    if (!validateFile(selectedFile)) {
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    setFile(selectedFile);
    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await uploadDocument(selectedFile);
      setSuccess(`"${response.filename}" successfully added to your vault.`);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      if (onUploadSuccess) {
        onUploadSuccess(response);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload document. Please ensure the backend is running.";
      setError(msg);
    } finally {

      setIsUploading(false);
    }
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      handleFile(droppedFile);
    }
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFile(selectedFile);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !isUploading && inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-5 py-8 text-center transition ${
          isDragging
            ? "border-[#246bfd] bg-[#edf4ff]"
            : "border-[#cfd3dc] bg-[#fbfbf9] hover:border-[#8aaaf0] hover:bg-[#f8fbff]"
        } ${isUploading ? "opacity-60 cursor-wait" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md,.json"
          className="hidden"
          onChange={onChange}
          disabled={isUploading}
        />
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]">
          {isUploading ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#246bfd] border-t-transparent" />
          ) : (
            <Icon name="upload" className="h-5 w-5" />
          )}
        </div>
        <p className="mt-3 text-sm font-semibold text-[#253044]">
          {isUploading
            ? "Uploading and indexing document..."
            : file
            ? file.name
            : "Drop a document here or browse"}
        </p>
        <p className="mt-1 text-xs text-[#8c94a1]">
          PDF, TXT, MD, or JSON · up to {MAX_FILE_SIZE_MB} MB
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2.5 rounded-xl border border-[#f5c6cb] bg-[#fff3f4] p-3 text-xs text-[#c93b4a]">
          <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="leading-snug">{error}</p>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-2.5 rounded-xl border border-[#c3e6cb] bg-[#f2faf6] p-3 text-xs text-[#16815d]">
          <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="leading-snug">{success}</p>
        </div>
      )}
    </div>
  );
}
