import { Outlet } from "react-router-dom";
import Header from "./Header";

/** Public shell: top navigation + content + footer. No auth required. */
export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-16 pt-7 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-panel-border py-5">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 text-xs text-muted sm:flex-row sm:px-6">
          <span>NEPSE Pulse — news &amp; market analytics for the Nepal Stock Exchange</span>
          <span>Data crawled from public NEPSE news portals; for research use only.</span>
        </div>
      </footer>
    </div>
  );
}
