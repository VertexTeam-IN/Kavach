import Link from "next/link";
import { getSession } from "@/lib/session";

export default async function Home({ searchParams }) {
  const { error } = await searchParams;
  const session = await getSession();

  return (
    <div className="mx-auto max-w-4xl">
      <div className="grid gap-8 md:grid-cols-[1.1fr_1fr] items-center">
        {/* Left Column: Campus Highlights & Intro */}
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-3.5 py-1 text-xs font-semibold text-rose-800">
            <span className="flex h-2 w-2 rounded-full bg-rose-600" />
            Fall Semester 2026 Active
          </div>

          <div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
              Unified Academic &amp; Student Services
            </h1>
            <p className="mt-3 text-base text-slate-600 leading-relaxed">
              Sign in with your verified Kavach Passkey to check class schedules, submit assignments, track real-time attendance, and view semester grades.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3.5 pt-2">
            <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-xs">
              <span className="text-lg">📊</span>
              <h3 className="mt-1 text-xs font-bold text-slate-800">Real-Time Grades</h3>
              <p className="text-[11px] text-slate-500">Live GPA &amp; course assessment tracking</p>
            </div>
            <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-xs">
              <span className="text-lg">🗓️</span>
              <h3 className="mt-1 text-xs font-bold text-slate-800">Course Schedule</h3>
              <p className="text-[11px] text-slate-500">Daily lectures, labs and seminars</p>
            </div>
            <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-xs">
              <span className="text-lg">🤝</span>
              <h3 className="mt-1 text-xs font-bold text-slate-800">Assisted Sign-In</h3>
              <p className="text-[11px] text-slate-500">Guardian &amp; helper view-only mode enabled</p>
            </div>
            <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-xs">
              <span className="text-lg">🔒</span>
              <h3 className="mt-1 text-xs font-bold text-slate-800">Zero Passwords</h3>
              <p className="text-[11px] text-slate-500">Protected by device biometrics &amp; FIDO2</p>
            </div>
          </div>
        </div>

        {/* Right Column: Authentication Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 shadow-xl shadow-slate-200/50">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Student Sign-In</h2>
              <p className="text-xs text-slate-500 mt-0.5">Secure authentication via OpenID Connect</p>
            </div>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-700 text-lg font-bold">
              ID
            </span>
          </div>

          {error && (
            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-700 font-medium">
              {error}
            </div>
          )}

          {session ? (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
                <p className="text-xs font-medium text-emerald-800">Active session detected</p>
                <p className="text-sm font-bold text-emerald-950 mt-1">{session.name}</p>
                <p className="text-xs text-emerald-700">@{session.username}</p>
              </div>

              <Link
                href="/dashboard"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#4c0519] px-5 py-3 text-center text-sm font-semibold text-white transition hover:bg-[#701a2b] shadow-sm"
              >
                Continue to Dashboard →
              </Link>
            </div>
          ) : (
            <div className="mt-6 space-y-5">
              {/* Modern Kavach OIDC Button */}
              <div>
                <a
                  href="/api/auth/login"
                  className="group relative flex w-full items-center justify-center gap-3 rounded-xl bg-[#0b0f19] px-5 py-3.5 text-sm font-semibold text-white transition-all hover:bg-slate-900 shadow-md hover:shadow-lg active:scale-[0.99]"
                >
                  <svg viewBox="0 0 24 24" className="h-5 w-5 text-blue-400" fill="none" aria-hidden="true">
                    <path
                      d="M12 2.8 5 5.6v5.6c0 4.5 3 8.4 7 9.9 4-1.5 7-5.4 7-9.9V5.6l-7-2.8Z"
                      stroke="#3B82F6"
                      strokeWidth="2"
                      strokeLinejoin="round"
                    />
                    <path
                      d="m8.8 12.2 2.3 2.3 4.2-4.6"
                      stroke="#60A5FA"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>Continue with Kavach</span>
                  <span className="text-xs text-slate-400 group-hover:translate-x-0.5 transition-transform">→</span>
                </a>

                <div className="mt-2.5 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span>One-touch biometric sign-in via FIDO2 / WebAuthn</span>
                </div>
              </div>

              {/* Divider */}
              <div className="relative flex items-center justify-center">
                <div className="w-full border-t border-slate-200" />
                <span className="absolute bg-white px-3 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Retired Login
                </span>
              </div>

              {/* Disabled Legacy Password Form */}
              <div className="space-y-3 opacity-45 pointer-events-none select-none">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Student Roll Number
                  </label>
                  <input
                    disabled
                    tabIndex={-1}
                    value="2024-CSE-0841"
                    readOnly
                    className="w-full rounded-xl border border-slate-300 bg-slate-100 px-3.5 py-2 text-xs text-slate-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Password
                  </label>
                  <input
                    disabled
                    tabIndex={-1}
                    value="••••••••••••"
                    readOnly
                    type="password"
                    className="w-full rounded-xl border border-slate-300 bg-slate-100 px-3.5 py-2 text-xs text-slate-500"
                  />
                </div>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-[11px] text-amber-900 leading-relaxed">
                <span className="font-semibold">Notice:</span> Traditional passwords have been phased out across all campus services. Use <b>Continue with Kavach</b> above.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
