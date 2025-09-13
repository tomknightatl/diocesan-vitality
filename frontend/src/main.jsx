import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App.jsx';
import Diocese from './Diocese.jsx';
import Dashboard from './Dashboard.jsx';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';

import Reports from './Reports.jsx';
import Layout from './Layout.jsx';
import Parish from './Parish.jsx';

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      {
        path: "/",
        element: <App />,
      },
      {
        path: "/diocese",
        element: <Diocese />,
      },
      {
        path: "/parish",
        element: <Parish />,
      },
      {
        path: "/reports",
        element: <Reports />,
      },
      {
        path: "/dashboard",
        element: <Dashboard />,
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
