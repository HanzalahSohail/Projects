import { useEffect, useState } from 'react';
import axios from 'axios';
import Post from './Post';
import CommentModal from '../components/CommentModal';

function Recipe() {
  const [recipes, setRecipes] = useState([]);
  const [selectedPost, setSelectedPost] = useState(null);
  const [likes, setLikes] = useState({});
  const [userRatings, setUserRatings] = useState({});
  const [averageRatings, setAverageRatings] = useState({});
  const [activeCommentPostId, setActiveCommentPostId] = useState(null);
  const [likeLocks, setLikeLocks] = useState({});

  const regular = "fa-regular fa-star";
  const solid = "fa-solid fa-star";

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('token');
      try {
        const recipeRes = await axios.get(`${import.meta.env.VITE_API_URL}/api/recipes`, {
          headers: { 'x-auth-token': token || '' },
        });
        const likedRes = await axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/liked`, {
          headers: { 'x-auth-token': token || '' },
        });

        let userRatedRes = { data: [] };
        try {
          userRatedRes = await axios.get(`${import.meta.env.VITE_API_URL}/api/recipes/user-ratings`, {
            headers: { 'x-auth-token': token || '' },
          });
        } catch (error) {
          console.warn("Warning: Could not load user ratings, proceeding without it.");
        }

        // Transform data to match StartCooking expectations
        const transformedRecipes = recipeRes.data.map(recipe => ({
          ...recipe,
          name: recipe.title, // Map title to name if needed
          steps: recipe.steps || [] // Ensure steps exists
        }));
        setRecipes(transformedRecipes);

        const likedMap = {};
        likedRes.data.forEach(id => likedMap[id] = true);
        setLikes(likedMap);

        const avgRatingMap = {};
        recipeRes.data.forEach(recipe => {
          if (recipe.ratings && recipe.ratings.length > 0) {
            const sum = recipe.ratings.reduce((acc, r) => acc + r.value, 0);
            avgRatingMap[recipe._id] = sum / recipe.ratings.length;
          } else {
            avgRatingMap[recipe._id] = 0;
          }
        });
        setAverageRatings(avgRatingMap);

        const userRatingMap = {};
        userRatedRes.data.forEach(rating => {
          userRatingMap[rating.recipeId] = rating.rating;
        });
        setUserRatings(userRatingMap);

      } catch (err) {
        console.error("Error fetching recipes or likes:", err);
      }
    };

    fetchData();
  }, []);

  const handleLikeToggle = async (id) => {
    if (likeLocks[id]) return;

    const token = localStorage.getItem('token');
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
        headers: { 'x-auth-token': token || '' },
      });
    } catch (err) {
      console.error("Error liking recipe:", err);
      setLikes(prev => ({ ...prev, [id]: isLiked }));
      setRecipes(prev =>
        prev.map(recipe =>
          recipe._id === id
            ? { ...recipe, likeCount: recipe.likeCount + (isLiked ? 1 : -1) }
            : recipe
        )
      );
    } finally {
      setLikeLocks(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleStarClick = async (id, index) => {
    const newRating = index + 1;

    setUserRatings(prev => ({ ...prev, [id]: newRating }));

    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/recipes/${id}/rate`,
        { rating: newRating },
        { headers: { 'x-auth-token': token || '' } }
      );
      const avg = res.data.averageRating ?? 0;
      setAverageRatings(prev => ({ ...prev, [id]: avg }));
    } catch (err) {
      console.error("Error rating recipe:", err);
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
    <>
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
                <h4 id="user_name">{recipe.user?.name || "Unknown"}</h4>
                <h4 id="user_badge">{recipe.user?.rank || "Prep Cook"}</h4>
              </div>
            </div>
            <img
              src={recipe.image || '/default.jpg'}
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
                <span style={{ marginLeft: "10px", fontSize: "14px", color: "#444" }}>
                  {recipe.commentCount || 0}
                </span>
              </div>
              <div className="ratings">
                {[...Array(5)].map((_, index) => {
                  const userRating = userRatings[recipe._id];
                  return (
                    <i
                      key={index}
                      className={index < (userRating || 0) ? solid : regular}
                      onClick={() => handleStarClick(recipe._id, index)}
                      style={{ cursor: "pointer" }}
                    />
                  );
                })}
              </div>
            </div>
            <div className="post-number">
              <p><b>{recipe.likeCount} {recipe.likeCount === 1 ? "like" : "likes"}</b></p>
              <p><b>{(averageRatings[recipe._id] || 0).toFixed(1)} rating</b></p>
            </div>
            <p className="post-description">
              <b>{recipe.title}</b> {recipe.caption?.slice(0, 100)}...
              <button
                className="learn-more"
                onClick={() => handleLearnMoreClick(recipe)}
                disabled={!recipe.steps || recipe.steps.length === 0}
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
    </>
  );
}

export default Recipe;