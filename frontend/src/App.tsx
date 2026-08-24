import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./AuthContext";
import Layout from "./components/Layout";
import AdminLayout from "./components/AdminLayout";
import Home from "./pages/Home";
import Companies from "./pages/Companies";
import CompanyDetail from "./pages/CompanyDetail";
import News from "./pages/News";
import Analysis from "./pages/Analysis";
import AdminLogin from "./pages/admin/AdminLogin";
import AdminDashboard from "./pages/admin/AdminDashboard";
import CrawlRuns from "./pages/admin/CrawlRuns";
import NewsReview from "./pages/admin/NewsReview";
import Users from "./pages/admin/Users";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/companies" element={<Companies />} />
            <Route path="/companies/:id" element={<CompanyDetail />} />
            <Route path="/news" element={<News />} />
            <Route path="/analysis" element={<Analysis />} />
          </Route>

          {/* Admin auth */}
          <Route path="/admin/login" element={<AdminLogin />} />

          {/* Admin (JWT + RBAC protected; enforced again server-side) */}
          <Route element={<AdminLayout />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/crawl-runs" element={<CrawlRuns />} />
            <Route path="/admin/news-review" element={<NewsReview />} />
            <Route path="/admin/users" element={<Users />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
