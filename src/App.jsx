import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
//import FindPage from "./pages/FindPage";

function App() {

  return (
    <>
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/find/*" element={<FindPage />} />
        </Routes>
      </Router>
    </>
  )
}

export default App