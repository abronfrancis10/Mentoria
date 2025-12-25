import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup
} from "firebase/auth";
import { auth } from "../firebase";
import Navbar from "../components/Navbar";
import "./Signup.css";

export default function Signup() {
  const navigate = useNavigate();
  const googleProvider = new GoogleAuthProvider();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const handleSignup = async (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      return setError("Passwords do not match");
    }

    try {
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email,
        password
      );
      console.log("UID:", userCredential.user.uid);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleGoogleSignup = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      console.log("Google UID:", result.user.uid);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <Navbar />

      <div className="auth-wrapper">
        <div className="auth-card">
          <h2>Create Account</h2>
          <p className="auth-caption">
            Start your AI-powered mock interview journey
          </p>

          <form className="auth-form" onSubmit={handleSignup}>
            <input
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />

            <input
              type="email"
              placeholder="Email ID"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            {/* Password */}
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
                  /* Eye OFF */
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M3 3L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
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
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M2 12C4.5 7 9 4 12 4s7.5 3 10 8c-2.5 5-7 8-10 8s-7.5-3-10-8z"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
                  </svg>
                )}
              </button>
            </div>

            {/* Confirm Password */}
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Confirm Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />

            <button className="button primary" type="submit">
              Sign Up
            </button>
          </form>

          <button
            className="button google"
            type="button"
            onClick={handleGoogleSignup}
          >
            Sign Up With Google
          </button>

          {error && <p className="auth-error">{error}</p>}

          <p className="auth-switch">
            Already have an account? <Link to="/">Login</Link>
          </p>
        </div>
      </div>
    </>
  );
}
