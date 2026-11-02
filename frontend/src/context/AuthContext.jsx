import { createContext, useContext, useEffect, useState, useCallback } from "react";
import * as api from "../services/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(!!api.getToken());

  const logout = useCallback(() => { localStorage.removeItem("token"); setUser(null); setProfile(null); }, []);

  async function accept(res, email, password) {
    // Registration may not return a token; fall back to logging in.
    if (!res.access_token) res = await api.login(email, password);
    localStorage.setItem("token", res.access_token);
    setUser({ id: res.id, name: res.name, email: res.email });
    setProfile(await api.getProfile());
  }

  useEffect(() => {
    api.setUnauthorizedHandler(logout);
    if (!api.getToken()) return;
    Promise.all([api.getMe(), api.getProfile()])
      .then(([u, p]) => { setUser(u); setProfile(p); })
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setLoading(false));
  }, [logout]);

  const value = {
    user, profile, loading, logout,
    login: async (email, pw) => accept(await api.login(email, pw)),
    register: async (name, email, pw) => accept(await api.register(name, email, pw), email, pw),
    refreshProfile: async () => setProfile(await api.getProfile()),
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
