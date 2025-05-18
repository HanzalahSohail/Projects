
import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import Post from './Post';
import CommentModal from '../components/CommentModal';

export default function SearchResults() {
  const location = useLocation();

  // State
  const [recipes, setRecipes]               = useState([]);
  const [likes, setLikes]                   = useState({});
  const [userRatings, setUserRatings]       = useState({});
  const [averageRatings, setAverageRatings] = useState({});
  const [selectedPost, setSelectedPost]     = useState(null);
  const [activeCommentPostId, setActiveCommentPostId] = useState(null);
  const [likeLocks, setLikeLocks]           = useState({});

  const solid   = "fa-solid fa-star";
  const regular = "fa-regular fa-star";

  // Pull query parameters
  const params     = new URLSearchParams(location.search);
  const recipeId   = params.get('recipeId');
  const ingredient = params.get('ingredient');
  const cuisine    = params.get('cuisine');

  // Build the header string
  const getSearchHeader = () => {
    if (recipeId && recipes[0]?.title) {
      return `Search Results: ${recipes[0].title}`;
    }
    const parts = [];
    if (ingredient) parts.push(ingredient);
    if (cuisine)    parts.push(cuisine);
    return parts.length
      ? `Search Results: ${parts.join(', ')}`
      : 'Search Results: All Recipes';
  };

  // Build the URL we'll fetch
  const buildFetchUrl = () => {
    if (recipeId) {
      return `${import.meta.env.VITE_API_URL}/api/recipes/${recipeId}`;
    }
    let url = `${import.meta.env.VITE_API_URL}/api/recipes/search?`;
    if (ingredient) url += `ingredient=${encodeURIComponent(ingredient)}&`;
    if (cuisine)    url += `cuisine=${encodeURIComponent(cuisine)}`;
    return url;
  };

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('token') || '';
      try {
        // 1) recipes (array or single)
        const recipesRes = await axios.get(buildFetchUrl(), {
          headers: { 'x-auth-token': token }
        });
        const data = Array.isArray(recipesRes.data)
          ? recipesRes.data
          : [recipesRes.data];
        setRecipes(data);

        // 2) liked IDs
        const likedRes = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/recipes/liked`,
          { headers: { 'x-auth-token': token } }
        );
        const likedMap = {};
        likedRes.data.forEach(id => (likedMap[id] = true));
        setLikes(likedMap);

        // 3) user’s own ratings
        const ratingsRes = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/recipes/user-ratings`,
          { headers: { 'x-auth-token': token } }
        );
        const userMap = {};
        ratingsRes.data.forEach(({ recipeId, rating }) => {
          userMap[recipeId] = rating;
        });
        setUserRatings(userMap);

        // 4) compute average rating
        const avgMap = {};
        data.forEach(r => {
          if (r.ratings && r.ratings.length) {
            const sum = r.ratings.reduce((s, x) => s + x.value, 0);
            avgMap[r._id] = sum / r.ratings.length;
          } else {
            avgMap[r._id] = 0;
          }
        });
        setAverageRatings(avgMap);

      } catch (err) {
        console.error('Error fetching search results data:', err);
      }
    };

    fetchData();
  }, [location.search]);

  // Toggle like/unlike
  const handleLikeToggle = async (id) => {
    if (likeLocks[id]) return;
    const token = localStorage.getItem('token') || '';
    const wasLiked = !!likes[id];

    // optimistic UI
    setLikeLocks(l => ({ ...l, [id]: true }));
    setLikes(l => ({ ...l, [id]: !wasLiked }));
    setRecipes(rs =>
      rs.map(r =>
        r._id === id
          ? { ...r, likeCount: r.likeCount + (wasLiked ? -1 : 1) }
          : r
      )
    );

    try {
      await axios.post(
       `${import.meta.env.VITE_API_URL}/api/recipes/${id}/like`,
        {},
        { headers: { 'x-auth-token': token } }
      );
    } catch (e) {
      console.error('Error toggling like:', e);
      // rollback
      setLikes(l => ({ ...l, [id]: wasLiked }));
      setRecipes(rs =>
        rs.map(r =>
          r._id === id
            ? { ...r, likeCount: r.likeCount + (wasLiked ? 1 : -1) }
            : r
        )
      );
    } finally {
      setLikeLocks(l => ({ ...l, [id]: false }));
    }
  };

  // Submit a rating 1–5
  const handleStarClick = async (id, idx) => {
    const newRating = idx + 1;
    const token = localStorage.getItem('token') || '';

    // optimistic
    setUserRatings(u => ({ ...u, [id]: newRating }));

    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/recipes/${id}/rate`,
        { rating: newRating },
        { headers: { 'x-auth-token': token } }
      );
      setAverageRatings(a => ({ ...a, [id]: res.data.averageRating }));
    } catch (e) {
      console.error('Error submitting rating:', e);
      // rollback
      setUserRatings(u => ({ ...u, [id]: 0 }));
    }
  };

  // Toggle Learn More / Go Back
  const handleLearnMoreClick = (recipe) => {
    setSelectedPost(s =>
      s?._id === recipe._id ? null : recipe
    );
  };

  return (
    <div className="middle-part-search">
      <h1 className="search-section-heading">{getSearchHeader()}</h1>

      {recipes.length > 0 ? (
        recipes.map(recipe => (
          <div key={recipe._id}>
            <div className="post_container">
              <div className="user_profile">
                {recipe.user?.profilePicture
                  ? <img
                      src={recipe.user.profilePicture}
                      alt={recipe.user.name}
                      className="profile-pic"
                    />
                  : <i className="fa-solid fa-user" />
                }
                <div className="user_info">
                  <h4>{recipe.user?.name}</h4>
                  <h4 id="user_badge">{recipe.user?.rank}</h4>
                </div>
              </div>

              <img
                src={recipe.image || '/default.jpg'}
                alt={recipe.title}
                className="recipe-image"
              />

              <div className="post_interations">
                <div className="like_comment">
                  <i
                    className={likes[recipe._id]
                      ? "fa-solid fa-heart"
                      : "fa-regular fa-heart"}
                    onClick={() => handleLikeToggle(recipe._id)}
                  />
                  <i
                    className="fa-regular fa-comment"
                    onClick={() => setActiveCommentPostId(recipe._id)}
                  />
                  <span style={{ marginLeft: 8 }}>
                    {recipe.commentCount || 0}
                  </span>
                </div>

                <div className="ratings">
                  {[...Array(5)].map((_, i) => (
                    <i
                      key={i}
                      className={i < (userRatings[recipe._id] || 0)
                        ? solid
                        : regular}
                      onClick={() => handleStarClick(recipe._id, i)}
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
                  <b>
                    {(averageRatings[recipe._id] || 0).toFixed(1)} rating
                  </b>
                </p>
              </div>

              <p className="post-description">
                <b>{recipe.title}</b> {recipe.caption?.slice(0,100)}…
                <button
                  className="learn-more"
                  onClick={() => handleLearnMoreClick(recipe)}
                >
                  {selectedPost?._id === recipe._id
                    ? "Go Back"
                    : "Learn More"}
                </button>
              </p>
            </div>

            {/* ← Expanded Post goes here */}
            {selectedPost?._id === recipe._id && (
              <div className="expanded-post">
                <Post recipe={selectedPost} />
              </div>
            )}
          </div>
        ))
      ) : (
        <p>No recipes found.</p>
      )}

      {/* Comment Modal */}
      {activeCommentPostId && (
        <CommentModal
          recipeId={activeCommentPostId}
          onClose={() => setActiveCommentPostId(null)}
        />
      )}
    </div>
  );
}