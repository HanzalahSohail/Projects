import React from 'react';
import { useNavigate } from 'react-router-dom';

function Navbar({ onLogout }) {
  const navigate = useNavigate();

  return (
    <div className="navbar">
      <h2 className="navbar-name">CulinaryCloud</h2>
      <div className="sites-container">
        <div className="sites" onClick={() => navigate("/home")}>
          <i className="fa-solid fa-house"></i>
          <h3>Home</h3>
        </div>
        <div className="sites" onClick={() => navigate("/home/create")}>
          <i className="fa-solid fa-square-plus"></i>
          <h3>Create</h3>
        </div>
        <div className="sites" onClick={() => navigate("/home/trending")}>
          <i className="fa-solid fa-fire"></i>
          <h3>Trending</h3>
        </div>
        <div className="sites" onClick={() => navigate("/home/quick-recipes")}>
          <i className="fa-solid fa-forward-fast"></i>
          <h3>Quick</h3>
        </div>
        <div className="sites" onClick={() => navigate("/home/profile")}>
          <i className="fa-solid fa-user"></i>
          <h3>Profile</h3>
        </div>
        {onLogout && (
          <div className="sites-logout" onClick={onLogout}>
            <i className="fa-solid fa-sign-out"></i>
            <h3>Logout</h3>
          </div>
        )}
      </div>
    </div>
  );
}

export default Navbar;
 