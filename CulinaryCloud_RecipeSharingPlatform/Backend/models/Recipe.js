const mongoose = require('mongoose');

const ALLOWED_CATEGORIES = [
  "Biryani Varieties",
  "Nihari Delicacies",
  "Karahi Creations",
  "Korma Specialties",
  "Haleem Masterpieces",
  "Kebab Assortments",
  "Tandoori Treats",
  "Curry Classics",
  "Pulao Dishes",
  "Daal Delights",
  "Chaat Sensations",
  "Paratha Varieties",
  "Naan & Flatbreads",
  "Samosa Selections",
  "Pakora & Bhaji",
  "Pickles & Chutneys",
  "Raita & Yogurt Dishes",
  "Saag & Green Vegetable Curries",
  "Vegetable Curries",
  "Mughlai Influences",
  "Street Food Specialties",
  "Seafood Selections",
  "Traditional Desserts",
  "Rice Puddings & Kheer",
  "Sheer Khurma",
  "Lassi & Yogurt Drinks",
  "Chai Varieties",
  "Halwa Creations",
  "Salad & Raita Innovations",
  "Fusion Desi Snacks"
];

const StepSchema = new mongoose.Schema({
  ingredients: [
    {
      name: String, 
      quantity: String, 
      unit: String
    }
  ],
  description: String,
  time: {
    hours: Number,
    minutes: Number
  }
  
});


const NutritionSchema = new mongoose.Schema({
  calories:   Number,
  protein:    Number,
  fat:        Number,
  carbs:      Number,
  analyzedAt: Date,
});

const RecipeSchema = new mongoose.Schema({
  title: { type: String, required: true },
  steps: [StepSchema],
  image: String,
  caption: String,
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  createdAt: { type: Date, default: Date.now },

  likeCount: { type: Number, default: 0 },
  commentCount: { type: Number, default: 0 },
  
  //Added by samad
  ratings: [
    {
      user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
      value: { type: Number, required: true }
    }
  ],

  categories: {
    type: [String],
    default: [],
    enum: ALLOWED_CATEGORIES,
    validate: {
      validator: function(val) {
        return val.length <= 3;
      },
      message: '{PATH} exceeds the limit of 3'
    }
  },
  videoUrls:{
    type: [String],
    default: []
  },
  nutrition:{
    type: NutritionSchema,
    default: null    // ← made it optional as there are existing recipes that do not have this
  }
});

RecipeSchema.index({
  title:             'text',
  categories:        'text',
  'steps.ingredients.name': 'text'
},
{
  weights: {
    title: 10,
    categories: 5,
    'steps.ingredients.name': 3
  }
}
);


module.exports = mongoose.model('Recipe', RecipeSchema);
