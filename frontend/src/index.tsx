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
(async () => {
    try {
        const userInfoList = await getUserInfo();
        if (userInfoList.length > 0 && userInfoList[0] && userInfoList[0].user_id) {
            console.log("setting app insights user to " + userInfoList[0].user_id);
            appInsights.setAuthenticatedUserContext(userInfoList[0].user_id);
        } else {
            console.log("no user info found for app insights.");
        }
    } catch (error) {
        console.error("An error occurred while loading user info:", error);
    }
})();


import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";

import "./index.css";

import Layout from "./pages/layout/Layout";
import NoPage from "./pages/NoPage";
import Chat from "./pages/chat/Chat";
import { AppStateProvider } from "./state/AppProvider";
import { getUserInfo } from "./api";

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
