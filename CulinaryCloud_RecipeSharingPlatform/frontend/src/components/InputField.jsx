
import React from "react";

const InputField = ({ label, type, value, onChange, placeholder, className = "" }) => {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder || `Enter your ${label.toLowerCase()}`}
        className={`mt-1 block w-full px-4 py-2 border rounded-lg focus:ring-green-500 focus:border-green-500 ${className}`}
      />
    </div>
  );
};

export default InputField;