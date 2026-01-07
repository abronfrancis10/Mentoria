// src/firebase.js
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCdUCx9IIzuzgZi_7vbwyrSrDPhk-a-Rrc",
  authDomain: "mentoria-571d7.firebaseapp.com",
  projectId: "mentoria-571d7",
  storageBucket: "mentoria-571d7.appspot.com", // corrected
  messagingSenderId: "493724937878",
  appId: "1:493724937878:web:756538fcafa4d52e859cb7"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Export Auth instance for use in Signup/Login pages
export const auth = getAuth(app);
export default app;
