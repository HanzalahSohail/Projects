// middleware/passportConfig.js
const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const User = require('../models/User'); 

passport.serializeUser((user, done) => {
  done(null, user._id);
});

passport.deserializeUser(async (id, done) => {
  try {
    const user = await User.findById(id);
    done(null, user);
  } catch (err) {
    done(err, null);
  }
});

passport.use(
  new GoogleStrategy(
    {
      clientID: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      callbackURL:  process.env.GOOGLE_CALLBACK_URL
    },
    async (accessToken, refreshToken, profile, done) => {
      try {
        //  Safely access the emai
        const email = profile.emails?.[0]?.value;

        if (!email) {
          return done(new Error("Email not provided by Google"), null);
        }

        let user = await User.findOne({ email });

        if (!user) {
          user = new User({
            email,
            name: profile.displayName,
            auth: {
              google: { id: profile.id }
            },
            profilePicture: profile.photos?.[0]?.value || ""
          });
          await user.save();
        } else if (!user.auth.google) {
          user.auth.google = { id: profile.id };
          await user.save();
        }

        return done(null, user);
      } catch (err) {
        console.error("Google OAuth Error:", err);
        return done(err, null);
      }
    }
  )
);


module.exports = passport;
