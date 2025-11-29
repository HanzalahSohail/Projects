import { useEffect, useState } from "react";
import {
  Routes,
  Route,
  useNavigate,
  useLocation,
  Outlet,
  Navigate
} from "react-router-dom";

// Pages and Components
import LoginScreen from "./pages/login.jsx";
import SignupScreen from "./pages/signup.jsx";
import Navbar from "./pages/Navbar";
import Search from "./pages/Search";
import Recipe from "./pages/Recipe";
import Profile from "./pages/Profile";
import Create from "./pages/Create";
import SearchResults from "./pages/SearchResults";
import QuickRecipes from "./pages/QuickRecipes.jsx";
import ChatBot from "./pages/Chatbot.jsx";
import TrendingRecipes from "./pages/TrendingRecipes.jsx";
import ProtectedRoute from "./components/ProtectedRoute";
import GuestTimeoutModal from "./components/GuestTimeoutModal";
import StartCooking from "./pages/startCooking"; // Added import for StartCooking

function App() {
  // Authentication and guest state
  const [isAuthenticated, setIsAuthenticated] = useState(
    localStorage.getItem("isAuthenticated") === "true"
  );
  const [isGuest, setIsGuest] = useState(
    localStorage.getItem("isGuest") === "true"
  );
  const [showSignup, setShowSignup] = useState(false);
  const [showGuestModal, setShowGuestModal] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();

  // Token handling from URL (e.g., Google OAuth redirect)
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const token = queryParams.get("token");

    if (token) {
      localStorage.setItem("token", token);
      localStorage.setItem("isAuthenticated", "true");
      localStorage.removeItem("isGuest");
      setIsAuthenticated(true);
      setIsGuest(false);
      navigate("/home", { replace: true });
    }
  }, [location, navigate]);

  // Show guest modal after 30 seconds if guest
  useEffect(() => {
    if (isGuest) {
      const timer = setTimeout(() => {
        setShowGuestModal(true);
      }, 30000);
      return () => clearTimeout(timer);
    }
  }, [isGuest]);

  const handleAuthSuccess = () => {
    setIsAuthenticated(true);
    setIsGuest(false);
    localStorage.setItem("isAuthenticated", "true");
    localStorage.removeItem("isGuest");
    navigate("/home");
  };

  const handleGuestLogin = () => {
    setIsAuthenticated(false);
    setIsGuest(true);
    localStorage.setItem("isAuthenticated", "false");
    localStorage.setItem("isGuest", "true");
    navigate("/home");
  };

  const handleLogout = async () => {
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/api/chat/history`, {
        method: 'DELETE',
        headers: { 'x-auth-token': localStorage.getItem('token') || '' }
      });
    } catch (err) {
      console.error("Failed to clear chat history on logout:", err);
    }
  
    // now clear client state
    setIsAuthenticated(false);
    setIsGuest(false);
    localStorage.clear();
    navigate("/");
  };  

  const toggleAuthScreen = () => {
    setShowSignup(!showSignup);
  };

  
  return (
    <div className="main-container">
      <Routes>
        <Route
          path="/"
          element={
            <div className="body-lo">
              {showSignup ? (
                <SignupScreen
                  onAuthSuccess={handleAuthSuccess}
                  toggleScreen={toggleAuthScreen}
                />
              ) : (
                <LoginScreen
                  onAuthSuccess={handleAuthSuccess}
                  toggleScreen={toggleAuthScreen}
                  onGuestLogin={handleGuestLogin}
                />
              )}
            </div>
          }
        />
        <Route path="/dashboard" element={<Navigate to="/home" replace />} />

        <Route
          path="/home/*"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isGuest={isGuest}>
              <div className="original-page">
                <div className="screen">
                  <div className="page">
                    <div className="left-part">
                      <Navbar onLogout={handleLogout} />
                    </div>
                    <div className="middle-part">
                      <Outlet />
                    </div>
                    <div className="right-part">
                    {!chatOpen ? (
                      <button
                        className="open-chat-btn"
                        onClick={() => setChatOpen(true)}
                      >
                        Talk with our AI expert
                      </button>
                    ) : (
                      <ChatBot onClose={() => setChatOpen(false)}
                        // session={chatSession}
                        // setSession={setChatSession}
                         />
                    )}
                  </div>
                  </div>
                  {showGuestModal && isGuest && (
                    <GuestTimeoutModal
                      onLogin={() => (window.location.href = "/")}
                      onSignup={() => (window.location.href = "/")}
                    />
                  )}
                </div>
              </div>
            </ProtectedRoute>
          }
        >
          {/* Default landing view: Search and Recipe */}
          <Route
            index
            element={
              <>
                <Search />
                <Recipe />
              </>
            }
          />
          {/* Nested routes */}
          <Route path="profile" element={<Profile />} />
          <Route path="search" element={<Search />} />
          <Route path="search-results" element={<SearchResults />} />
          <Route path="create" element={<Create />} />
          <Route path="quick-recipes" element={<QuickRecipes />} />
          <Route path="start-cooking" element={<StartCooking />} /> {/* Added route for step-by-step cooking */}
          <Route path="trending" element={<TrendingRecipes/>} />
        </Route>
      </Routes>
    </div>
  );
}

export default App;