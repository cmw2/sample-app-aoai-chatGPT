import React from "react";
import { ApplicationInsights } from '@microsoft/applicationinsights-web';
import { ReactPlugin} from '@microsoft/applicationinsights-react-js';

var reactPlugin = new ReactPlugin();
var appInsights = new ApplicationInsights({
    config: {
        connectionString: import.meta.env.VITE_APPINSCONSTR,
        enableAutoRouteTracking: true,
        extensions: [reactPlugin]        
    }
});

appInsights.loadAppInsights();

import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";

import "./index.css";

import Layout from "./pages/layout/Layout";
import NoPage from "./pages/NoPage";
import Chat from "./pages/chat/Chat";
import { AppStateProvider } from "./state/AppProvider";

initializeIcons();

export default function App() {
    return (
        <AppStateProvider>
            <HashRouter>
                <Routes>
                    <Route path="/" element={<Layout />}>
                        <Route index element={<Chat />} />
                        <Route path="*" element={<NoPage />} />
                    </Route>
                </Routes>
            </HashRouter>
        </AppStateProvider>
    );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);
