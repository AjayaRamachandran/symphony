import React from "react";

import TitleBar from "../components/TitleBar";
import Content from "../components/Content";

function HomePage() {
  return (
    <div className="full-page">
      <TitleBar />
      <Content />
    </div>
  );
}

export default HomePage;
