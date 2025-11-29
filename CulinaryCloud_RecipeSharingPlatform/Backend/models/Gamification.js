const User = require('../models/User');
const Recipe = require('../models/Recipe');
const Like = require('../models/Like');
const Comment = require('../models/Comment');


async function calculateUserScore(userId) {
    try {
        const recipes = await Recipe.find({ user: userId });
        const likes = await Like.find({ recipe: { $in: recipes.map(r => r._id) } });
        const comments = await Comment.find({ recipe: { $in: recipes.map(r => r._id) } });

        let totalRating = 0;
        let ratingCount = 0;
        recipes.forEach(recipe => {
            recipe.ratings.forEach(rating => {
                totalRating += rating.value;
                ratingCount++;
            });
        });
        const averageRating = ratingCount > 0 ? totalRating / ratingCount : 0;

        const score =
            recipes.length * 5 +   
            averageRating * 4 +     
            likes.length * 3 +         
            comments.length * 2;       

        return score;
    } catch (error) {
        console.error('Error calculating user score:', error);
        return 0;
    }
}

function determineUserRank(score) {
    if (score >= 500) {
        return 'Master Chef';
    } else if (score >= 200) {
        return 'Experienced Cook';
    } else if (score >= 30) {
        return 'Sous Chef';
    } else {
        return 'Prep Cook';
    }
}

async function updateUserRankAndScore(userId, score, rank) {
    try {
        await User.findByIdAndUpdate(userId, { score: score, rank: rank });
        console.log(`[Gamification] Updated → User: ${userId} | Score: ${score} | Rank: ${rank}`);
    } catch (error) {
        console.error('Error updating user rank and score:', error);
    }
}

module.exports = {
    calculateUserScore,
    determineUserRank,
    updateUserRankAndScore,
};