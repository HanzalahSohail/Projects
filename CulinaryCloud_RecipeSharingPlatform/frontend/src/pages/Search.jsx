// src/Search.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; 

function Search() {
  const [searchTerm, setSearchTerm] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const navigate = useNavigate(); 

  useEffect(() => {
    if (searchTerm.trim().length < 2) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(() => {
      fetch(`${import.meta.env.VITE_API_URL}/api/recipes/search?ingredient=${encodeURIComponent(searchTerm)}`)
        .then((res) => res.json())
        .then((data) => setSuggestions(data))
        .catch((err) => {
          console.error('Error fetching suggestions:', err);
          setSuggestions([]);
        });
    }, 500);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleSuggestionClick = (recipe) => {
    navigate(`/home/search-results?recipeId=${recipe._id}`);
  };

  return (
    <div className="search-container">
      <div className="search-field-div">
        <input
          type="text"
          placeholder="Search by recipe, cuisine, or author"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-field"
        />
      </div>
      {suggestions.length > 0 && (
        <ul className="suggestions-list" style={{ listStyleType: 'none', padding: 0 }}>
          {suggestions.map((recipe) => (
            <li
              key={recipe._id}
              onClick={() => handleSuggestionClick(recipe)}
              style={{ cursor: 'pointer', padding: '8px', borderBottom: '1px solid #ccc' }}
            >
              {recipe.title} — <em>{recipe.categories.join(', ')}</em>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default Search;     