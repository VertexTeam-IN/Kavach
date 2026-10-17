import { notFound } from "next/navigation";

import AttackLab from "@/components/attack-lab";

// DEMO ONLY. The page exists only when KAVACH_ENABLE_LAB=1 (frontend/.env.local);
// otherwise /lab is a normal 404. It is deliberately not linked from the site navigation.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Attack Lab — Kavach",
  robots: { index: false, follow: false },
};

export default function LabPage() {
  if (process.env.KAVACH_ENABLE_LAB !== "1") notFound();
  return <AttackLab />;
}
