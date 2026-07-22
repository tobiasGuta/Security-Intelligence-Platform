// Minimal dropdown-menu implementation without @radix-ui dependency.
// Will be upgraded with @radix-ui/react-dropdown-menu in a later milestone.
import * as React from "react";
import { cn } from "@/lib/utils";

const DropdownMenu = ({ children }: { children: React.ReactNode }) => (
  <div className="relative inline-block">{children}</div>
);

const DropdownMenuTrigger = ({
  children,
}: {
  children: React.ReactNode;
  asChild?: boolean;
}) => <>{children}</>;

const DropdownMenuContent = ({
  children,
  className,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  align = "start",
}: {
  children: React.ReactNode;
  className?: string;
  align?: "start" | "end" | "center";
}) => (
  <div
    className={cn(
      "z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
      className,
    )}
  >
    {children}
  </div>
);

const DropdownMenuItem = ({
  children,
  className,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) => (
  <div
    role="menuitem"
    tabIndex={0}
    onClick={onClick}
    onKeyDown={(e) => e.key === "Enter" && onClick?.()}
    className={cn(
      "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
      className,
    )}
  >
    {children}
  </div>
);

const DropdownMenuSeparator = ({ className }: { className?: string }) => (
  <div className={cn("-mx-1 my-1 h-px bg-border", className)} />
);

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
};
