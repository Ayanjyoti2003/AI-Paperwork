export function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <p className="mb-1 text-xs font-bold uppercase tracking-[0.14em] text-[#7c8494]">{eyebrow}</p> : null}
        <h1 className="text-2xl font-bold tracking-[-0.035em] text-[#172033] md:text-[32px]">{title}</h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-6 text-[#667085] md:text-[15px]">{description}</p>
      </div>
      {action}
    </div>
  );
}
