"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, type IconName } from "./icons";

const items: { href: string; label: string; icon: IconName }[] = [
  { href: "/dashboard", label: "Dashboard", icon: "home" },
  { href: "/documents", label: "My documents", icon: "file" },
  { href: "/applications", label: "Applications", icon: "layers" },
  { href: "/settings", label: "Settings", icon: "settings" },
];

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="space-y-1.5">
      {items.map((item) => {
        const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
        return (
          <Link key={item.href} href={item.href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${active ? "bg-[#edf4ff] text-[#1756cf]" : "text-[#667085] hover:bg-[#f1f0ec] hover:text-[#253044]"}`}>
            <Icon name={item.icon} className="h-[18px] w-[18px]" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
