const express = require('express');
const axios = require('axios');
const auth = require('../middleware/auth');
const ChatMessage = require('../models/ChatMsgs');
const Recipe = require('../models/Recipe');
const router = express.Router();

// Helper: zero-shot classify & extract search term
async function detectFindIntentWithGemini(question) {
  const prompt = `
You are a kitchen assistant. Given one user question, output JSON:
• intent: "find_recipe" or "other"
• if "find_recipe", include "term": the ingredient or keyword

Respond ONLY with one valid JSON object, e.g.:
{"intent":"find_recipe","term":"chicken"}
or
{"intent":"other"}

Question:
"${question}"
`;
  const res = await axios.post(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
    { contents:[{ parts:[{ text: prompt }] }] }
  );
  const txt = res.data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
  try {
    return JSON.parse(txt);
  } catch {
    return { intent: "other" };
  }
}

// Add this helper function to detect queries about popular recipes
async function detectPopularRecipesIntent(question) {
  const popularTerms = ["popular", "best", "top", "highest rated", "trending", "most liked"];
  const questionLower = question.toLowerCase();
  
  // Check if the question contains popular-related terms
  const containsPopularTerm = popularTerms.some(term => questionLower.includes(term));
  
  // Basic intent detection - can be enhanced with Gemini later
  if (containsPopularTerm && 
      (questionLower.includes("recipe") || 
       questionLower.includes("dish") || 
       questionLower.includes("food") || 
       questionLower.includes("meal"))) {
    return true;
  }
  
  return false;
}

// POST /api/chat/ask
router.post('/ask', auth, async (req, res) => {
  const userId   = req.user.id;
  const { question } = req.body;

  try {

    const isPopularDishesQuery = await detectPopularRecipesIntent(question);
    
    if (isPopularDishesQuery) {
      // 1) Aggregate: compute ratingCount & averageRating safely
      const popularRecipes = await Recipe.aggregate([
        {
          $addFields: {
            ratingCount: {
              $size: { $ifNull: ["$ratings", []] }
            },
            averageRating: {
              $cond: {
                if: { $gt: [{ $size: { $ifNull: ["$ratings", []] } }, 0] },
                then: { $avg: "$ratings.value" },
                else: 0
              }
            }
          }
        },
        // 2) Only include recipes with at least 2 ratings
        { $match: { ratingCount: { $gte: 2 } } },
        // 3) Sort by averageRating (desc), then likeCount (desc)
        { $sort: { averageRating: -1, likeCount: -1 } },
        // 4) Limit to top 5
        { $limit: 5 },
        // 5) Lookup creator’s name
        {
          $lookup: {
            from: "users",
            localField: "user",
            foreignField: "_id",
            as: "creator"
          }
        },
        { $unwind: "$creator" },
        // 6) Project only needed fields
        {
          $project: {
            title: 1,
            caption: 1,
            likeCount: 1,
            categories: 1,
            ratingCount: 1,
            averageRating: { $round: ["$averageRating", 1] },
            creatorName: "$creator.name"
          }
        }
      ]);
    
      if (popularRecipes.length) {
        // 7) Format answer
        const recipesList = popularRecipes
          .map((r, i) => {
            // choose emoji by keyword
            let emoji = "🍲";
            const t = r.title.toLowerCase();
            if (t.includes("chicken")) emoji = "🍗";
            if (t.includes("rice") || t.includes("biryani") || t.includes("pulao")) emoji = "🍚";
    
            return `**${i + 1}. ${emoji} ${r.title}**\n` +
                   `_${r.caption || "A delicious recipe"}_\n` +
                   `👨‍🍳 ${r.creatorName} | ⭐ ${r.averageRating} (${r.ratingCount} ratings)` +
                   (r.likeCount ? ` | ❤️ ${r.likeCount} likes` : "");
          })
          .join("\n\n");
    
        const answer = `**🏆 Most Popular Dishes:**\n\n${recipesList}\n\n` +
                       `Search by title (and chef name) on the site to view them.`;
    
        // 8) Save chat
        await ChatMessage.create({ userId, from: 'user', text: question });
        await ChatMessage.create({ userId, from: 'bot',  text: answer });
    
        return res.json({ answer });
      }
    }    

    // 1) Intent detection
    const { intent, term } = await detectFindIntentWithGemini(question);

    if (intent === 'find_recipe' && term) {
      // Text-search your Recipe collection with the required fields
      const hits = await Recipe.find(
        { $text: { $search: term } },
        { 
          score: { $meta: 'textScore' },
          title: 1,
          caption: 1,
          user: 1,
          ratings: 1,
          image: 1
        }
      )
      .sort({ score: { $meta: 'textScore' } })
      .limit(5)
      .populate('user', 'name'); // Get creator name
    
      if (hits.length) {
        // Format the search results with additional information
        const formattedResults = hits.map(recipe => {
          // Calculate average rating
          const avgRating = recipe.ratings.length > 0 
            ? recipe.ratings.reduce((sum, rating) => sum + rating.value, 0) / recipe.ratings.length 
            : 'No ratings yet';
          
          // Format the rating to show up to 1 decimal place if it's a number
          const formattedRating = typeof avgRating === 'number' 
            ? avgRating.toFixed(1) 
            : avgRating;
          
          return {
            title: recipe.title,
            caption: recipe.caption || 'No caption available',
            creator: recipe.user?.name || 'Unknown chef',
            rating: formattedRating,
            id: recipe._id,
            image: recipe.image
          };
        });
    
        // Format the response
// Format the response with better styling
      const recipesList = formattedResults.map((r, index) => {
        const ratingDisplay = r.rating === 'No ratings yet' 
          ? 'No ratings yet' 
          : `${r.rating}★`;
        
        return `**${index + 1}. [${r.title}](/recipes/${r.id})**
        ${r.caption ? `_"${r.caption}"_` : ''}
        👨‍🍳 Chef: ${r.creator} | 🌟 Rating: ${ratingDisplay}`;
      }).join('\n\n');

      const answer = `**Yummy recipes with "${term}" Found:**\n\n${recipesList}\n\nSearch them up to enjoy a TASTY MEAL!`;

      // Save user & bot messages
      await ChatMessage.create({ userId, from: 'user', text: question });
      await ChatMessage.create({ userId, from: 'bot', text: answer });

      return res.json({ answer });
      } else {
        const answer = `I'm sorry, I couldn't find any recipes containing "${term}." Would you like me to suggest some general cooking tips with ${term} instead?`;
        
        // Save user & bot messages
        await ChatMessage.create({ userId, from: 'user', text: question });
        await ChatMessage.create({ userId, from: 'bot', text: answer });
    
        return res.json({ answer });
      }
    }

    // — else: full cooking-assistant flow —

    // 3) Fetch last 5 messages for context
    const recent = await ChatMessage.find({ userId })
      .sort({ timestamp: -1 })
      .limit(5)
      .select('from text');
    const history = recent.reverse()
      .map(m => `${m.from}: ${m.text}`)
      .join('\n');

    // 4) Build system prompt
    const systemPrompt = `You are "ChefBot," a friendly and expert assistant focused only on culinary topics.
• You help users with recipes, ingredient substitutions, cooking methods, cuisines, food science, nutrition, and kitchen tools.
• You can respond to casual or structured food-related queries — even vague ones like “What can I use instead of tomatoes?”
• You do not answer anything outside the culinary domain. If asked something unrelated, politely respond:  
  “I'm here to help only with food, cooking, and culinary questions!”
    
    When answering:
    1. Give practical, step-by-step advice (“First…, Next…, Finally…”).
    2. If a user asks for measurements or conversions, include both metric & imperial.
    3. If they request a recipe, list ingredients, quantities, and prep/cook times.
    4. Ask clarifying questions if ambiguous.
    5. Keep responses under 150 words unless asked for more.
    
    Always start with a quick summary (“Sure! Here’s how you can…”) and end with an offer (“Let me know if you need more tips!”).`;
    

    const prompt = `
${systemPrompt}

Previous conversation:
${history}

Question: ${question}
`;

    // 5) Call Gemini for the cooking response
    let apiRes;
    try {
      apiRes = await axios.post(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,
        { contents:[{ parts:[{ text: prompt }] }] }
      );
    } catch (err) {
      console.error("Gemini API error:", err.response?.data || err.message);
      return res.status(502).json({ error: "AI service error. Please try again." });
    }

    const candidate = apiRes.data.candidates?.[0] || {};
    const reply =
      candidate.content?.parts?.[0]?.text ||
      candidate.output?.content?.text ||
      "Sorry, I couldn't fetch an answer from the AI.";

    // 6) Save the chat exchange
    await ChatMessage.create({ userId, from: 'user', text: question });
    await ChatMessage.create({ userId, from: 'bot',  text: reply });

    return res.json({ answer: reply });

  } catch (error) {
    console.error("Chat /ask error:", error);
    res.status(500).json({ error: "Failed to process chat request." });
  }
});

// GET /api/chat/history - Retrieve conversation history
router.get('/history', auth, async (req, res) => {
  const userId = req.user.id;
  try {
    const messages = await ChatMessage.find({ userId })
      .sort({ timestamp: 1 })
      .select('from text');
    res.json(messages);
  } catch (error) {
    console.error("Error fetching chat history:", error);
    res.status(500).json({ error: "Failed to fetch chat history." });
  }
});

// DELETE /api/chat/history - Clear entire chat for this user
router.delete('/history', auth, async (req, res) => {
  try {
    await ChatMessage.deleteMany({ userId: req.user.id });
    res.sendStatus(204);
  } catch (err) {
    console.error("Error clearing chat history:", err);
    res.status(500).json({ error: "Failed to clear chat history." });
  }
});


module.exports = router;