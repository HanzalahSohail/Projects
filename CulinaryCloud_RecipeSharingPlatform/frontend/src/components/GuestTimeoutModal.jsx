import React from "react";

export default function GuestTimeoutModal({ onLogin, onSignup }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex justify-center items-center z-50">
      <div className="bg-white p-6 rounded-lg shadow-lg text-center max-w-sm">
        <h2 className="text-xl font-semibold text-green-700 mb-2">
          EXPLORE MORE!
        </h2>
        <p className="mb-4">
          Please log in or sign up to continue using Culinary Cloud.
        </p>
        <div className="space-x-4">
          <button
            onClick={onLogin}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Log In
          </button>
          <button
            onClick={onSignup}
            className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400"
          >
            Sign Up
          </button>
        </div>
      </div>
    </div>
  );
}
 