import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Landing() {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/login");
    }, 5000); // slightly longer to enjoy animation
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="landing-container">
      <img src="/mentoria_logo.jpg" alt="Mentoria Logo" className="landing-logo" />
      <h1 className="landing-title">Mentoria</h1>
      <p className="landing-subtitle">AI Interview Trainer</p>
    </div>
  );
}
