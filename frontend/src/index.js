import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/index.css";
import App from "@/App";
import ChatDashboard from "@/components/ChatDashboard";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/chat" element={<ChatDashboard />} />
        <Route path="/demo" element={<ChatDashboard />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
