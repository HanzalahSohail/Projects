import React from "react";
const Button = ({ text, onClick, loading }) => {
  return (
    <button
      onClick={onClick}
      className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition"
      disabled={loading}
    >
      {loading ? "Processing..." : text}
    </button>
  );
};

export default Button;
 