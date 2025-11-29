const jwt = require('jsonwebtoken');

module.exports = function (req, res, next) {
  // Get token from heade
  const token = req.header('x-auth-token');

  if (token) {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      req.user = decoded.user;
    } catch (err) {
      console.error('Optional auth: Invalid token, proceeding as guest.');
    }
  }
  next();
};
