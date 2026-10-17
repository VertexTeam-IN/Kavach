"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Brand } from "@/components/ui";
import { api } from "@/lib/api";

import s from "./home.module.css";

// WebGL only runs in the browser; load the 3D scene after the page is interactive.
const Globe3D = dynamic(() => import("@/components/Globe3D"), { ssr: false });

const TITLE = ["Next-Generation", "Passwordless Identity", "For Every"];
const TITLE_ACCENT = "Application";

// What happens during an authentic passkey ceremony
const FLOW = [
  { step: "Challenge", text: "Kavach generates a cryptographic 32-byte one-time challenge." },
  { step: "Hardware Enclave", text: "Your device's TPM / Secure Enclave verifies your biometrics and signs the challenge." },
  { step: "Origin Verified", text: "Kavach verifies the asymmetric signature against origin. Instant single-touch access." },
];

const PLATFORMS = "ANDROID · IPHONE · WINDOWS HELLO · MACOS · SECURITY KEYS";

const STEPS = [
  {
    n: "01",
    title: "Hardware-bound passkeys",
    text: "Cryptographic key pairs are generated inside your device's Secure Enclave or TPM and unlocked by biometrics. The private key never leaves your machine.",
  },
  {
    n: "02",
    title: "Phishing-resistant by design",
    text: "Passkey signatures are cryptographically bound to the real domain. Look-alike phishing sites and credential relays are mathematically rejected.",
  },
  {
    n: "03",
    title: "Inclusive assisted sign-in",
    text: "Citizens who cannot operate a passkey can be securely assisted by a trusted helper with number-matching verification, keeping the session view-only.",
  },
];

export default function Home() {
  const [me, setMe] = useState(null);
  const [apiUp, setApiUp] = useState(null); // null = checking
  const [flowStep, setFlowStep] = useState(0);
  const signinCard = useRef(null);
  const statusCard = useRef(null);

  useEffect(() => {
    api("/api/me")
      .then(setMe)
      .catch(() => setMe(null));
    api("/api/health")
      .then((h) => setApiUp(!!h?.ok))
      .catch(() => setApiUp(false));
    const id = setInterval(() => setFlowStep((n) => (n + 1) % FLOW.length), 2600);
    return () => clearInterval(id);
  }, []);

  // Subtle 3D tilt of the glass cards that follows the pointer (set directly, no re-render).
  const tilt = useCallback((x, y) => {
    if (signinCard.current)
      signinCard.current.style.transform = `perspective(900px) rotateY(${x * 4}deg) rotateX(${-y * 3}deg)`;
    if (statusCard.current)
      statusCard.current.style.transform = `perspective(900px) rotateY(${-x * 3}deg) rotateX(${y * 2}deg)`;
  }, []);

  return (
    <>
      <div className={s.shell}>
        <header className={s.header}>
          <Brand />
          <nav className={s.nav} aria-label="Main navigation">
            <a href="#how">How it works</a>
            <Link href="/assist">Assisted sign-in</Link>
            <Link href="/recover">Recovery</Link>
            <a href="#websites">For developers</a>
          </nav>
          <div className={s.headerActions}>
            {me ? (
              <Link className={s.headerCta} href="/dashboard">
                {me.display_name} →
              </Link>
            ) : (
              <>
                <Link className={s.headerLink} href="/register">
                  Create account
                </Link>
                <Link className={s.headerCta} href="/login">
                  Sign in
                </Link>
              </>
            )}
          </div>
        </header>

        <main className={s.hero} id="home">
          <section className={s.copy} aria-labelledby="hero-title">
            <div className={s.eyebrow}>
              <span>01</span>
              <span className={s.eyebrowLine} />
              <span>ENTERPRISE PASSKEY PLATFORM · CC6-IC04</span>
            </div>
            <h1 id="hero-title" className={s.title}>
              {TITLE.map((line, i) => (
                <span key={line} style={{ animationDelay: `${0.22 + i * 0.08}s` }}>
                  {line}
                </span>
              ))}
              <span className={s.accent} style={{ animationDelay: `${0.22 + TITLE.length * 0.08}s` }}>
                {TITLE_ACCENT}
              </span>
            </h1>
            <div className={s.bottom}>
              <a className={s.serviceLink} href="#how">
                Architecture overview <span>⌄</span>
              </a>
              {me ? (
                <Link className={s.mainCta} href="/dashboard">
                  <span>Continue as {me.display_name}</span>
                  <span className={s.arrowDisc}>↗</span>
                </Link>
              ) : (
                <Link className={s.mainCta} href="/login">
                  <span>Sign in with passkey</span>
                  <span className={s.arrowDisc}>↗</span>
                </Link>
              )}
            </div>
            <p className={s.note}>
              <span className={s.noteDot} />
              <span>
                Phishing-resistant biometrics built on FIDO2 and OpenID Connect. Eliminates password leaks
                and SMS OTP vulnerabilities for modern digital services.
              </span>
            </p>
          </section>

          <div className={s.stage} aria-label="Interactive 3D illustration of a protected identity">
            <Globe3D onPointer={tilt} />
            <div className={`${s.label} ${s.labelTop}`}>FIDO2 &nbsp;/&nbsp; WEBAUTHN</div>

            <div className={`${s.glass} ${s.signinCard}`} ref={signinCard}>
              <div className={s.cardTop}>
                <span className={s.cardLabel}>{me ? "Active Session" : "Authentication Protocol"}</span>
                {apiUp !== null && (
                  <span className={`${s.pill} ${apiUp ? "" : s.pillOff}`}>{apiUp ? "LIVE" : "OFFLINE"}</span>
                )}
              </div>
              {me ? (
                <>
                  <div className={s.bigNumber}>
                    {me.display_name}
                    <small>{me.is_assisted ? `ASSISTED BY ${me.assisted_by?.toUpperCase()}` : "HARDWARE PASSKEY VERIFIED"}</small>
                  </div>
                  <div className={s.cardSub}>
                    {me.is_assisted ? "View-only assisted session" : "Enterprise full access"} · expires{" "}
                    {new Date(me.session_expires_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                  <Link href="/dashboard" className={s.cardLink}>
                    Open security console →
                  </Link>
                </>
              ) : (
                <>
                  <div className={s.bigNumber} aria-live="polite">
                    {FLOW[flowStep].step}
                    <small>STEP {flowStep + 1} / 3</small>
                  </div>
                  <div className={s.cardSub}>{FLOW[flowStep].text}</div>
                  <div className={s.flow}>
                    {FLOW.map((f, i) => (
                      <div key={f.step} className={`${s.flowStep} ${i === flowStep ? s.flowActive : ""}`}>
                        <b>0{i + 1}</b>
                        {f.step}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div className={`${s.glass} ${s.statusCard}`} ref={statusCard}>
              <div className={s.statusHead}>
                <span className={s.cardLabel}>{me ? "Account Security Status" : "Security Guarantees"}</span>
                <span className={s.statusCheck}>✓</span>
              </div>
              <div className={s.statusList}>
                {(me
                  ? [
                      { k: "Registered passkeys", v: String(me.passkey_count), ok: me.passkey_count > 0 },
                      { k: "Backup authenticator", v: me.has_backup ? "ENROLLED" : "RECOMMENDED", ok: me.has_backup, href: "/dashboard" },
                      {
                        k: "Emergency recovery key",
                        v: me.has_recovery_code ? "SECURED" : "MISSING",
                        ok: me.has_recovery_code,
                        href: "/dashboard",
                      },
                    ]
                  : [
                      { k: "Phishing immunity", v: "ENFORCED", ok: true },
                      { k: "Replay resistance", v: "ACTIVE", ok: true },
                      { k: "Passwords stored", v: "ZERO", ok: true },
                    ]
                ).map((row) => (
                  <div key={row.k}>
                    <div className={s.statusRow}>
                      <span>{row.k}</span>
                      {row.href && !row.ok ? (
                        <Link href={row.href} className={s.fixLink}>
                          {row.v} →
                        </Link>
                      ) : (
                        <strong className={row.ok ? "" : s.bad}>{row.v}</strong>
                      )}
                    </div>
                    <div className={s.track}>
                      <span className={row.ok ? "" : s.trackBad} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className={s.chip}>
              <b>●</b>{" "}
              {apiUp === null ? "CHECKING SYSTEM STATUS…" : apiUp ? "ALL IDENTITY SERVICES OPERATIONAL" : "API OFFLINE — START BACKEND"}
            </div>
            <div className={`${s.label} ${s.labelBottom}`}>PHISHING-RESISTANT BY ARCHITECTURE</div>
          </div>

          <div className={s.scrollCue}>
            <span className={s.scrollLine} /> SUPPORTS {PLATFORMS}
          </div>
          <div className={s.index}>
            KAVACH <b>—</b> CC6-IC04 · 2026
          </div>
        </main>
      </div>

      <section className={s.section} id="how">
        <div className={s.sectionHead}>
          <div>
            <div className="kv-eyebrow">02 · Architecture</div>
            <h2 className={s.sectionTitle}>
              Zero passwords to steal.
              <br />
              <span className={s.accent}>Cryptographic certainty.</span>
            </h2>
          </div>
          <p className={s.sectionLead}>
            Kavach eliminates passwords and SMS OTPs with passkeys — the open FIDO2 / WebAuthn standard
            natively integrated into modern smartphones, computers and hardware security keys.
          </p>
        </div>
        <div className={s.steps}>
          {STEPS.map((st) => (
            <article key={st.n} className={s.step}>
              <div className={s.stepNum}>{st.n}</div>
              <h3 className={s.stepTitle}>{st.title}</h3>
              <p className={s.stepText}>{st.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={s.band} id="websites">
        <div>
          <div className="kv-eyebrow" style={{ color: "#ffffff90" }}>
            03 · Developer Integration
          </div>
          <h2 className={s.bandTitle}>
            Add &ldquo;Continue with Kavach&rdquo;
            <br />
            <span className={s.accent}>via Standard OpenID Connect.</span>
          </h2>
        </div>
        <div>
          <p className={s.bandText}>
            Kavach is a compliant OpenID Connect provider. Any university, government portal,
            or enterprise application can deploy phishing-proof sign-in with standard OIDC libraries —
            with full granular control over assisted, view-only session policies.
          </p>
          <div className={s.bandLinks}>
            <Link className={s.mainCta} href="/register">
              <span>Create developer account</span>
              <span className={s.arrowDisc}>↗</span>
            </Link>
            <a className={s.ghostBtn} href="http://127.0.0.1:3001" target="_blank" rel="noreferrer">
              Try the College Portal Demo
            </a>
          </div>
        </div>
      </section>

      <footer className={s.footer}>
        <span>KAVACH · NEXT-GENERATION PASSWORDLESS IDENTITY</span>
        <span>FIDO2 / WEBAUTHN · OPENID CONNECT</span>
      </footer>
    </>
  );
}
