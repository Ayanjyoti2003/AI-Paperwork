export default function Loading() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="h-8 w-60 rounded-lg bg-[#e9e7e1]" />
      <div className="h-4 w-[420px] max-w-full rounded-lg bg-[#eeece7]" />
      <div className="grid gap-4 md:grid-cols-3"><div className="h-32 rounded-[22px] bg-[#ebe9e4]" /><div className="h-32 rounded-[22px] bg-[#ebe9e4]" /><div className="h-32 rounded-[22px] bg-[#ebe9e4]" /></div>
    </div>
  );
}
