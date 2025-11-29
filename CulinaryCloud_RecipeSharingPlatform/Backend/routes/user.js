const express = require('express');
const User = require('../models/User');
const authMiddleware = require('../middleware/auth');
const multer = require('multer');
// const cloudinary = require('../utils/cloudinary');
const router = express.Router();
const { uploadBufferToS3 } = require('../utils/s3');

const storage = multer.memoryStorage();
const upload = multer({ 
  storage,
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

router.get('/profile-picture/:userId', authMiddleware, async (req, res) => {
  try {
    if (req.params.userId !== req.user.id) {
      return res.status(403).send('Unauthorized access');
    }

    const user = await User.findById(req.user.id).select('profilePicture');
    
    if (!user?.profilePicture) {
      return res.status(404).send('Profile picture not found');
    }

    res.json({ url: user.profilePicture });
  } catch (err) {
    console.error(err.message);
    res.status(500).send('Server error');
  }
});

router.get('/me', authMiddleware, async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('_id profilePicture bio email rank name lname');
    if (!user) {
      return res.status(404).json({ msg: 'User not found' });
    }
    res.json({ id: user._id, profilePicture: user.profilePicture , bio:user.bio, email:user.email, rank:user.rank, fname:user.name, lname:user.lname});
  } catch (err) {
    console.error(err.message);
    res.status(500).json({ msg: 'Server error' });
  }
});

router.put('/profile', authMiddleware, upload.single('profilePicture'), async (req, res) => {
  try {
    console.log('[PUT /profile] req.user.id =', req.user.id);
    console.log('[PUT /profile] req.body =', req.body);
    console.log('[PUT /profile] req.file =', req.file);

    let profilePictureUrl = req.body.existingImage || ""; 
    
    if (req.file) {
      // Convert buffer to base64 
      // +      // Upload directly to S3 under "user-profiles/"
        profilePictureUrl = await uploadBufferToS3(
        req.file.buffer,
        req.file.mimetype,
        'user-profiles/'
        );
        console.log('[S3] Uploaded to', profilePictureUrl);
    }

    const updatedUser = await User.findByIdAndUpdate(
      req.user.id,
      {
        profilePicture: profilePictureUrl,
        dietaryPreferences: req.body.dietaryPreferences
      },
      { new: true }
    );
    
    res.json(updatedUser);
  } catch (err) {
    console.error(err.message);
    res.status(500).send('Server error');
  }
});


router.get('/bio', authMiddleware, async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('bio');
    if (!user) {
      return res.status(404).json({ msg: 'User not found' });
    }
    res.json({ bio: user.bio || "" });
  } catch (err) {
    console.error('[GET Bio Error]', err.message);
    res.status(500).send('Server error');
  }
});

router.put('/bio', authMiddleware, async (req, res) => {
  try {
    const { bio } = req.body;

    // Optional: limit bio lengt
    if (bio && bio.length > 300) {
      return res.status(400).json({ msg: 'Bio is too long (max 300 characters)' });
    }

    const user = await User.findByIdAndUpdate(
      req.user.id,
      { bio },
      { new: true }
    ).select('bio');

    res.json({ bio: user.bio });
  } catch (err) {
    console.error('[PUT Bio Error]', err.message);
    res.status(500).send('Server error');
  }
});

module.exports = router;