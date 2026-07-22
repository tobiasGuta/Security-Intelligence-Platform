import { redirect } from "next/navigation";
import { apiGet } from "./api-client";

export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Fetches the current authenticated user from the backend.
 * Returns null if the request fails (not authenticated).
 * For use in Server Components only.
 */
export async function getServerSession(): Promise<User | null> {
  try {
    return await apiGet<User>("/auth/me");
  } catch {
    return null;
  }
}

/**
 * Requires authentication. Redirects to /login if not authenticated.
 * For use in Server Components only.
 */
export async function requireAuth(): Promise<User> {
  const user = await getServerSession();
  if (!user) {
    redirect("/login");
  }
  return user;
}
