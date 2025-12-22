import React from "react";
import { Link } from "react-router-dom";
import "./Navbar.css";

export default function Navbar() {
  return (
    <nav className="navbar">
      <h2 className="logo">Mentoria</h2>
      <ul>
        <li><Link to="/dashboard">Dashboard</Link></li>
        <li><Link to="/help">Help</Link></li>
        <li><Link to="/">Login</Link></li>
      </ul>
    </nav>
  );
}
