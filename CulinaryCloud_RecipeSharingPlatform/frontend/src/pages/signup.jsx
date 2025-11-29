import React, { useState } from "react";
import axios from "axios";
import InputField from "../components/InputField";
import Button from "../components/Button";

export default function SignupScreen({ onAuthSuccess, toggleScreen }) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profilePicture, setProfilePicture] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [bio, setBio] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState("");


  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setProfilePicture(e.target.files[0]);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setEmailError("");
    setPasswordError("");
    setConfirmPasswordError("");

    let hasErrors = false;

    if (!email.trim()) {
      setEmailError("Email is required");
      hasErrors = true;
    }
    if (!password.trim()) {
      setPasswordError("Password is required");
      hasErrors = true;
    }
    if (!confirmPassword.trim()) {
      setConfirmPasswordError("Confirm Password is required");
      hasErrors = true;
    }
  
    if (hasErrors) {
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
      setLoading(false);
      return;
    }
    
    // 2) must have upper + lower + special
    const complexity = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).+$/;

    if (!complexity.test(password)) {
      setPasswordError(
        "Password must include uppercase, lowercase & a special character."
      );
      setLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      setLoading(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append("firstName", firstName);
      formData.append("lastName", lastName);
      formData.append("email", email);
      formData.append("password", password);
      if (profilePicture) {
        formData.append("profilePicture", profilePicture);
      }
      if (bio) {
        formData.append("bio", bio);
      }
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/auth/register`,
        // ${import.meta.env.VITE_API_URL}/api/recipes/${recipeId}
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      const { token } = response.data;
      localStorage.setItem("token", token);

      onAuthSuccess();
    } catch (err) {
      if (err.response && err.response.data) {
        setError(err.response.data.msg);
      } else {
        setError("An error occurred. Please try again.");
      }
    }
    setLoading(false);
  };

  return (
    <div className="mt-4 mb-4 w-full max-w-md bg-login_background p-6 rounded-lg shadow-md">
      <h2 className="text-center text-2xl font-bold text-green-700 mb-4">
        Create Account
      </h2>

      {error && <p className="text-red-500 text-sm mb-2">{error}</p>}

      <form className="space-y-4" onSubmit={handleSignup}>
        <InputField
          label="First Name"
          type="text"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
        />
        <InputField
          label="Last Name"
          type="text"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
        />
        <InputField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setEmailError(""); // Clear error on input change
          }}
          placeholder={emailError || undefined}
          className={emailError ? "placeholder-red-500 border-red-500" : "placeholder-gray-400"}
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
          className={passwordError ? "placeholder-red-500 border-red-500" : "placeholder-gray-400"}
        />
        {passwordError && (
          <p className="text-red-500 text-sm mt-1">{passwordError}</p>
        )}
        <InputField
          label="Confirm Password"
          type="password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            setConfirmPasswordError("");
          }}
          placeholder={confirmPasswordError || undefined}
          className={confirmPasswordError ? "placeholder-red-500 border-red-500" : "placeholder-gray-400"}
        />
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">
            Profile Picture
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="mt-1 block w-full"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700">Bio</label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            rows={4}
            placeholder="Tell us a bit about yourself..."
          />
        </div>

        <Button text="Sign up" loading={loading} onClick={handleSignup} />
      </form>

      <div className="flex justify-between text-sm text-gray-600 mt-4">
        <button
          onClick={toggleScreen}
          className="text-green-700 font-semibold hover:underline"
        >
          Already have an account? Log in
        </button>
      </div>
    </div>
  );
}