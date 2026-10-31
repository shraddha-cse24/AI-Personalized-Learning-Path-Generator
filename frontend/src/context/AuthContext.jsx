import { createContext, useContext, useState } from "react";
import * as api from "../services/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));

  function save(u) { localStorage.setItem("user", JSON.stringify(u)); setUser(u); }

  const value = {
    user,
    async login(email, password) { save(await api.login(email, password)); },
    async register(name, email, password) { save(await api.register(name, email, password)); },
    logout() { localStorage.removeItem("user"); setUser(null); },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
