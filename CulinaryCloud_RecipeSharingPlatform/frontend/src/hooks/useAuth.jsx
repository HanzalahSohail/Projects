import { useState } from "react";

export function useAuth() {
  const [user, setUser] = useState(null);
  
  const login = async (email, password) => {
    console.log("Authenticating user:", email);
    // Call backend API when ready
    setUser({ email });
  };

  return { user, login };
}
 