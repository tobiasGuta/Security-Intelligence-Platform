import * as React from "react";
import { cn } from "@/lib/utils";

const TooltipProvider = ({ children }: { children: React.ReactNode }) => (
  <>{children}</>
);

const Tooltip = ({ children }: { children: React.ReactNode }) => (
  <div className="group relative inline-flex">{children}</div>
);

const TooltipTrigger = ({ children }: { children: React.ReactNode }) => (
  <>{children}</>
);

const TooltipContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { side?: "top" | "bottom" | "left" | "right" }
>
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  (({ className, side = "top", ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 hidden group-hover:block overflow-hidden rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md whitespace-nowrap",
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = "TooltipContent";

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };
