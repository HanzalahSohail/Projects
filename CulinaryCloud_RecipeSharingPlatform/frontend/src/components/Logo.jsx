import React from "react";
import logo from '../assets/logo.jpg';

const Logo = () => {
  return (
    <div className="flex justify-center mb-6">
      <img src={logo} alt="App Logo" className="h-12" />
    </div>
  );
};

export default Logo;
 