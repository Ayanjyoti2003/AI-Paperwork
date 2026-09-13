import Link from "next/link";
import { NavLinks } from "./nav-links";
import { Icon } from "./icons";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
      <aside className="hidden min-h-screen border-r border-[#e3e1db] bg-[#fbfaf7]/95 px-4 py-5 lg:flex lg:flex-col">
        <Link href="/dashboard" className="flex items-center gap-3 px-2">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#246bfd] text-white shadow-sm">
            <Icon name="file" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[15px] font-bold tracking-[-0.02em]">Paperwork Agent</p>
            <p className="text-xs text-[#8a91a0]">Personal admin workspace</p>
          </div>
        </Link>

        <Link href="/new-request" className="mt-8 flex items-center justify-center gap-2 rounded-xl bg-[#246bfd] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#175de6]">
          <Icon name="plus" className="h-4 w-4" />
          New request
        </Link>

        <div className="mt-5">
          <NavLinks />
        </div>

        <div className="mt-auto rounded-2xl border border-[#e8e6e0] bg-white p-3.5">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-[#e9edf5] text-xs font-bold text-[#526078]">AD</div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">Arion Dutta</p>
              <p className="truncate text-xs text-[#8a91a0]">Personal workspace</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[#e7e5df] bg-[#faf9f6]/90 px-4 backdrop-blur-xl md:px-7 lg:px-9">
          <Link href="/dashboard" className="flex items-center gap-2.5 lg:hidden">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#246bfd] text-white"><Icon name="file" className="h-4.5 w-4.5" /></div>
            <span className="font-bold">Paperwork Agent</span>
          </Link>
          <div className="hidden items-center gap-2 rounded-xl border border-[#e2e0da] bg-white px-3 py-2 text-sm text-[#8b93a2] md:flex md:w-[320px] lg:flex">
            <Icon name="search" className="h-4 w-4" />
            <span>Search applications and documents</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden rounded-full border border-[#e2e0da] bg-white px-3 py-1.5 text-xs font-medium text-[#667085] sm:block">Private workspace</div>
            <div className="grid h-9 w-9 place-items-center rounded-full bg-[#e9edf5] text-xs font-bold text-[#526078]">AD</div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1500px] px-4 py-5 md:px-7 md:py-7 lg:px-9 lg:py-9">{children}</main>
        <nav className="fixed inset-x-3 bottom-3 z-40 flex justify-around rounded-2xl border border-[#dedcd5] bg-white/95 p-2 shadow-xl backdrop-blur-xl lg:hidden">
          <Link href="/dashboard" className="p-2.5 text-[#667085]"><Icon name="home" /></Link>
          <Link href="/documents" className="p-2.5 text-[#667085]"><Icon name="file" /></Link>
          <Link href="/new-request" className="grid h-11 w-11 place-items-center rounded-xl bg-[#246bfd] text-white"><Icon name="plus" /></Link>
          <Link href="/applications" className="p-2.5 text-[#667085]"><Icon name="layers" /></Link>
          <Link href="/settings" className="p-2.5 text-[#667085]"><Icon name="settings" /></Link>
        </nav>
      </div>
    </div>
  );
}
