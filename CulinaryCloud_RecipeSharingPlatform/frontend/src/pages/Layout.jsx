// src/pages/Layout.jsx
import React, { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import Navbar from "../Navbar";
import GuestTimeoutModal from "../components/GuestTimeoutModal";

export default function Layout({ isGuest, onLogout }) {
  const [showGuestModal, setShowGuestModal] = useState(false);

  useEffect(() => {
    if (isGuest) {
      const timer = setTimeout(() => {
        setShowGuestModal(true);
      }, 30000);
      return () => clearTimeout(timer);
    }
  }, [isGuest]);

  return (
    <div className="original-page">
      <div className="screen">
        <div className="page">
          <div className="left-part">
            <Navbar onLogout={onLogout} />
          </div>
          <div className="middle-part">
            <Outlet />
          </div>
        </div>
      </div>
      {showGuestModal && isGuest && (
        <GuestTimeoutModal
          onLogin={() => (window.location.href = "/")}
          onSignup={() => (window.location.href = "/")}
        />
      )}
    </div>
  );
}
 