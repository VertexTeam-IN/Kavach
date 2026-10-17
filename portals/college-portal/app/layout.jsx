import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Apex Institute of Technology — Student Portal",
  description: "Secure Student & Faculty Academic Portal powered by Kavach Passwordless Authentication",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 font-sans text-slate-800 antialiased flex flex-col justify-between">
        {/* Header */}
        <header className="sticky top-0 z-30 border-b border-rose-950/20 bg-[#4c0519] text-white shadow-md">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5 sm:px-6">
            <Link href="/" className="flex items-center gap-3 group">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20 shadow-inner text-xl transition group-hover:scale-105">
                🎓
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold tracking-tight text-base sm:text-lg">
                    Apex Institute of Technology
                  </span>
                  <span className="hidden sm:inline-flex rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-rose-200 ring-1 ring-rose-400/30">
                    PORTAL
                  </span>
                </div>
                <p className="text-[11px] text-rose-200/70 font-medium">
                  Academic Computing &amp; Student Services
                </p>
              </div>
            </Link>

            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-300/20 bg-rose-950/40 px-3 py-1 text-xs font-medium text-rose-100 backdrop-blur-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="hidden sm:inline">OIDC Client ·</span> Kavach SSO
              </span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:py-12 flex-1">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 bg-white py-6 text-xs text-slate-500">
          <div className="mx-auto flex max-w-6xl flex-col sm:flex-row items-center justify-between gap-3 px-5 sm:px-6">
            <p>© 2026 Apex Institute of Technology · Department of Academic Computing</p>
            <p className="flex items-center gap-2 text-slate-400">
              <span>Next.js OIDC Client</span>
              <span>•</span>
              <span className="text-slate-600 font-medium">Assisted Sign-In Enabled</span>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
