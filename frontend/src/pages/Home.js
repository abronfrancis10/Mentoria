import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function Home() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleLogin(e) {
    e.preventDefault();
    if (!email || !password) return alert("Enter credentials");
    navigate("/role"); // Go to role selection after login
  }

  function googleLogin() {
    alert("Google Login Coming Soon 🔒");
  }

  return (
    <>
      <Navbar />
      <div className="container small-box">
        <h2>Welcome to Mentoria</h2>
        <p style={{ color: "#555" }}>Login to start Mock Interviews</p>

        <form onSubmit={handleLogin} className="auth-form">
          <input
            type="email"
            placeholder="Email ID"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button className="button primary" type="submit">Login</button>

          <button
            type="button"
            className="button google"
            onClick={googleLogin}
          >
            Continue with Google
          </button>
        </form>

        <p style={{ marginTop: 10 }}>
          Don’t have an account? <Link to="/signup">Sign Up</Link>
        </p>
      </div>
    </>
  );
}
