import type { Requirement } from "./types";

export const dashboardStats = [
  { label: "Ready to submit", value: "1", hint: "Passport application" },
  { label: "In progress", value: "2", hint: "Scholarship, admission" },
  { label: "Documents", value: "14", hint: "11 verified" },
];

export const recentDocuments = [
  { name: "aadhaar.pdf", type: "Identity proof", status: "Verified", date: "Today" },
  { name: "bank_statement.pdf", type: "Address proof", status: "Verified", date: "Today" },
  { name: "degree_certificate.pdf", type: "Education", status: "Verified", date: "12 Sep" },
  { name: "passport_photo.jpg", type: "Photograph", status: "Valid", date: "12 Sep" },
];

export const passportRequirements: Requirement[] = [
  { label: "Passport application form", detail: "Prepared from your verified information", status: "verified", action: "View" },
  { label: "Identity proof", detail: "aadhaar.pdf · Page 1", status: "verified", action: "View" },
  { label: "Current address proof", detail: "bank_statement.pdf · Page 1", status: "verified", action: "View" },
  { label: "Recent passport photo", detail: "passport_photo.jpg", status: "verified", action: "View" },
  { label: "Birth proof", detail: "No accepted document found", status: "missing", action: "Add" },
  { label: "Signature verification", detail: "Signature is visible but needs your confirmation", status: "review", action: "Review" },
];

export const applications = [
  { title: "Passport application", status: "Ready for review", progress: 83, updated: "Updated today", href: "/applications/passport" },
  { title: "University admission", status: "Collecting documents", progress: 58, updated: "Updated yesterday", href: "/applications/passport" },
  { title: "State scholarship", status: "Needs information", progress: 36, updated: "Updated 10 Sep", href: "/applications/passport" },
];
