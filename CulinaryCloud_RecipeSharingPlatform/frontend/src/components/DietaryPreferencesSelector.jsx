// components/DietaryPreferencesSelector.jsx
import React from 'react';

export default function DietaryPreferencesSelector({ 
  allowedCategories, 
  selectedCategories, 
  onCategoryChange 
}) {
  return (
    <div>
      <p className="block text-sm font-medium text-gray-700 mb-2">
        Dietary Preferences (Select up to 10)
      </p>
      <div className="max-h-48 overflow-y-auto border p-2 rounded-lg">
        {allowedCategories.map((category) => (
          <label key={category} className="flex items-center space-x-2">
            <input
              type="checkbox"
              value={category}
              checked={selectedCategories.includes(category)}
              onChange={onCategoryChange}
            />
            <span>{category}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
 