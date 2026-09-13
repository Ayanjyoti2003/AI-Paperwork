export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

export type RequirementStatus = "verified" | "missing" | "review";

export type Requirement = {
  label: string;
  detail: string;
  status: RequirementStatus;
  action: string;
};
