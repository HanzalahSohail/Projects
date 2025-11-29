const express = require('express');
const mongoose = require('mongoose');
const dotenv = require('dotenv');
const cors = require('cors');
const session = require('express-session');     // <-- New: Session middleware
const passport = require('passport');           // <-- New: Passport middleware
// const { v2: cloudinary } = require('cloudinary'); // Add this line

dotenv.config();
// cloudinary.config({ 
//   cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
//   api_key: process.env.CLOUDINARY_API_KEY,
//   api_secret: process.env.CLOUDINARY_API_SECRET
// });

const app = express();

app.use(cors({
  origin: [
    process.env.FRONTEND_URL
  ],
  // credentials: true
}));

app.use(express.json({ limit: '25mb' }));
app.use(express.urlencoded({ extended: true, limit: '25mb' }));
// Set up session middleware
app.use(
  session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
  })
);

// Initialize Passport and enable session support
require('./middleware/passportConfig');  // Load passport configuration
app.use(passport.initialize());
app.use(passport.session());

// Connect to MongoDB
const connectDB = async () => {
  try {
    await mongoose.connect(process.env.MONGO_URI);
    console.log('MongoDB connected');
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
};

connectDB();

app.get('/', (req, res) => res.send('API running'));

// Route imports
const authRoutes = require('./routes/auth');
const recipeRoutes = require('./routes/recipe');
const commentRoutes = require('./routes/comment');
const userRoutes = require('./routes/user');
const chatRoutes = require('./routes/chat')

// Use routes
app.use('/api/auth', authRoutes);
app.use('/api/recipes', recipeRoutes);
app.use('/api/comments', commentRoutes);
app.use('/api/user', userRoutes);
app.use('/api/chat', chatRoutes); //added by samad

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => console.log(`Server running on port ${PORT}`));
