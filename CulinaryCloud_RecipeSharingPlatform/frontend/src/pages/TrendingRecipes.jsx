import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import Post from './Post';
import CommentModal from '../components/CommentModal';

export default function TrendingRecipes({ setPost, setProfile, onLogout }) {
  const [recipes, setRecipes] = useState([]);
  const [likes, setLikes] = useState({});
  const [stars, setStars] = useState({});
  const [selectedPost, setSelectedPost] = useState(null);
  const [activeCommentPostId, setActiveCommentPostId] = useState(null);
  const [likeLocks, setLikeLocks] = useState({});
  const navigate = useNavigate();

  const solid = "fa-solid fa-star";
  const regular = "fa-regular fa-star";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem("token");

        const [recipeRes, likedRes] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/trending`, {
            headers: { 'x-auth-token': token || '' }
          }),
          axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/liked`, {
            headers: { 'x-auth-token': token || '' }
          }),
        ]);

        setRecipes(recipeRes.data);
        const likedMap = {};
        likedRes.data.forEach(id => likedMap[id] = true);
        setLikes(likedMap);

      } catch (err) {
        console.error("Error fetching trending recipes or likes:", err);
      }
    };

    fetchData();
  }, []);

  const handleLikeToggle = async (id) => {
    if (likeLocks[id]) return;
    const token = localStorage.getItem("token");
    const isLiked = likes[id];
    setLikeLocks(prev => ({ ...prev, [id]: true }));
    setLikes(prev => ({ ...prev, [id]: !isLiked }));
    setRecipes(prev =>
      prev.map(recipe =>
        recipe._id === id
          ? { ...recipe, likeCount: recipe.likeCount + (isLiked ? -1 : 1) }
          : recipe
      )
    );

    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/recipes/${id}/like`, {}, {
        headers: { 'x-auth-token': token || '' }
      });
    } catch (err) {
      console.error("Error liking recipe:", err);
      setLikes(prev => ({ ...prev, [id]: isLiked }));
    } finally {
      setLikeLocks(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleStarClick = (id, index) => {
    setStars(prev => ({
      ...prev,
      [id]: (index + 1 === prev[id] ? index : index + 1)
    }));
  };

  const handleLearnMoreClick = (recipe) => {
    if (selectedPost?._id === recipe._id) {
      setSelectedPost(null);
    } else {
      setSelectedPost(recipe);
    }
  };

  return (
  
          <div className="middle-part-trending" style={{ paddingLeft: '20px' }}>
            <div className="trending-recipes-title-container">
                <h1 className="trending-recipes-title">Trending Recipes</h1>
            </div>
  
            {recipes.map((recipe) => (
              <div key={recipe._id}>
                <div className="post_container">
                  <div className="user_profile">
                    {recipe.user?.profilePicture ? (
                      <img
                        src={recipe.user.profilePicture}
                        alt={recipe.user.name || "Profile"}
                        className="profile-pic"
                      />
                    ) : (
                      <i className="fa-solid fa-user" />
                    )}
                    <div className="user_info">
                      <h4>{recipe.user?.name || "Unknown"}</h4>
                      <h4 id="user_badge">{recipe.user?.rank || "Prep Cook"}</h4>
                    </div>
                  </div>
  
                  <img src={recipe.image} alt="Food" className="recipe-image" />
  
                  <div className="post_interations">
                    <div className="like_comment">
                      <i
                        className={likes[recipe._id] ? "fa-solid fa-heart" : "fa-regular fa-heart"}
                        onClick={() => handleLikeToggle(recipe._id)}
                      />
                      <i
                        className="fa-regular fa-comment"
                        onClick={() => setActiveCommentPostId(recipe._id)}
                      />
                      <span style={{ fontSize: '14px', marginLeft: '5px' }}>
                        {recipe.commentCount || 0}
                      </span>
                    </div>
  
                    <div className="ratings">
                      {[...Array(5)].map((_, index) => (
                        <i
                          key={index}
                          className={index < (stars[recipe._id] || 0) ? solid : regular}
                          onClick={() => handleStarClick(recipe._id, index)}
                        />
                      ))}
                    </div>
                  </div>
  
                  <div className="post-number">
                    <p><b>{recipe.likeCount || 0} likes</b></p>
                    <p><b>{recipe.averageRating?.toFixed(1) || "0.0"} rated</b></p>
                  </div>
  
                  <p className="post-description">
                    <b>{recipe.title}</b> {recipe.caption?.slice(0, 100)}...
                    <button
                      className="learn-more"
                      onClick={() => handleLearnMoreClick(recipe)}
                    >
                      {selectedPost?._id === recipe._id ? 'Go Back' : 'Learn More'}
                    </button>
                  </p>
                </div>
  
                {selectedPost?._id === recipe._id && (
                  <div className="expanded-post">
                    <Post recipe={selectedPost} />
                  </div>
                )}
              </div>
            ))}
  
            {activeCommentPostId && (
              <CommentModal
                recipeId={activeCommentPostId}
                onClose={() => setActiveCommentPostId(null)}
              />
            )}
          </div>
  );
}   