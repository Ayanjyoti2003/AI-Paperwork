"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { StatusPill } from "./ui/status-pill";
import { Progress } from "./ui/progress";
import { assessPaperwork } from "@/lib/api";
import type { ReadinessAssessment } from "@/lib/types";

const suggestions = [
  "I want to apply for an Indian passport.",
  "I want to apply for a driving license.",
  "Apply for a new PAN card.",
  "I want to complete the example application.",
  "Apply for a Canadian study permit.",
];


export function RequestComposer() {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<ReadinessAssessment | null>(null);

  const handleSubmit = async (goalToSubmit?: string) => {
    const goal = (goalToSubmit || value).trim();
    if (!goal) return;

    setLoading(true);
    setError(null);
    setAssessment(null);

    try {
      const result = await assessPaperwork(goal);
      setAssessment(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to process assessment. Please verify backend is running.";
      setError(msg);
    } finally {

      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <label className="text-xs font-semibold uppercase tracking-wider text-[#7a8494]">
          Quick Suggestions
        </label>
        <div className="mt-2 flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
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

      <div className="rounded-2xl border border-[#dfddd7] bg-white p-2 shadow-sm focus-within:border-[#9ebaf3] focus-within:ring-4 focus-within:ring-[#edf4ff]">
        <textarea
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setError(null);
          }}
          rows={3}
          placeholder="Tell me what you need to get done (e.g. 'I want to complete the example application')..."
          className="w-full resize-none bg-transparent px-3 py-2 text-[15px] leading-6 outline-none placeholder:text-[#a2a8b2]"
        />
        <div className="flex items-center justify-between gap-3 border-t border-[#efede8] px-2 pt-2">
          <Link
            href="/documents"
            className="flex items-center gap-2 rounded-lg px-2 py-2 text-xs font-semibold text-[#768092] hover:bg-[#f5f4f0]"
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
                Analyzing evidence...
              </>
            ) : (
              <>
                Start request <Icon name="send" className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-[#f5c6cb] bg-[#fff3f4] p-4 text-sm text-[#c93b4a]">
          <Icon name="alert" className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Assessment Request Failed</p>
            <p className="mt-0.5 text-xs text-[#a82e3b]">{error}</p>
          </div>
        </div>
      )}

      {assessment && (
        <div className="space-y-5 rounded-2xl border border-[#d6e5dd] bg-[#f9fcfa] p-5 md:p-6">
          {/* Header */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-[#e1ece5] pb-5">
            <div>
              <div className="flex items-center gap-2">
                <StatusPill tone={assessment.ready ? "success" : "warning"} dot>
                  {assessment.ready ? "Ready to Submit" : "Needs Attention"}
                </StatusPill>
                <span className="text-xs text-[#6e7d75]">
                  {assessment.workflow_name}
                </span>
              </div>
              <h3 className="mt-2 text-xl font-bold tracking-[-0.02em] text-[#1d2939]">
                {assessment.ready
                  ? "All requirements verified!"
                  : `Readiness: ${assessment.completion_percentage}% completed`}
              </h3>
            </div>
            <div className="w-full sm:w-48">
              <div className="mb-1 flex justify-between text-xs font-semibold text-[#576b61]">
                <span>Progress</span>
                <span>{assessment.completion_percentage}%</span>
              </div>
              <Progress value={assessment.completion_percentage} />
            </div>
          </div>

          {/* Satisfied Requirements */}
          {assessment.satisfied_requirements.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#16815d]">
                Satisfied Requirements ({assessment.satisfied_requirements.length})
              </h4>
              <div className="mt-2 space-y-2">
                {assessment.satisfied_requirements.map((req) => (
                  <div
                    key={req.requirement_id}
                    className="rounded-xl border border-[#d3ebe0] bg-white p-3.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon name="check" className="h-4 w-4 text-[#16815d]" />
                        <span className="text-sm font-semibold text-[#283346]">
                          {req.requirement_name}
                        </span>
                      </div>
                      <StatusPill tone="success">Verified</StatusPill>
                    </div>
                    {req.evidence && req.evidence.length > 0 && (
                      <div className="mt-2.5 space-y-1.5 border-t border-[#f0f4f2] pt-2">
                        {req.evidence.map((ev, idx) => (
                          <div
                            key={idx}
                            className="flex flex-wrap items-baseline justify-between text-xs text-[#526071]"
                          >
                            <span>
                              <strong className="text-[#333f51] capitalize">
                                {ev.field.replace("_", " ")}:
                              </strong>{" "}
                              {ev.value || "Present"}
                            </span>
                            {ev.evidence_snippet && (
                              <span className="text-[11px] text-[#7d8898] italic">
                                &ldquo;{ev.evidence_snippet}&rdquo;
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Missing Requirements */}
          {assessment.missing_requirements.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#c93b4a]">
                Missing Requirements ({assessment.missing_requirements.length})
              </h4>
              <div className="mt-2 space-y-2">
                {assessment.missing_requirements.map((req) => (
                  <div
                    key={req.requirement_id}
                    className="rounded-xl border border-[#f7d6d9] bg-white p-3.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon name="alert" className="h-4 w-4 text-[#c93b4a]" />
                        <span className="text-sm font-semibold text-[#283346]">
                          {req.requirement_name}
                        </span>
                      </div>
                      <StatusPill tone="danger">Missing</StatusPill>
                    </div>
                    {req.notes && (
                      <p className="mt-2 text-xs leading-5 text-[#737d8e]">{req.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Conflicts */}
          {assessment.conflicts.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#a96716]">
                Detected Conflicts ({assessment.conflicts.length})
              </h4>
              <div className="mt-2 space-y-2">
                {assessment.conflicts.map((req) => (
                  <div
                    key={req.requirement_id}
                    className="rounded-xl border border-[#fae2bd] bg-white p-3.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon name="alert" className="h-4 w-4 text-[#a96716]" />
                        <span className="text-sm font-semibold text-[#283346]">
                          {req.requirement_name}
                        </span>
                      </div>
                      <StatusPill tone="warning">Discrepancy</StatusPill>
                    </div>
                    {req.notes && (
                      <p className="mt-2 text-xs leading-5 text-[#855e1a]">{req.notes}</p>
                    )}
                    {req.conflicts && req.conflicts.length > 0 && (
                      <div className="mt-2 space-y-1 rounded-lg bg-[#fffaf2] p-2 text-xs text-[#6e5320]">
                        {req.conflicts.map((c, cIdx) => (
                          <div key={cIdx}>
                            <span className="font-semibold capitalize">{c.field}:</span>
                            <ul className="ml-4 list-disc space-y-0.5">
                              {c.values.map((v, vIdx) => (
                                <li key={vIdx}>
                                  &ldquo;{v.value}&rdquo; (source: {v.source_document})
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Next Actions */}
          {assessment.recommended_next_actions.length > 0 && (
            <div className="border-t border-[#e1ece5] pt-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#4f5c6b]">
                Recommended Actions
              </h4>
              <ul className="mt-2 space-y-1.5">
                {assessment.recommended_next_actions.map((act, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-[#526071]">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#246bfd] shrink-0" />
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
          )}
        </div>
      )}
    </div>
  );
}
