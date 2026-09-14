"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { StatusPill } from "./ui/status-pill";
import { Progress } from "./ui/progress";
import { assessPaperwork, preparePackage } from "@/lib/api";
import type {
  PreparedPackageResponse,
  ReadinessAssessment,
} from "@/lib/types";

const suggestions = [
  "I want to apply for an Indian passport.",
  "I want to apply for a driving license.",
  "Apply for a new PAN card.",
  "I want to complete the example application.",
  "Apply for a Canadian study permit.",
];

function extractApplicantName(assessment: ReadinessAssessment): string {
  for (const check of [
    ...assessment.satisfied_requirements,
    ...assessment.conflicts,
    ...assessment.uncertainties,
  ]) {
    for (const ev of check.evidence) {
      if (
        ["full_name", "name", "applicant_name"].includes(ev.field.toLowerCase()) &&
        ev.value
      ) {
        return ev.value;
      }
    }
  }
  return "Applicant";
}

export function RequestComposer() {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<ReadinessAssessment | null>(null);

  // Human Review & Approval state
  const [applicantName, setApplicantName] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [preparingPackage, setPreparingPackage] = useState(false);
  const [preparedPackage, setPreparedPackage] =
    useState<PreparedPackageResponse | null>(null);
  const [packageError, setPackageError] = useState<string | null>(null);
  const [showSummaryPreview, setShowSummaryPreview] = useState(false);

  const handleSubmit = async (goalToSubmit?: string) => {
    const goal = (goalToSubmit || value).trim();
    if (!goal) return;
    if (goalToSubmit) setValue(goalToSubmit);

    setLoading(true);
    setError(null);
    setAssessment(null);
    setPreparedPackage(null);
    setPackageError(null);

    try {
      const res = await assessPaperwork(goal);
      setAssessment(res);
      setApplicantName(extractApplicantName(res));
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handlePreparePackage = async () => {
    if (!assessment) return;

    setPreparingPackage(true);
    setPackageError(null);

    try {
      const res = await preparePackage(
        assessment,
        applicantName || undefined,
        reviewerNotes || undefined
      );
      setPreparedPackage(res);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to prepare application package.";
      setPackageError(msg);
    } finally {
      setPreparingPackage(false);
    }
  };

  const handleDownloadJson = () => {
    if (!preparedPackage) return;
    const blob = new Blob(
      [JSON.stringify(preparedPackage.package, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `readiness_package_${preparedPackage.package_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadMarkdown = () => {
    if (!preparedPackage) return;
    const blob = new Blob([preparedPackage.markdown_summary], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `readiness_summary_${preparedPackage.package_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Quick Suggestions */}
      <div>
        <label className="text-xs font-semibold uppercase tracking-wider text-[#7a8494]">
          Quick Suggestions
        </label>
        <div className="mt-2 flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setValue(suggestion);
                handleSubmit(suggestion);
              }}
              className="rounded-full border border-[#dddcd6] bg-white px-3 py-1.5 text-xs font-medium text-[#667085] transition hover:border-[#b9c9ea] hover:text-[#245fce]"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* Input box */}
      <div className="rounded-2xl border border-[#dfddd7] bg-white p-2 shadow-sm focus-within:border-[#9ebaf3] focus-within:ring-4 focus-within:ring-[#edf4ff]">
        <textarea
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setError(null);
          }}
          rows={3}
          placeholder="Tell me what you need to get done… (e.g. 'I want to complete the example application.')"
          className="w-full resize-none bg-transparent px-3 py-2 text-[15px] leading-6 outline-none placeholder:text-[#a2a8b2]"
        />
        <div className="flex items-center justify-between gap-3 border-t border-[#efede8] px-2 pt-2">
          <Link
            href="/documents"
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-semibold text-[#768092] hover:bg-[#f5f4f0]"
          >
            <Icon name="upload" className="h-4 w-4" />
            Manage vault files
          </Link>
          <button
            disabled={!value.trim() || loading}
            onClick={() => handleSubmit()}
            className="flex items-center gap-2 rounded-xl bg-[#246bfd] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f61e7] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Assessing...</span>
              </>
            ) : (
              <>
                <span>Start verification</span>
                <Icon name="spark" className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Loading state indicator */}
      {loading ? (
        <div className="rounded-2xl border border-[#dce4f4] bg-[#f8fbff] p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#edf4ff] text-[#246bfd]">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#246bfd] border-t-transparent" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#1e2d42]">
                Paperwork Agent is running verification pipeline...
              </p>
              <p className="mt-0.5 text-xs text-[#697892]">
                Discovering target workflow, reading documents (with OCR for scans/images), extracting facts with document provenance, and performing cross-document conflict checks.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Error display */}
      {error ? (
        <div className="rounded-2xl border border-[#f8d7da] bg-[#fff3f4] p-4 text-xs text-[#b32b39]">
          <div className="flex gap-2">
            <Icon name="alert" className="h-4 w-4 shrink-0 text-[#c93b4a]" />
            <div>
              <p className="font-bold">Assessment Request Failed</p>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Assessment Results */}
      {assessment ? (
        <div className="space-y-6 pt-2">
          {/* Header Card */}
          <div className="rounded-2xl border border-[#e5e3dc] bg-[#fbfbf9] p-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#8b93a0]">
                  Workflow Matched
                </span>
                <h3 className="mt-1 text-lg font-bold text-[#232f42]">
                  {assessment.workflow_name}
                </h3>
                <p className="text-xs text-[#707c8e]">
                  Workflow ID: <code className="rounded bg-white px-1.5 py-0.5 border border-[#e3e1da]">{assessment.workflow_id}</code>
                </p>
              </div>
              <div className="flex flex-col items-start sm:items-end gap-2">
                {assessment.ready ? (
                  <StatusPill tone="success" dot>
                    Ready for submission
                  </StatusPill>
                ) : (
                  <StatusPill tone="warning" dot>
                    Action Required · Incomplete
                  </StatusPill>
                )}
                <div className="w-44">
                  <div className="mb-1 flex justify-between text-[11px] font-semibold text-[#768294]">
                    <span>Readiness score</span>
                    <span>{assessment.completion_percentage}%</span>
                  </div>
                  <Progress value={assessment.completion_percentage} />
                </div>
              </div>
            </div>
          </div>

          {/* 1. Flagged Conflicts Section */}
          {assessment.conflicts.length > 0 ? (
            <div className="rounded-2xl border border-[#fed7aa] bg-[#fffaf5] p-5">
              <div className="flex items-start gap-3">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#ffedd5] text-[#ea580c]">
                  <Icon name="alert" className="h-4.5 w-4.5" />
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-[#9a3412]">
                    Cross-Document Conflicts Flagged ({assessment.conflicts.length})
                  </h4>
                  <p className="mt-0.5 text-xs text-[#7c2d12]">
                    The agent verified conflicting information across submitted documents. This discrepancy must be clarified before external submission.
                  </p>

                  <div className="mt-4 space-y-3">
                    {assessment.conflicts.map((check) => (
                      <div
                        key={check.requirement_id}
                        className="rounded-xl border border-[#fed7aa] bg-white p-3.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[#431407]">
                            {check.requirement_name}
                          </span>
                          <span className="text-[10px] font-semibold text-[#c2410c] uppercase">
                            Discrepancy
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-[#7c2d12]">
                          {check.notes}
                        </p>

                        {check.conflicts.map((conf) => (
                          <div
                            key={conf.field}
                            className="mt-2.5 rounded-lg bg-[#fff7ed] p-2.5 text-xs"
                          >
                            <span className="font-semibold text-[#9a3412]">
                              Field: {conf.field}
                            </span>
                            <div className="mt-1.5 grid gap-1.5 sm:grid-cols-2">
                              {conf.values.map((v, i) => (
                                <div
                                  key={i}
                                  className="rounded border border-[#fdba74] bg-white px-2 py-1 text-[11px]"
                                >
                                  <span className="text-[#9a3412] font-semibold">
                                    &ldquo;{v.value}&rdquo;
                                  </span>{" "}
                                  <span className="text-[#9ca3af]">
                                    (source: {v.source_document})
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {/* 2. Missing Requirements Section */}
          {assessment.missing_requirements.length > 0 ? (
            <div className="rounded-2xl border border-[#fecaca] bg-[#fef2f2] p-5">
              <div className="flex items-start gap-3">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#fee2e2] text-[#dc2626]">
                  <Icon name="alert" className="h-4.5 w-4.5" />
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-[#991b1b]">
                    Missing Documents & Requirements ({assessment.missing_requirements.length})
                  </h4>
                  <p className="mt-0.5 text-xs text-[#7f1d1d]">
                    These items are currently missing from your document vault and required for complete submission.
                  </p>

                  <div className="mt-4 space-y-2.5">
                    {assessment.missing_requirements.map((check) => (
                      <div
                        key={check.requirement_id}
                        className="rounded-xl border border-[#fca5a5] bg-white p-3 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[#7f1d1d]">
                            {check.requirement_name}
                          </span>
                          <span className="text-[10px] font-semibold text-[#dc2626] uppercase">
                            Missing
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-[#6b7280]">
                          {check.notes || "No supporting document found in vault."}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {/* 3. Satisfied Requirements Section with Provenance */}
          {assessment.satisfied_requirements.length > 0 ? (
            <div className="rounded-2xl border border-[#bbf7d0] bg-[#f0fdf4] p-5">
              <div className="flex items-start gap-3">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#dcfce7] text-[#16a34a]">
                  <Icon name="check" className="h-4.5 w-4.5" />
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-[#166534]">
                    Satisfied Requirements ({assessment.satisfied_requirements.length})
                  </h4>
                  <p className="mt-0.5 text-xs text-[#14532d]">
                    Verified with provenance from local documents.
                  </p>

                  <div className="mt-4 space-y-2.5">
                    {assessment.satisfied_requirements.map((check) => (
                      <div
                        key={check.requirement_id}
                        className="rounded-xl border border-[#86efac] bg-white p-3.5 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[#14532d]">
                            {check.requirement_name}
                          </span>
                          <span className="text-[10px] font-semibold text-[#16a34a] uppercase">
                            Verified
                          </span>
                        </div>
                        {check.evidence && check.evidence.length > 0 ? (
                          <div className="mt-2 space-y-1">
                            {check.evidence.map((ev, i) => (
                              <div
                                key={i}
                                className="rounded bg-[#f0fdf4] px-2.5 py-1.5 text-[11px] text-[#166534]"
                              >
                                <span className="font-semibold">{ev.field}:</span>{" "}
                                <span>&ldquo;{ev.value}&rdquo;</span>{" "}
                                <span className="text-[#65a30d]">
                                  (from {ev.source_document}
                                  {ev.extraction_method && ev.extraction_method !== "native_text" ? ` · ${ev.extraction_method}` : ""}
                                  {typeof ev.confidence === "number" ? ` · ${(ev.confidence * 100).toFixed(0)}% OCR` : ""})
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {/* Recommended Next Actions */}
          {assessment.recommended_next_actions && assessment.recommended_next_actions.length > 0 ? (
            <div className="rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#475569]">
                Recommended Actions
              </h4>
              <ul className="mt-3 space-y-2">
                {assessment.recommended_next_actions.map((act, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 text-xs text-[#475569]">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[#246bfd] shrink-0" />
                    <span>{act}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex gap-3">
                <Link
                  href="/documents"
                  className="inline-flex items-center gap-2 rounded-xl bg-[#246bfd] px-4 py-2 text-xs font-semibold text-white hover:bg-[#1f61e7]"
                >
                  <Icon name="upload" className="h-3.5 w-3.5" />
                  Upload missing documents
                </Link>
              </div>
            </div>
          ) : null}

          {/* 4. Human Review & Work Product Authorization */}
          <div className="rounded-2xl border border-[#d8d6cf] bg-white p-5 md:p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#edf4ff] text-[#246bfd]">
                <Icon name="user" className="h-4.5 w-4.5" />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-bold text-[#1e2d42]">
                  Human Review & Work Product Authorization
                </h4>
                <p className="mt-1 text-xs leading-5 text-[#6c7789]">
                  <strong>You stay in control.</strong> The agent has assessed your paperwork and verified evidence against requirements. Preparing the application package is authorized by you — no external submission occurs automatically.
                </p>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#697587]">
                      Applicant Name
                    </label>
                    <input
                      type="text"
                      value={applicantName}
                      onChange={(e) => setApplicantName(e.target.value)}
                      placeholder="e.g. Jane Alexandra Doe"
                      className="mt-1 w-full rounded-xl border border-[#d9d7d1] bg-white px-3 py-2 text-xs text-[#283346] outline-none focus:border-[#246bfd]"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold uppercase tracking-wider text-[#697587]">
                      Reviewer Notes (Optional)
                    </label>
                    <input
                      type="text"
                      value={reviewerNotes}
                      onChange={(e) => setReviewerNotes(e.target.value)}
                      placeholder="e.g. Approved for package preparation"
                      className="mt-1 w-full rounded-xl border border-[#d9d7d1] bg-white px-3 py-2 text-xs text-[#283346] outline-none focus:border-[#246bfd]"
                    />
                  </div>
                </div>

                {packageError ? (
                  <div className="mt-3 text-xs text-[#dc2626]">
                    {packageError}
                  </div>
                ) : null}

                {!preparedPackage ? (
                  <button
                    disabled={preparingPackage}
                    onClick={handlePreparePackage}
                    className="mt-5 flex items-center gap-2 rounded-xl bg-[#1f2d44] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#152033] disabled:opacity-40"
                  >
                    {preparingPackage ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        <span>Preparing package...</span>
                      </>
                    ) : (
                      <>
                        <Icon name="check" className="h-4 w-4" />
                        <span>Approve & Prepare Package</span>
                      </>
                    )}
                  </button>
                ) : (
                  <div className="mt-5 rounded-2xl border border-[#bbf7d0] bg-[#f0fdf4] p-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <StatusPill tone="success">
                            Approved & Prepared
                          </StatusPill>
                          <span className="text-xs font-semibold text-[#166534]">
                            Package ID: <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-[#86efac]">{preparedPackage.package_id}</code>
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-[#15803d]">
                          Work product generated deterministically from approved assessment.
                        </p>
                      </div>

                      {/* Download Buttons */}
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={handleDownloadJson}
                          className="flex items-center gap-1.5 rounded-xl border border-[#86efac] bg-white px-3 py-2 text-xs font-semibold text-[#166534] shadow-sm hover:bg-[#f0fdf4]"
                        >
                          <Icon name="download" className="h-3.5 w-3.5" />
                          Download JSON
                        </button>
                        <button
                          onClick={handleDownloadMarkdown}
                          className="flex items-center gap-1.5 rounded-xl bg-[#166534] px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-[#14532d]"
                        >
                          <Icon name="file" className="h-3.5 w-3.5" />
                          Download Markdown
                        </button>
                        <button
                          onClick={() => setShowSummaryPreview(!showSummaryPreview)}
                          className="flex items-center gap-1 rounded-xl border border-[#d8d6cf] bg-white px-2.5 py-2 text-xs font-medium text-[#4b5563] hover:bg-[#f9fafb]"
                        >
                          {showSummaryPreview ? "Hide Preview" : "View Summary"}
                        </button>
                      </div>
                    </div>

                    {showSummaryPreview ? (
                      <div className="mt-4 rounded-xl border border-[#e5e7eb] bg-white p-4 text-xs font-mono text-[#374151] max-h-72 overflow-y-auto whitespace-pre-wrap">
                        {preparedPackage.markdown_summary}
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
