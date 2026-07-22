import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LoginPage from "@/app/(auth)/login/page";
import { CSRFProvider } from "@/contexts/csrf-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/login",
}));

// Mock api-client to avoid actual fetch calls
vi.mock("@/lib/api-client", () => ({
  apiGet: vi.fn().mockRejectedValue(new Error("Not authenticated")),
  apiPost: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  CsrfError: class CsrfError extends Error {
    constructor() {
      super("CSRF");
    }
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <CSRFProvider>{children}</CSRFProvider>
      </QueryClientProvider>
    );
  };
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the login form with username and password fields", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>
    );

    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders the sign in button", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>
    );

    expect(
      screen.getByRole("button", { name: /sign in/i })
    ).toBeInTheDocument();
  });

  it("renders the platform title", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>
    );

    expect(screen.getByText(/intel platform/i)).toBeInTheDocument();
  });
});
