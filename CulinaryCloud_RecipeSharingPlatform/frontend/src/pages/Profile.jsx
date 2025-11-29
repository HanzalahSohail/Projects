import React, { useState, useEffect } from "react";
import axios from "axios";
import profile_img from "../assets/profile_img.png";

function Profile() {
  const [userData, setUserData] = useState({
    id: null,
    profilePicture: "",
    username: "Username",
    bio: "User Bio",
    rank: "Prep Cook"
  });
  const [userRecipes, setUserRecipes] = useState([]); // for user's posts
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isEditingBio, setIsEditingBio] = useState(false);
  const [newBio, setNewBio] = useState("");
  
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/user/me`,
          {
            headers: { "x-auth-token": token }
          }
        );
        const fullName = 
        setUserData(prev => ({
          ...prev,
          id: response.data.id,
          profilePicture: response.data.profilePicture || profile_img,
          username: (
            `${response.data.fname || ""} ${response.data.lname || ""}`
          ).trim() || "User name",
          bio: response.data.bio || "No bio yet.",
          rank: response.data.rank || "Prep Cook"
        }));
      } catch (error) {
        console.error("Error fetching user data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, []);

  // Fetch recipes created by the authenticated user
  useEffect(() => {
    const fetchUserRecipes = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/recipes/myrecipes`,
          { headers: { "x-auth-token": token } }
        );
        setUserRecipes(response.data);
      } catch (error) {
        console.error("Error fetching user's recipes:", error);
      }
    };

    if (userData.id) {
      fetchUserRecipes();
    }
  }, [userData.id]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type and size
    if (!file.type.match('image.*')) {
      alert('Please select an image file');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    
    try {
      const formData = new FormData();
      formData.append('profilePicture', file);

      const response = await axios.put(
        `${import.meta.env.VITE_API_URL}/api/user/profile`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'x-auth-token': localStorage.getItem('token')
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(percentCompleted);
          }
        }
      );

      setUserData(prev => ({
        ...prev,
        id: response.data.id,
        profilePicture: response.data.profilePicture || profile_img,
        username: response.data.name || "Username",
        bio: response.data.bio || "No bio yet.",
        rank: response.data.rank || "Prep Cook"
      }));
      
      alert('Profile picture updated successfully!');
    } catch (error) {
      console.error('Upload failed:', error);
      alert(error.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  // Handler for deleting a recipe using your delete API
  const handleDelete = async (recipeId) => {
    const token = localStorage.getItem("token");
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/recipes/${recipeId}`, {
        headers: { "x-auth-token": token }
      });
      // Remove the deleted recipe from state
      setUserRecipes(prev => prev.filter(r => r._id !== recipeId));
      alert("Recipe deleted successfully!");
    } catch (error) {
      console.error("Error deleting recipe:", error);
      alert(error.response?.data?.error || "Failed to delete recipe");
    }
  };

  // Handler for editing: redirecting to edit page (adjust as needed)
  const handleEdit = (recipe) => {
    window.location.href = `/edit-recipe/${recipe._id}`;
  };

  const handleBioUpdate = async () => {
    if (!newBio.trim()) {
      alert("Bio cannot be empty");
      return;
    }
  
    try {
      const token = localStorage.getItem("token");
      const response = await axios.put(
        `${import.meta.env.VITE_API_URL}/api/user/bio`,
        { bio: newBio },
        {
          headers: {
            "Content-Type": "application/json",
            "x-auth-token": token
          }
        }
      );
  
      setUserData(prev => ({
        ...prev,
        bio: response.data.bio || newBio
      }));
      setIsEditingBio(false);
      setNewBio("");
    } catch (error) {
      console.error("Error updating bio:", error);
      alert(error.response?.data?.msg || "Failed to update bio");
    }
  };
  

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="profile-container">
      <div className="profile-top">
        <div className="profile-left">
          <img
            src={userData.profilePicture}
            alt="user_image"
            className="user-image"
            onError={(e) => { e.target.src = profile_img; }}
          />
          {isEditingBio ? (
          <div className="bio-edit-container">
            <input
              type="text"
              className="bio-input"
              placeholder="Enter your bio"
              value={newBio}
              onChange={(e) => setNewBio(e.target.value)}
            />
            <button className="bio-confirm-btn" onClick={handleBioUpdate}>
              Confirm
            </button>
          </div>
        ) : (
          <>
            <p className="user-bio">{userData.bio}</p>
            <button
              className="bio-edit-btn"
              onClick={() => {
                setIsEditingBio(true);
                setNewBio(userData.bio === "No bio yet." ? "" : userData.bio);
              }}
            >
              Change Bio
            </button>
          </>
        )}
        
        </div>
        <div className="profile-right">
          <p>{userData.username}</p>
          <p>{userData.rank}</p>
          <input
            type="file"
            id="profile-upload"
            accept="image/*"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
            disabled={uploading}
          />
          <label htmlFor="profile-upload" className="edit-profile">
            {uploading ? `Uploading... ${uploadProgress}%` : 'Change Photo'}
          </label>
        </div>
      </div>

      <div className="profile-bottom">
        <h2 className="post-heading">
          Posts <i className="fa-solid fa-image"></i>
        </h2>
        <div className="user-posts">
          {userRecipes.length > 0 ? (
            userRecipes.map((recipe) => (
              <div key={recipe._id} className="user-recipe-post">
                <img
                  src={recipe.image || '/default.jpg'}
                  alt={recipe.title}
                  className="user-recipe-posts"
                />
                <div className="recipe-details">
                  <p className="profile-post-title"><b>{recipe.title}</b></p>
                  <button className="profile-post-delete" onClick={() => handleDelete(recipe._id)}><i className="fa-solid fa-trash"></i></button>{/*changed by samad*/}
                </div>
              </div>
            ))
          ) : (
            <p>No posts yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default Profile;