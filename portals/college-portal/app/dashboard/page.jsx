import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";

const COURSES = [
  {
    code: "CSE301",
    name: "Computer Networks & Distributed Systems",
    instructor: "Dr. Arvind Mehta",
    attendance: 86,
    grade: "A",
    status: "Assignment Due in 2 days",
  },
  {
    code: "CSE305",
    name: "Information Security & Cryptography",
    instructor: "Prof. Sunita Rao",
    attendance: 92,
    grade: "A+",
    status: "Lab Verified ✓",
  },
  {
    code: "CSE311",
    name: "Database Systems & Engineering",
    instructor: "Dr. K. Raman",
    attendance: 78,
    grade: "B+",
    status: "Quiz Scheduled",
  },
];

export default async function Dashboard() {
  const s = await getSession();
  if (!s) redirect("/");
  const readOnly = s.assisted;

  return (
    <div className="space-y-6">
      {/* Assisted Mode Banner */}
      {readOnly && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50/90 p-5 text-amber-950 shadow-xs">
          <div className="flex items-start gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-200 text-base">
              ⚠️
            </span>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold tracking-tight">
                  Assisted Session Active · View-Only Mode
                </h3>
                <span className="rounded-full bg-amber-200/80 px-2.5 py-0.5 text-[10px] font-semibold text-amber-800">
                  acr: assisted
                </span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed">
                Kavach confirmed this sign-in was approved by your trusted helper{" "}
                <b className="font-semibold text-amber-950">{s.assistedBy ?? "a trusted helper"}</b> with their passkey.
                In accordance with academic security policies, you may view records and attendance, but grade submissions and profile changes are locked.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Student Profile Card */}
      <div className="flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#4c0519] to-[#701a2b] font-bold text-white text-xl shadow-sm">
            {s.name ? s.name.charAt(0) : "S"}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">{s.name}</h1>
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide ${
                readOnly
                  ? "border border-amber-300 bg-amber-50 text-amber-800"
                  : "border border-emerald-300 bg-emerald-50 text-emerald-800"
              }`}>
                {readOnly ? "View-Only Access" : "Direct Passkey Verified ✓"}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-2">
              <span>@{s.username}</span>
              <span>•</span>
              <span>B.Tech Computer Science (Semester 5)</span>
              <span>•</span>
              <span className="font-mono text-slate-400">ID: {s.sub.slice(0, 8)}…</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            disabled={readOnly}
            className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            title={readOnly ? "Disabled in assisted session" : undefined}
          >
            Edit Profile
          </button>
          <a
            href="/api/auth/logout"
            className="rounded-xl bg-[#4c0519] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#701a2b] shadow-xs"
          >
            Sign Out
          </a>
        </div>
      </div>

      {/* Key Academic Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Cumulative GPA</p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900">3.84 <span className="text-xs text-slate-400 font-normal">/ 4.00</span></p>
          <p className="mt-1 text-[11px] font-medium text-emerald-600">Top 5% in class</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Overall Attendance</p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900">85.3%</p>
          <p className="mt-1 text-[11px] font-medium text-slate-500">Required min: 75%</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Earned Credits</p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900">18 <span className="text-xs text-slate-400 font-normal">/ 24</span></p>
          <p className="mt-1 text-[11px] font-medium text-slate-500">Full-time status</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Midterm Schedule</p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900">2 <span className="text-xs text-slate-400 font-normal">Pending</span></p>
          <p className="mt-1 text-[11px] font-medium text-rose-600">Starts in 10 days</p>
        </div>
      </div>

      {/* Courses & Grades Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Enrolled Courses &amp; Continuous Assessment</h2>
            <p className="text-xs text-slate-500">Fall Semester 2026 course evaluations and attendance</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
            3 Active Courses
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/80 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5">Course Code &amp; Title</th>
                <th className="px-6 py-3.5">Instructor</th>
                <th className="px-6 py-3.5">Attendance</th>
                <th className="px-6 py-3.5">Current Grade</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {COURSES.map((c) => (
                <tr key={c.code} className="hover:bg-slate-50/50 transition">
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-900">{c.code}</div>
                    <div className="text-xs text-slate-500">{c.name}</div>
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-600 font-medium">
                    {c.instructor}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="h-2 w-24 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            c.attendance >= 85 ? "bg-emerald-500" : c.attendance >= 75 ? "bg-amber-500" : "bg-rose-500"
                          }`}
                          style={{ width: `${c.attendance}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-slate-700">{c.attendance}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-800">
                      {c.grade}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      disabled={readOnly}
                      className="rounded-lg bg-[#4c0519] px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-[#701a2b] disabled:opacity-35 disabled:cursor-not-allowed shadow-2xs"
                      title={readOnly ? "Disabled in view-only assisted mode" : undefined}
                    >
                      {readOnly ? "Locked (Assisted)" : "Submit Assignment"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
