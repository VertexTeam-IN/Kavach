"use client";

import { useEffect, useRef } from "react";

/**
 * 3D Kavach Cyber Shield — Professional Enterprise Edition:
 *  - Sculpted 3D Cyber Shield with faceted beveled titanium armor plates;
 *  - Central biometric core featuring procedural fingerprint ridges and FIDO2 minutiae;
 *  - Dynamic moving laser beam with real-time cobalt light projection;
 *  - Dual counter-rotating holographic targeting reticles and pulsed defense forcefield;
 *  - Orbiting authenticated hardware devices (Phone, Laptop, Security Key) with
 *    bidirectional cryptographic challenge/signature data packets;
 *  - Professional cybersecurity lighting (electric cobalt + ice cyan + gold minutiae)
 *    with smooth cursor parallax.
 */
const DEVICES = [
  { id: "phone", label: "Phone · fingerprint" },
  { id: "laptop", label: "Laptop · Windows Hello" },
  { id: "key", label: "Security key · touch" },
];

export default function Globe3D({ className = "", onPointer }) {
  const canvasRef = useRef(null);
  const labelRefs = useRef([]);
  const onPointerRef = useRef(onPointer);
  onPointerRef.current = onPointer;

  useEffect(() => {
    let disposed = false;
    let cleanup = () => {};

    Promise.all([import("three"), import("three/addons/geometries/RoundedBoxGeometry.js")]).then(
      ([THREE, { RoundedBoxGeometry }]) => {
        if (disposed || !canvasRef.current) return;
        const canvas = canvasRef.current;
        const stage = canvas.parentElement;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
        camera.position.set(0, 0, 8.6);
        const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setClearColor(0x000000, 0);
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.25;

        // ---- Cyber Lighting: Metallic key, royal cobalt rim & ice cyan contrast
        scene.add(new THREE.AmbientLight(0xffffff, 1.4));
        const keyLight = new THREE.DirectionalLight(0xffffff, 3.8);
        keyLight.position.set(-3.5, 5, 5);
        scene.add(keyLight);

        const cobaltRim = new THREE.PointLight(0x3b82f6, 28, 14);
        cobaltRim.position.set(3.5, -1.2, 3);
        scene.add(cobaltRim);

        const cyberCyan = new THREE.PointLight(0x38bdf8, 18, 14);
        cyberCyan.position.set(-4.2, 1.5, -2.5);
        scene.add(cyberCyan);

        // Dynamic laser sweep light that tracks the scanning beam
        const laserLight = new THREE.PointLight(0x60a5fa, 8, 4);
        laserLight.position.set(0, 0.08, 0.4);
        scene.add(laserLight);

        const rig = new THREE.Group();
        scene.add(rig);

        // ---- The Kavach Cyber Shield Group
        const shieldGroup = new THREE.Group();
        rig.add(shieldGroup);

        // Helper: creates sharp heraldic/cyber shield 2D path
        const createShieldShape = (scale = 1.0) => {
          const s = new THREE.Shape();
          const w = 1.18 * scale;
          const topCrestY = 1.55 * scale;
          const topMidY = 1.48 * scale;
          const shoulderY = 0.55 * scale;
          const taperY = -0.38 * scale;
          const botTipY = -1.72 * scale;

          s.moveTo(0, topMidY);
          s.lineTo(w * 0.5, topCrestY);
          s.lineTo(w * 0.95, topCrestY * 0.92);
          s.quadraticCurveTo(w * 1.12, shoulderY, w * 0.98, taperY);
          s.quadraticCurveTo(w * 0.72, taperY - 0.55 * scale, 0, botTipY);
          s.quadraticCurveTo(-w * 0.72, taperY - 0.55 * scale, -w * 0.98, taperY);
          s.quadraticCurveTo(-w * 1.12, shoulderY, -w * 0.95, topCrestY * 0.92);
          s.lineTo(-w * 0.5, topCrestY);
          s.closePath();
          return s;
        };

        // 1. Outer Dark Titanium Armor Chassis (Beveled & Polished)
        const outerShape = createShieldShape(1.0);
        const outerGeo = new THREE.ExtrudeGeometry(outerShape, {
          depth: 0.16,
          bevelEnabled: true,
          bevelSegments: 5,
          steps: 1,
          bevelSize: 0.08,
          bevelThickness: 0.08,
        });
        const titaniumMat = new THREE.MeshStandardMaterial({
          color: 0x111622,
          metalness: 0.92,
          roughness: 0.2,
        });
        const outerShield = new THREE.Mesh(outerGeo, titaniumMat);
        outerShield.position.z = -0.16;
        shieldGroup.add(outerShield);

        // 2. Inner Recessed Carbon Shield Core
        const innerShape = createShieldShape(0.88);
        const innerGeo = new THREE.ExtrudeGeometry(innerShape, {
          depth: 0.09,
          bevelEnabled: true,
          bevelSegments: 4,
          steps: 1,
          bevelSize: 0.04,
          bevelThickness: 0.04,
        });
        const carbonMat = new THREE.MeshStandardMaterial({
          color: 0x1a2233,
          metalness: 0.7,
          roughness: 0.32,
        });
        const innerShield = new THREE.Mesh(innerGeo, carbonMat);
        innerShield.position.z = 0.02;
        shieldGroup.add(innerShield);

        // 3. Glowing Cobalt Circuit Perimeter
        const borderGeo = new THREE.BufferGeometry().setFromPoints(outerShape.getPoints(54));
        const borderLine = new THREE.Line(
          borderGeo,
          new THREE.LineBasicMaterial({ color: 0x3b82f6, linewidth: 2, transparent: true, opacity: 0.9 }),
        );
        borderLine.position.z = 0.14;
        shieldGroup.add(borderLine);

        // 4. Central Spine Ridge (Adds faceted 3D metallic highlights)
        const spineGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 1.48, 0.14),
          new THREE.Vector3(0, 0.8, 0.18),
          new THREE.Vector3(0, -0.7, 0.18),
          new THREE.Vector3(0, -1.68, 0.14),
        ]);
        const spineLine = new THREE.Line(
          spineGeo,
          new THREE.LineBasicMaterial({ color: 0x93c5fd, linewidth: 2, transparent: true, opacity: 0.85 }),
        );
        shieldGroup.add(spineLine);

        // 5. Procedural Biometric Sensor Texture (Fingerprint + Cyber Grids + Minutiae)
        const bioCanvas = document.createElement("canvas");
        bioCanvas.width = 1024;
        bioCanvas.height = 1024;
        const ctx = bioCanvas.getContext("2d");

        // Deep cyber backdrop
        ctx.fillStyle = "#0c111d";
        ctx.fillRect(0, 0, 1024, 1024);

        // Concentric radar grid
        ctx.strokeStyle = "#172338";
        ctx.lineWidth = 2.5;
        for (let r = 70; r < 500; r += 65) {
          ctx.beginPath();
          ctx.arc(512, 512, r, 0, Math.PI * 2);
          ctx.stroke();
        }
        // Degree crosshairs
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
          ctx.beginPath();
          ctx.moveTo(512, 512);
          ctx.lineTo(512 + Math.cos(a) * 470, 512 + Math.sin(a) * 470);
          ctx.stroke();
        }

        // Biometric Fingerprint Ridges
        let seed = 7719;
        const rand = () => {
          seed = (seed * 16807) % 2147483647;
          return (seed - 1) / 2147483646;
        };

        const cx = 512;
        const cy = 512;
        ctx.strokeStyle = "#7c8fa6";
        ctx.lineWidth = 5.2;
        ctx.lineCap = "round";

        for (let r = 24; r < 360; r += 16.5) {
          const gapAt = rand() * Math.PI * 2;
          const gapLen = rand() < 0.6 ? 0.22 + rand() * 0.42 : 0;
          ctx.beginPath();
          let pen = false;
          for (let t = 0; t <= Math.PI * 2 + 0.02; t += 0.035) {
            const inGap = gapLen && Math.abs(((t - gapAt + Math.PI * 3) % (Math.PI * 2)) - Math.PI) < gapLen;
            const wob = Math.sin(t * 3 + r * 0.065) * 4.6 + Math.sin(t * 7 + r * 0.125) * 2.6;
            const x = cx + Math.cos(t) * (r * 0.86 + wob);
            const y = cy + Math.sin(t) * (r * 1.08 + wob) - Math.max(0, Math.sin(t)) * r * 0.08;
            if (inGap) {
              pen = false;
              continue;
            }
            pen ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
            pen = true;
          }
          ctx.stroke();
        }

        // FIDO2 Minutiae Points (Warm Amber/Gold Nodes)
        for (let i = 0; i < 18; i++) {
          const a = rand() * Math.PI * 2;
          const r = 35 + rand() * 270;
          const px = cx + Math.cos(a) * (r * 0.86);
          const py = cy + Math.sin(a) * (r * 1.08);

          ctx.beginPath();
          ctx.arc(px, py, 7.5, 0, Math.PI * 2);
          ctx.fillStyle = "#f59e0b";
          ctx.fill();

          ctx.beginPath();
          ctx.moveTo(px, py);
          ctx.lineTo(px + (rand() - 0.5) * 44, py + (rand() - 0.5) * 44);
          ctx.strokeStyle = "#f59e0b88";
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        // Outer sensor boundary ring
        ctx.beginPath();
        ctx.arc(512, 512, 440, 0, Math.PI * 2);
        ctx.strokeStyle = "#3b82f6";
        ctx.lineWidth = 9;
        ctx.stroke();

        const bioTex = new THREE.CanvasTexture(bioCanvas);
        bioTex.colorSpace = THREE.SRGBColorSpace;
        bioTex.anisotropy = renderer.capabilities.getMaxAnisotropy();

        // 6. Central Biometric Scanner Disc
        const scannerMesh = new THREE.Mesh(
          new THREE.CircleGeometry(0.76, 64),
          new THREE.MeshStandardMaterial({
            map: bioTex,
            roughness: 0.28,
            metalness: 0.32,
            bumpMap: bioTex,
            bumpScale: 0.05,
          }),
        );
        scannerMesh.position.set(0, 0.06, 0.12);
        shieldGroup.add(scannerMesh);

        // 7. Counter-Rotating Holographic Reticles
        const holoRing1 = new THREE.Mesh(
          new THREE.RingGeometry(0.80, 0.84, 64),
          new THREE.MeshBasicMaterial({ color: 0x3b82f6, side: THREE.DoubleSide, transparent: true, opacity: 0.75 }),
        );
        holoRing1.position.set(0, 0.06, 0.16);
        shieldGroup.add(holoRing1);

        const holoRing2 = new THREE.Mesh(
          new THREE.RingGeometry(0.92, 0.95, 48),
          new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide, transparent: true, opacity: 0.55 }),
        );
        holoRing2.position.set(0, 0.06, 0.18);
        shieldGroup.add(holoRing2);

        // 8. Active Sweeping Laser Beam + Luminous Glow
        const laserBar = new THREE.Mesh(
          new RoundedBoxGeometry(1.44, 0.024, 0.016, 2, 0.005),
          new THREE.MeshBasicMaterial({ color: 0x93c5fd, transparent: true, opacity: 0.95 }),
        );
        laserBar.position.set(0, 0.06, 0.2);
        shieldGroup.add(laserBar);

        const laserGlow = new THREE.Mesh(
          new THREE.PlaneGeometry(1.44, 0.16),
          new THREE.MeshBasicMaterial({
            color: 0x3b82f6,
            transparent: true,
            opacity: 0.4,
            side: THREE.DoubleSide,
          }),
        );
        laserGlow.position.set(0, 0.06, 0.2);
        shieldGroup.add(laserGlow);

        // 9. Pulsing Defense Wave (Kavach Energy Field)
        const waveRing = new THREE.Mesh(
          new THREE.RingGeometry(0.7, 0.74, 48),
          new THREE.MeshBasicMaterial({ color: 0x3b82f6, side: THREE.DoubleSide, transparent: true, opacity: 0.6 }),
        );
        waveRing.position.set(0, 0.06, 0.15);
        shieldGroup.add(waveRing);

        // 10. Outer Faceted Holographic Defense Lattice
        const hexCage = new THREE.Mesh(
          new THREE.IcosahedronGeometry(2.05, 1),
          new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.2 }),
        );
        rig.add(hexCage);

        const hexInner = new THREE.Mesh(
          new THREE.IcosahedronGeometry(1.78, 1),
          new THREE.MeshBasicMaterial({ color: 0x3b82f6, wireframe: true, transparent: true, opacity: 0.15 }),
        );
        rig.add(hexInner);

        // ---- Authorized Hardware Authenticators
        const darkMat = new THREE.MeshStandardMaterial({ color: 0x192130, roughness: 0.35, metalness: 0.45 });
        const screenMat = new THREE.MeshStandardMaterial({
          color: 0x222e42,
          roughness: 0.2,
          metalness: 0.1,
          emissive: 0x0f1624,
        });
        const metalMat = new THREE.MeshStandardMaterial({ color: 0xc4c7ca, roughness: 0.25, metalness: 0.88 });
        const blueAccentMat = new THREE.MeshStandardMaterial({
          color: 0x3b82f6,
          roughness: 0.3,
          emissive: 0x2563eb,
          emissiveIntensity: 0.5,
        });

        const makePhone = () => {
          const g = new THREE.Group();
          g.add(new THREE.Mesh(new RoundedBoxGeometry(0.34, 0.66, 0.05, 4, 0.05), darkMat));
          const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.29, 0.56), screenMat);
          screen.position.z = 0.026;
          g.add(screen);
          const sensor = new THREE.Mesh(new THREE.RingGeometry(0.035, 0.05, 32), blueAccentMat);
          sensor.position.set(0, -0.17, 0.028);
          g.add(sensor);
          return g;
        };

        const makeLaptop = () => {
          const g = new THREE.Group();
          const base = new THREE.Mesh(new RoundedBoxGeometry(0.72, 0.035, 0.48, 3, 0.012), metalMat);
          g.add(base);
          const lid = new THREE.Group();
          lid.position.set(0, 0.018, -0.24);
          lid.rotation.x = -0.32;
          const lidBody = new THREE.Mesh(new RoundedBoxGeometry(0.72, 0.46, 0.025, 3, 0.012), metalMat);
          lidBody.position.y = 0.23;
          lid.add(lidBody);
          const display = new THREE.Mesh(new THREE.PlaneGeometry(0.64, 0.38), screenMat);
          display.position.set(0, 0.23, 0.014);
          lid.add(display);
          const shieldIcon = new THREE.Mesh(new THREE.CircleGeometry(0.045, 32), blueAccentMat);
          shieldIcon.position.set(0, 0.24, 0.016);
          lid.add(shieldIcon);
          g.add(lid);
          return g;
        };

        const makeKey = () => {
          const g = new THREE.Group();
          g.add(new THREE.Mesh(new RoundedBoxGeometry(0.42, 0.15, 0.055, 4, 0.03), darkMat));
          const plug = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.09, 0.025), metalMat);
          plug.position.x = 0.27;
          g.add(plug);
          const touch = new THREE.Mesh(new THREE.TorusGeometry(0.035, 0.009, 12, 32), blueAccentMat);
          touch.position.set(-0.08, 0, 0.03);
          g.add(touch);
          const hole = new THREE.Mesh(new THREE.TorusGeometry(0.028, 0.008, 12, 32), metalMat);
          hole.position.set(-0.17, 0, 0.03);
          g.add(hole);
          return g;
        };

        // Orbit plane
        const ORBIT_R = 2.65;
        const orbitRing = new THREE.Mesh(
          new THREE.TorusGeometry(ORBIT_R, 0.005, 6, 240),
          new THREE.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.32 }),
        );
        const orbitTilt = new THREE.Group();
        orbitTilt.rotation.set(0.38, 0, -0.12);
        rig.add(orbitTilt);
        orbitRing.rotation.x = Math.PI / 2;
        orbitTilt.add(orbitRing);

        const devicesRig = new THREE.Group();
        orbitTilt.add(devicesRig);

        const linkMat = new THREE.LineBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.38 });
        const challengePulseMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
        const signPulseMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });

        const devices = [makePhone(), makeLaptop(), makeKey()].map((mesh, i) => {
          const holder = new THREE.Group();
          const a = (i / 3) * Math.PI * 2 + 0.6;
          holder.position.set(Math.cos(a) * ORBIT_R, 0, Math.sin(a) * ORBIT_R);
          holder.add(mesh);
          devicesRig.add(holder);

          const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
          const line = new THREE.Line(lineGeo, linkMat);
          scene.add(line);

          // Challenge data packet traveling outbound
          const challengePulse = new THREE.Mesh(new THREE.SphereGeometry(0.032, 16, 12), challengePulseMat);
          scene.add(challengePulse);

          // Cryptographic signature packet traveling inbound
          const signPulse = new THREE.Mesh(new THREE.SphereGeometry(0.042, 16, 12), signPulseMat);
          scene.add(signPulse);

          return { holder, mesh, line, challengePulse, signPulse, offset: i * 0.33 };
        });

        // Floating ambient cyber dust particles
        const count = 180;
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
          const r = 2.5 + Math.random() * 2.5;
          const a = Math.random() * Math.PI * 2;
          const b = Math.acos(2 * Math.random() - 1);
          pos[i * 3] = r * Math.sin(b) * Math.cos(a);
          pos[i * 3 + 1] = r * Math.cos(b);
          pos[i * 3 + 2] = r * Math.sin(b) * Math.sin(a);
        }
        const pGeo = new THREE.BufferGeometry();
        pGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
        const particles = new THREE.Points(
          pGeo,
          new THREE.PointsMaterial({ color: 0xffffff, size: 0.013, transparent: true, opacity: 0.45 }),
        );
        scene.add(particles);

        // ---- Pointer tracking & card tilt feedback
        let targetX = 0;
        let targetY = 0;
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        const onMove = (e) => {
          const r = stage.getBoundingClientRect();
          const mx = ((e.clientX - r.left) / Math.max(r.width, 1) - 0.5) * 2;
          const my = ((e.clientY - r.top) / Math.max(r.height, 1) - 0.5) * 2;
          targetY = mx * 0.22;
          targetX = my * 0.16;
          onPointerRef.current?.(mx, my);
        };

        const onLeave = () => {
          targetX = 0;
          targetY = 0;
          onPointerRef.current?.(0, 0);
        };

        window.addEventListener("pointermove", onMove, { passive: true });
        document.addEventListener("pointerleave", onLeave);

        let width = 1;
        let height = 1;
        const resize = () => {
          const r = stage.getBoundingClientRect();
          width = Math.max(1, r.width);
          height = Math.max(1, r.height);
          renderer.setSize(width, height, false);
          camera.aspect = width / height;
          const vw = window.innerWidth;
          camera.position.z = vw <= 600 ? 9.8 : vw <= 1050 ? 9.2 : 8.6;
          camera.updateProjectionMatrix();
          rig.position.set(vw <= 1050 ? 0 : 0.12, 0, 0);
          rig.scale.setScalar(vw <= 600 ? 0.8 : vw <= 1050 ? 0.9 : 1);
        };

        const ro = new ResizeObserver(resize);
        ro.observe(stage);
        resize();

        const tmp = new THREE.Vector3();
        const center = new THREE.Vector3();
        const clock = new THREE.Clock();
        let raf = 0;

        const animate = () => {
          raf = requestAnimationFrame(animate);
          const t = clock.getElapsedTime();
          const m = reduced ? 0 : 1;

          // Shield gentle hover and pointer responsiveness
          shieldGroup.position.y = Math.sin(t * 1.4) * 0.05 * m;
          shieldGroup.rotation.y += (targetY - shieldGroup.rotation.y) * 0.04;
          shieldGroup.rotation.x += (-targetX - shieldGroup.rotation.x) * 0.04;

          // Holographic reticle spinning
          holoRing1.rotation.z = t * 0.45 * m;
          holoRing2.rotation.z = -t * 0.3 * m;

          // Biometric laser scanner sweeps across the fingerprint
          const laserY = 0.06 + Math.sin(t * 2.5) * 0.64 * m;
          laserBar.position.y = laserY;
          laserGlow.position.y = laserY;
          laserLight.position.y = laserY;

          // Pulsing defense wave
          const wavePhase = (t * 0.8) % 1;
          waveRing.scale.setScalar(1 + wavePhase * 1.4);
          waveRing.material.opacity = (1 - wavePhase) * 0.55;

          // Energy cage & particle drift
          hexCage.rotation.y = -t * 0.07 * m;
          hexCage.rotation.x = 0.16 + Math.sin(t * 0.25) * 0.08 * m;
          hexInner.rotation.y = t * 0.05 * m;
          devicesRig.rotation.y = t * 0.13 * m;
          particles.rotation.y = t * 0.01 * m;

          shieldGroup.getWorldPosition(center);

          devices.forEach((d, i) => {
            // Keep each device facing camera, with gentle float
            d.mesh.position.y = Math.sin(t * 0.85 + i * 2) * 0.08 * m;
            d.holder.getWorldPosition(tmp);
            d.mesh.lookAt(camera.position);

            // Connect cryptographic link from device directly to shield edge
            const edge = tmp.clone().sub(center).setLength(1.42).add(center);
            d.line.geometry.setFromPoints([tmp, edge]);

            // Outbound challenge packet (cyan)
            const p1 = (((t * 0.5 + d.offset) % 1) + 1) % 1;
            d.challengePulse.position.lerpVectors(edge, tmp, reduced ? 0.5 : p1);

            // Inbound cryptographic response packet (amber)
            const p2 = (((t * 0.5 + d.offset + 0.5) % 1) + 1) % 1;
            d.signPulse.position.lerpVectors(tmp, edge, reduced ? 0.5 : p2);
            d.signPulse.scale.setScalar(p2 < 0.5 ? 1 : 1.35);

            // Screen-space label projection
            const el = labelRefs.current[i];
            if (el) {
              const p = tmp.clone().add(new THREE.Vector3(0, -0.52, 0)).project(camera);
              const x = (p.x * 0.5 + 0.5) * width;
              const y = (-p.y * 0.5 + 0.5) * height;
              el.style.transform = `translate(-50%, 0) translate(${x}px, ${y}px)`;
              el.style.opacity = p.z < 1 ? "1" : "0";
            }
          });

          renderer.render(scene, camera);
        };
        animate();

        cleanup = () => {
          cancelAnimationFrame(raf);
          ro.disconnect();
          window.removeEventListener("pointermove", onMove);
          document.removeEventListener("pointerleave", onLeave);
          scene.traverse((o) => {
            o.geometry?.dispose();
            if (o.material) [].concat(o.material).forEach((mat) => mat.dispose());
          });
          bioTex.dispose();
          renderer.dispose();
        };
      },
    );

    return () => {
      disposed = true;
      cleanup();
    };
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        className={`absolute inset-0 block h-full w-full cursor-grab outline-none active:cursor-grabbing ${className}`}
        aria-label="Kavach Cyber Shield — 3D biometric armor emblem with orbiting devices authenticating via FIDO2 passkeys"
      />
      {DEVICES.map((d, i) => (
        <span
          key={d.id}
          ref={(el) => (labelRefs.current[i] = el)}
          className="pointer-events-none absolute left-0 top-0 z-[3] whitespace-nowrap rounded-full border border-slate-700 bg-slate-900/80 px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-300 backdrop-blur-md shadow-sm"
          style={{ opacity: 0 }}
        >
          {d.label}
        </span>
      ))}
    </>
  );
}
