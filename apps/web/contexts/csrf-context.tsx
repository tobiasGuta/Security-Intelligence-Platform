"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiGet } from "@/lib/api-client";

interface CSRFContextType {
  csrfToken: string | null;
  setCsrfToken: (token: string) => void;
}

const CSRFContext = createContext<CSRFContextType | undefined>(undefined);

/**
 * Provides the CSRF token to the component tree.
 * - Token is stored in React state (memory only — never in cookies or localStorage).
 * - Also mirrored on window.__CSRF_TOKEN__ so api-client.ts can access it without prop drilling.
 * - On mount, attempts to fetch the token from /api/v1/auth/csrf to restore across page refreshes.
 */
export function CSRFProvider({ children }: { children: React.ReactNode }) {
  const [csrfToken, setCsrfTokenState] = useState<string | null>(null);

  const setCsrfToken = useCallback((token: string) => {
    setCsrfTokenState(token);
    if (typeof window !== "undefined") {
      (window as Window & { __CSRF_TOKEN__?: string }).__CSRF_TOKEN__ = token;
    }
  }, []);

  useEffect(() => {
    // Attempt to restore CSRF token if a session cookie is already present.
    // If not authenticated, the request will fail silently.
    apiGet<{ csrf_token: string }>("/auth/csrf")
      .then((data) => {
        if (data.csrf_token) {
          setCsrfToken(data.csrf_token);
        }
      })
      .catch(() => {
        // Not authenticated — ignore
      });
  }, [setCsrfToken]);

  return (
    <CSRFContext.Provider value={{ csrfToken, setCsrfToken }}>
      {children}
    </CSRFContext.Provider>
  );
}

export function useCSRF(): CSRFContextType {
  const context = useContext(CSRFContext);
  if (context === undefined) {
    throw new Error("useCSRF must be used within a CSRFProvider");
  }
  return context;
}
