"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  ShieldAlert,
  Eye,
  Bell,
  Database,
  Settings,
  LogOut,
  Moon,
  Sun,
  ChevronRight,
} from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { apiPost } from "@/lib/api-client";
import type { User } from "@/lib/auth";

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Intelligence",
    items: [
      { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      {
        title: "Vulnerability Explorer",
        href: "/vulnerabilities",
        icon: ShieldAlert,
      },
      { title: "Watchlists", href: "/watchlists", icon: Eye },
      { title: "Alerts", href: "/alerts", icon: Bell },
    ],
  },
  {
    title: "Administration",
    items: [
      { title: "Data Sources", href: "/admin/sources", icon: Database },
      { title: "Settings", href: "/admin/settings", icon: Settings },
    ],
  },
];

export function Sidebar({ user }: { user: User }) {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await apiPost("/auth/logout");
    } catch {
      // ignore errors — logout best-effort
    } finally {
      router.push("/login");
      router.refresh();
    }
  };

  const isActive = (href: string) =>
    href === "/dashboard"
      ? pathname === href
      : pathname.startsWith(href);

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-card flex flex-col">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-border">
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 font-semibold text-sm tracking-tight"
        >
          <div className="w-7 h-7 bg-primary/10 rounded-lg flex items-center justify-center">
            <ShieldAlert className="h-4 w-4 text-primary" />
          </div>
          <span>Intel Platform</span>
        </Link>
        <button
          className="relative p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Notifications"
        >
          <Bell className="h-4 w-4" />
          {/* Placeholder unread dot — wired in Milestone 6 */}
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-blue-500 opacity-0" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {navSections.map((section) => (
          <div key={section.title} className="mb-4">
            <p className="px-4 mb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
              {section.title}
            </p>
            <div className="space-y-0.5 px-2">
              {section.items.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-2.5 py-2 rounded-md text-sm transition-colors group",
                      active
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <item.icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        active ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                      )}
                    />
                    <span className="flex-1 truncate">{item.title}</span>
                    {active && (
                      <ChevronRight className="h-3 w-3 text-primary opacity-60" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-3 space-y-1">
        {/* User info + theme toggle */}
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-xs font-semibold text-white shrink-0">
            {user.username[0]?.toUpperCase()}
          </div>
          <span className="text-sm font-medium flex-1 truncate">
            {user.username}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0"
            onClick={() =>
              setTheme(resolvedTheme === "dark" ? "light" : "dark")
            }
            title="Toggle theme"
          >
            {resolvedTheme === "dark" ? (
              <Sun className="h-3.5 w-3.5" />
            ) : (
              <Moon className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-2.5 py-2 rounded-md text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
