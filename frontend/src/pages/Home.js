import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signInWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { auth } from "../firebase"; // Import your Firebase Auth
import Navbar from "../components/Navbar";
import "./Home.css";

export default function Home() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);


  const googleProvider = new GoogleAuthProvider();

  // Email/Password login
  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      return setError("Enter both email and password");
    }
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      console.log("Logged in UID:", userCredential.user.uid);
      navigate("/role"); // Go to role selection after login
    } catch (err) {
      setError(err.message);
    }
  };

  // Google login
  const googleLogin = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      console.log("Google UID:", result.user.uid);
      navigate("/role"); // Redirect to role selection
    } catch (err) {
      setError(err.message);
    }
  };

  return (
  <>
    <Navbar />

    <div className="home-wrapper">
      <div className="home-grid">

        {/* LEFT: LOGIN CARD */}
        <div className="home-card">
          <h2>Welcome to Mentoria</h2>
          <p className="home-caption">
            Practice AI-powered mock interviews and get real-time feedback.
          </p>

          <form onSubmit={handleLogin} className="auth-form">
            <input
              type="email"
              placeholder="Email ID"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

           <div className="password-wrapper">
  <input
    type={showPassword ? "text" : "password"}
    placeholder="Password"
    value={password}
    onChange={(e) => setPassword(e.target.value)}
  />

  <button
  type="button"
  className="toggle-password"
  onClick={() => setShowPassword(!showPassword)}
  aria-label="Toggle password visibility"
>
  {!showPassword ? (
    /* Eye OFF (default) */
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M3 3L21 21"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M10.6 10.6A3 3 0 0012 15a3 3 0 002.4-4.4"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M6.2 6.2C4.3 7.7 2.9 9.7 2 12c2.5 5 7 8 10 8 1.3 0 2.7-.4 4-1"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M9.9 4.2A10.6 10.6 0 0112 4c3 0 7.5 3 10 8a14.5 14.5 0 01-3.2 4.4"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  ) : (
    /* Eye ON */
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M2 12C4.5 7 9 4 12 4s7.5 3 10 8c-2.5 5-7 8-10 8s-7.5-3-10-8z"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle
        cx="12"
        cy="12"
        r="3"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  )}
</button>

</div>


            <button className="button primary" type="submit">
              Login
            </button>

            <button
              type="button"
              className="button google"
              onClick={googleLogin}
            >
              Continue with Google
            </button>
          </form>

          {error && <p style={{ color: "red", marginTop: 8 }}>{error}</p>}

          <p className="signup-text">
            Don’t have an account? <Link to="/signup">Sign Up</Link>
          </p>
        </div>

        {/* RIGHT: ILLUSTRATION */}
        <div className="illustration-box">
  <img src="/illustrations/Interview.png" alt="Interview Illustration" />
  <p className="illustration-caption">
    Practice interviews with AI-powered feedback
  </p>
</div>



      </div>
    </div>
  </>
);

}
