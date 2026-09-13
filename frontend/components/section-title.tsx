export function SectionTitle({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h2 className="text-base font-bold tracking-[-0.02em] text-[#1e293b]">{title}</h2>
        {description ? <p className="mt-1 text-sm text-[#7b8494]">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}
