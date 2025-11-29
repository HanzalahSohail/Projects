const mongoose = require('mongoose');
const validator = require('validator');

const AuthLocalSchema = new mongoose.Schema({
  password: {
    type: String,
    required: function () {
      const parent = this.parent();
      return !(parent.google && parent.google.id);
    }
  }
}, { _id: false });

const AuthGoogleSchema = new mongoose.Schema({
  id: { type: String }
}, { _id: false });

const AuthSchema = new mongoose.Schema({
  local: {
    type: AuthLocalSchema,
    default: {}
  },
  google: {
    type: AuthGoogleSchema,
    default: {}
  }
}, { _id: false });

const UserSchema = new mongoose.Schema({
  email: {
    type: String,
    required: [true, "Email is required"],
    unique: true,
    validate: {
      validator: validator.isEmail,
      message: props => `${props.value} is not a valid email address!`
    }
  },
  name: { 
    type: String 
  },
  lname:{
    type: String
  },
  auth: {
    type: AuthSchema,
    default: {}
  },
  profilePicture:{
    type: String, 
    default: ""
  },
  dietaryPreferences: {
    type: [String],
    default: [],
    validate: [val => val.length <= 10, '{PATH} exceeds the limit of 10']
  },
  bio: {
    type:String,
    default: "No bio yet"
  },
  rank: {
    type: String,
    default: "Prep Cook"
  },
  score: {
    type: Number,
    default: 0
  }
}, { timestamps: true });

// at the bottom of User.js, right before module.export
UserSchema.pre('save', function(next) {
  if (!this.name && this.email) {
    this.name = this.email.split('@')[0];
  }
  next();
});


module.exports = mongoose.model('User', UserSchema);