import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function Signup() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSignup(e) {
    e.preventDefault();
    alert("Signup Success ✔");
    navigate("/"); // Redirect to Login
  }

  return (
    <>
      <Navbar />
      <div className="container small-box">
        <h2>Create Account</h2>

        <form className="auth-form" onSubmit={handleSignup}>
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <input
            placeholder="Email ID"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button className="button primary" type="submit">
            Sign Up
          </button>

          <button className="button google" type="button">
            Sign Up With Google
          </button>
        </form>

        <p style={{ marginTop: 10 }}>
          Already have an account? <Link to="/">Login</Link>
        </p>
      </div>
    </>
  );
}
