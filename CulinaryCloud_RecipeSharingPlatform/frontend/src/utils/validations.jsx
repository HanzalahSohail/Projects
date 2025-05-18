export const validateEmail = (email) => {
    return /\S+@\S+\.\S+/.test(email);
  };
  
  export const validatePassword = (password) => {
    return password.length >= 6;
  };
     