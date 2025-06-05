import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";

import TitleBar from "../components/TitleBar";
import Content from "../components/Content";

function HomePage() {

  return (
    <div className='full-page'>
      <TitleBar />
      <Content />
    </div>
  );
}

export default HomePage;