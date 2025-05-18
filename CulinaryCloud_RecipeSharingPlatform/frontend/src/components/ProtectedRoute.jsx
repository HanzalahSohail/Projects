import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ children, isAuthenticated, isGuest }) {
  if (!isAuthenticated && !isGuest) {
    console.log("Auth:", isAuthenticated, "Guest:", isGuest);
    return <Navigate to="/" replace />;
  }
  return children;
} 