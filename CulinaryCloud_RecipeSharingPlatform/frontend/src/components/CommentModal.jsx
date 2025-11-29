import { useEffect, useState } from 'react';
import axios from 'axios';

function CommentModal({ recipeId, onClose }) {
  const [comments, setComments] = useState([]);
  const [text, setText] = useState("");

  const fetchComments = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/comments/${recipeId}`);
      setComments(res.data);
    } catch (err) {
      console.error("Error fetching comments:", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;

    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/comments/${recipeId}`, {
        text
      }, {
        headers: {
          'x-auth-token': localStorage.getItem('token') || ''
        }
      });
      setText("");
      fetchComments(); // Refresh comments after pos
    } catch (err) {
      console.error("Error posting comment:", err);
    }
  };

  useEffect(() => {
    fetchComments();
  }, [recipeId]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Comments</h2>
        <div className="comment-list">
          {comments.map((c) => (
            <div key={c._id} className="comment-item">
              <div className="comment-user-info" style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                {c.user?.profilePicture ? (
                  <img
                    src={c.user.profilePicture}
                    alt="User"
                    style={{ width: "24px", height: "24px", borderRadius: "50%" }}
                  />
                ) : (
                  <i className="fa-solid fa-user" style={{ fontSize: "18px" }} />
                )}
                <strong>{c.user?.name || "User"}</strong>
                <span style={{ color: "#888", fontSize: "12px" }}>
                  ({c.user?.rank || "Prep Cook"})
                </span>
              </div>
              <p style={{ marginLeft: "32px" }}>{c.text}</p>
            </div>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="comment-form" style={{ marginTop: "16px", display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Write a comment..."
            className="comment-input"
            style={{ flex: 1, padding: "8px" }}
          />
          <button type="submit" className="comment-submit" style={{ backgroundColor: "#008000", color: "#fff", border: "none", padding: "8px 12px", borderRadius: "4px" }}>
            Post
          </button>
        </form>
      </div>
    </div>
  );
}

export default CommentModal;
