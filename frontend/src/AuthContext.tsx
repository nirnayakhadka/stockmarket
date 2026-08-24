import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import {
  login as apiLogin,
  setToken,
  clearToken,
  getToken,
} from "./api/client";
import type { User } from "./types";

interface ApiCurrentUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: "admin" | "analyst" | "viewer";
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function mapUser(u: ApiCurrentUser): User {
  return {
    id: u.id,
    name: u.full_name || u.username,
    email: u.email,
    role: u.role,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount: if a token is already stored (e.g. page refresh), try to
  // restore the session by re-decoding what login gave us. Simplest
  // approach here: store the mapped user alongside the token rather than
  // re-fetching — avoids needing a separate GET /api/auth/me endpoint.
  useEffect(() => {
    const token = getToken();
    const stored = sessionStorage.getItem("nepse_auth_user");
    if (token && stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        clearToken();
      }
    }
    setLoading(false);
  }, []);

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password);
    setToken(res.access_token);
    const mapped = mapUser(res.user);
    sessionStorage.setItem("nepse_auth_user", JSON.stringify(mapped));
    setUser(mapped);
  }

  function logout() {
    clearToken();
    sessionStorage.removeItem("nepse_auth_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
