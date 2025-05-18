
import React, { useState } from "react";
import axios from "axios";
import InputField from "../components/InputField";
import Button from "../components/Button";
import { useNavigate } from "react-router-dom";

export default function LoginScreen({ onAuthSuccess, toggleScreen, onGuestLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [generalError, setGeneralError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setGeneralError("");
    setEmailError("");
    setPasswordError("");

    // Simple front-end validation
    let hasError = false;
    if (!email.trim()) {
      setEmailError("Email is required");
      hasError = true;
    }
    if (!password.trim()) {
      setPasswordError("Password is required");
      hasError = true;
    }

    if (hasError) {
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/auth/login`,
        { email, password }
      );

      const { token, user } = response.data;
      localStorage.setItem("token", token);
      localStorage.setItem("user", JSON.stringify(user));

      onAuthSuccess();
      navigate("/dashboard");
    } catch (err) {
      if (err.response && err.response.data) {
        setGeneralError(err.response.data.msg);
      } else {
        setGeneralError("An error occurred. Please try again.");
      }
    }

    setLoading(false);
  };

  const handleGuestView = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    onGuestLogin();
    navigate("/dashboard");
  };

  return (
    <div className="w-full max-w-md bg-login_background p-6 rounded-lg shadow-md">
      <h2 className="text-center text-xl font-bold text-green-700 mb-1">
        Welcome to Culinary Cloud
      </h2>
      <h4 className="text-center italic text-sm text-tagline font-semibold text-login_caption">
        Inspiring Chefs, One Recipe at a Time!
      </h4>

      {generalError && (
        <p className="text-red-500 text-sm mt-2 mb-2">{generalError}</p>
      )}

      <form className="space-y-4 mt-6" onSubmit={handleLogin}>
        <InputField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setEmailError("");
          }}
          placeholder={emailError || undefined}
          className={
            emailError ? "placeholder-red-500 border-red-500" : "placeholder-gray-400"
          }
        />
        <InputField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            setPasswordError("");
          }}
          placeholder={passwordError || undefined}
          className={
            passwordError ? "placeholder-red-500 border-red-500" : "placeholder-gray-400"
          }
        />

        <button
          type="button"
          onClick={() =>
            (window.location.href =  `${import.meta.env.VITE_API_URL}/api/auth/google`)
          }
          className="w-full h-10 flex items-center justify-center bg-white border border-gray-300 text-gray-700 font-semibold rounded-md shadow-sm hover:bg-gray-100 transition duration-200"
        >
          <img
            src="https://www.svgrepo.com/show/475656/google-color.svg"
            alt="Google"
            className="w-5 h-5 mr-2"
          />
          Sign in with Google
        </button>

        <Button text="Sign in" loading={loading} onClick={handleLogin} />
      </form>

      <div className="flex items-center justify-between mt-6">
        <button
          onClick={toggleScreen}
          className="w-1/2 text-green-700 font-semibold hover:underline text-center"
        >
          Sign up
        </button>
        <span className="px-2 text-gray-400 font-medium select-none">OR</span>
        <button
          onClick={handleGuestView}
          className="w-1/2 text-blue-500 font-semibold hover:underline text-center"
        >
          Guest
        </button>
      </div>
    </div>
  );
}
