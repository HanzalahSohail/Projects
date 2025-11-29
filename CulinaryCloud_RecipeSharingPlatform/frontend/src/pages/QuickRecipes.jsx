
import { useEffect, useState } from 'react';
import axios from 'axios';
import Post from './Post';
import CommentModal from '../components/CommentModal';

export default function QuickRecipes() {
  const [recipes, setRecipes] = useState([]);
  const [likes, setLikes] = useState({});
  const [stars, setStars] = useState({});
  const [selectedPost, setSelectedPost] = useState(null);
  const [activeCommentPostId, setActiveCommentPostId] = useState(null);
  const [likeLocks, setLikeLocks] = useState({});

  const solid = "fa-solid fa-star";
  const regular = "fa-regular fa-star";

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem("token") || "";
      try {
        const [recipeRes, likedRes, userRatedRes] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/quick`, {
            headers: { 'x-auth-token': token }
          }),
          axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/liked`, {
            headers: { 'x-auth-token': token }
          }),
          axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/user-ratings`, {
            headers: { 'x-auth-token': token }
          })
        ]);

        // set recipes
        setRecipes(recipeRes.data);

        // build likes map
        const likedMap = {};
        likedRes.data.forEach(id => likedMap[id] = true);
        setLikes(likedMap);

        // build initial stars map from existing ratings
        const ratingMap = {};
        userRatedRes.data.forEach(({ recipeId, rating }) => {
          ratingMap[recipeId] = rating;
        });
        setStars(ratingMap);
      } catch (err) {
        console.error("Error fetching quick recipes data:", err);
      }
    };

    fetchData();
  }, []);

  const handleLikeToggle = async (id) => {
    if (likeLocks[id]) return;
    const token = localStorage.getItem("token") || "";
    const isLiked = likes[id];

    // optimistic UI update
    setLikeLocks(prev => ({ ...prev, [id]: true }));
    setLikes(prev => ({ ...prev, [id]: !isLiked }));
    setRecipes(prev =>
      prev.map(r =>
        r._id === id
          ? { ...r, likeCount: r.likeCount + (isLiked ? -1 : 1) }
          : r
      )
    );

    try {
      await axios.post(
        `${import.meta.env.VITE_API_URL}/api/recipes/${id}/like`,
        {},
        { headers: { 'x-auth-token': token } }
      );
    } catch (err) {
      console.error("Error liking recipe:", err);
      // rollback on failure
      setLikes(prev => ({ ...prev, [id]: isLiked }));
      setRecipes(prev =>
        prev.map(r =>
          r._id === id
            ? { ...r, likeCount: r.likeCount + (isLiked ? 1 : -1) }
            : r
        )
      );
    } finally {
      setLikeLocks(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleStarClick = async (id, index) => {
    const newRating = index + 1;
    // optimistic update
    setStars(prev => ({ ...prev, [id]: newRating }));

    try {
      const token = localStorage.getItem("token") || "";
      await axios.post(
        `${import.meta.env.VITE_API_URL}/api/recipes/${id}/rate`,
        { rating: newRating },
        { headers: { 'x-auth-token': token } }
      );
    } catch (err) {
      console.error("Error rating recipe:", err);
      // rollback on failure
      setStars(prev => ({ ...prev, [id]: 0 }));
    }
  };

  const handleLearnMoreClick = (recipe) => {
    if (selectedPost?._id === recipe._id) {
      setSelectedPost(null);
    } else {
      setSelectedPost(recipe);
    }
  };

  return (
    <div className="middle-part-quick">
      <h1 className="quick-recipes-title">Quick Recipes</h1>

      {recipes.map(recipe => (
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

            <img
              src={recipe.image}
              alt="Food"
              className="recipe-image"
            />

            <div className="post_interations">
              <div className="like_comment">
                <i
                  className={likes[recipe._id] ? "fa-solid fa-heart" : "fa-regular fa-heart"}
                  onClick={() => handleLikeToggle(recipe._id)}
                  style={{ cursor: "pointer" }}
                />
                <i
                  className="fa-regular fa-comment"
                  onClick={() => setActiveCommentPostId(recipe._id)}
                  style={{ cursor: "pointer" }}
                />
                <span style={{ marginLeft: 8, fontSize: 14, color: "#444" }}>
                  {recipe.commentCount || 0}
                </span>
              </div>
              <div className="ratings">
                {[...Array(5)].map((_, idx) => (
                  <i
                    key={idx}
                    className={idx < (stars[recipe._id] || 0) ? solid : regular}
                    onClick={() => handleStarClick(recipe._id, idx)}
                    style={{ cursor: "pointer" }}
                  />
                ))}
              </div>
            </div>

            <div className="post-number">
              <p>
                <b>
                  {recipe.likeCount || 0}{" "}
                  {recipe.likeCount === 1 ? "like" : "likes"}
                </b>
              </p>
              <p>
                <b>{(stars[recipe._id] || 0).toFixed(1)} rating</b>
              </p>
            </div>

            <p className="post-description">
              <b>{recipe.title}</b> {recipe.caption?.slice(0, 100)}…
              <button
                className="learn-more"
                onClick={() => handleLearnMoreClick(recipe)}
              >
                {selectedPost?._id === recipe._id ? "Go Back" : "Learn More"}
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