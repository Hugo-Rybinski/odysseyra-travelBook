import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./index.css";

// The service worker is registered by useRegisterSW() inside <PwaStatus/>, which
// also surfaces the update-available / offline-ready toasts.

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
