const express = require('express');
const Comment = require('../models/Comment');
const Recipe = require('../models/Recipe');
const authMiddleware = require('../middleware/auth');

const { calculateUserScore, determineUserRank, updateUserRankAndScore } = require('../models/Gamification');


const router = express.Router();

router.post('/:recipeId', authMiddleware, async (req, res) => {
  try {
    const { text } = req.body;
    const recipeId = req.params.recipeId;

    const newComment = new Comment({
      recipe: recipeId,
      user: req.user.id,
      text
    });

    await newComment.save();
    await Recipe.findByIdAndUpdate(recipeId, { $inc: { commentCount: 1 } });

    try {
      const recipe = await Recipe.findById(recipeId);
      const recipeOwnerId = recipe.user;
      const newScore = await calculateUserScore(recipeOwnerId);
      const newRank = determineUserRank(newScore);
      console.log("📢 Called updateUserRankAndScore()");
      await updateUserRankAndScore(recipeOwnerId, newScore, newRank);
      console.log(`User ${recipeOwnerId} score updated after comment.`);
    } catch (error) {
      console.error('Gamification error (comment):', error);
    }

    res.status(201).json(newComment);
  } catch (err) {
    console.error(err.message);
    res.status(500).send('Server error');
  }
});

// GET all comments for a recipe (with pagination)
router.get('/:recipeId', async (req, res) => {
  try {
    const recipeId = req.params.recipeId;

    // Pagination parameters from query string
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;

    const comments = await Comment.find({ recipe: recipeId })
      .populate('user', 'name profilePicture rank') // attach username to comment
      .sort({ createdAt: -1 }) // newest first
      .skip(skip)
      .limit(limit);

    res.json(comments);
  } catch (err) {
    console.error(err.message);
    res.status(500).send('Server error');
  }
});

//delete the comments
router.delete('/:commentId', authMiddleware, async (req, res) => {
    try {
      const comment = await Comment.findById(req.params.commentId);
      if (!comment) return res.status(404).json({ msg: 'Comment not found' });
  
      if (comment.user.toString() !== req.user.id) {
        return res.status(401).json({ msg: 'Not authorized' });
      }
  
      await Comment.deleteOne({ _id: comment._id });
      await Recipe.findByIdAndUpdate(comment.recipe, { $inc: { commentCount: -1 } });
  
      res.json({ msg: 'Comment deleted successfully' });
    } catch (err) {
      console.error(err.message);
      res.status(500).send('Server error');
    }
  });
  

module.exports = router;
