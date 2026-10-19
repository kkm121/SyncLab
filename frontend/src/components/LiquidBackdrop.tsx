import React, { useEffect, useRef } from 'react';

/**
 * Liquid Glass Aurora Canvas for SyncLab.
 * Optimized with Adaptive Performance System:
 * - On Mobile / Low-Power phones (e.g. Xiaomi 12 Pro & mid-to-low end Androids):
 *   Runs in zero-overhead CSS mode with no requestAnimationFrame loop, preventing GPU
 *   thermal throttling, input lag, and frame drops.
 * - On Desktop / Ultra mode:
 *   Runs frame-rate capped organic fluid motion with tab-visibility sleep.
 */
interface Props {
  performanceMode?: 'ultra' | 'balanced' | 'lite';
}

export const LiquidBackdrop: React.FC<Props> = ({ performanceMode = 'balanced' }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Check if current device is a mobile phone, touch device, or small screen
  const isMobileDevice = (() => {
    if (typeof window === 'undefined') return false;
    const isTouch = 'ontouchstart' in window || (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
    const isSmall = window.innerWidth <= 860;
    const isLowPower =
      (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) ||
      ((navigator as any).deviceMemory && (navigator as any).deviceMemory <= 4);
    return isTouch || isSmall || isLowPower;
  })();

  const useStaticAurora = performanceMode === 'lite' || (performanceMode === 'balanced' && isMobileDevice);

  useEffect(() => {
    if (useStaticAurora) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    // Use a reduced buffer resolution for high-DPI displays to eliminate fill-rate contention
    let width = (canvas.width = Math.max(320, Math.floor(window.innerWidth / 3)));
    let height = (canvas.height = Math.max(240, Math.floor(window.innerHeight / 3)));

    let mouseX = width / 2;
    let mouseY = height / 2;
    let targetMouseX = mouseX;
    let targetMouseY = mouseY;

    const handlePointerMove = (e: PointerEvent) => {
      // Ignore coarse touch pointers to save cycles
      if (e.pointerType === 'touch') return;
      targetMouseX = (e.clientX / window.innerWidth) * width;
      targetMouseY = (e.clientY / window.innerHeight) * height;
    };
    window.addEventListener('pointermove', handlePointerMove, { passive: true });

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = Math.max(320, Math.floor(window.innerWidth / 3));
      height = canvas.height = Math.max(240, Math.floor(window.innerHeight / 3));
    };
    window.addEventListener('resize', handleResize, { passive: true });

    // Multi-color vibrant orbs for SyncLab (Teal, Emerald, Sapphire, Cyan)
    const orbs = [
      { x: width * 0.22, y: height * 0.26, radius: 140, vx: 0.6, vy: 0.4, colorDark: '#059669', colorLight: '#34d399' },
      { x: width * 0.82, y: height * 0.32, radius: 150, vx: -0.5, vy: 0.7, colorDark: '#0284c7', colorLight: '#38bdf8' },
      { x: width * 0.52, y: height * 0.75, radius: 160, vx: 0.7, vy: -0.5, colorDark: '#4f46e5', colorLight: '#818cf8' },
      { x: width * 0.88, y: height * 0.82, radius: 130, vx: -0.4, vy: -0.6, colorDark: '#10b981', colorLight: '#6ee7b7' },
      { x: width * 0.16, y: height * 0.84, radius: 135, vx: 0.5, vy: 0.5, colorDark: '#06b6d4', colorLight: '#67e8f9' },
    ];

    let animId = 0;
    let isVisible = !document.hidden;
    const handleVis = () => {
      isVisible = !document.hidden;
      if (isVisible) {
        lastTime = performance.now();
        animId = requestAnimationFrame(renderLoop);
      } else {
        cancelAnimationFrame(animId);
      }
    };
    document.addEventListener('visibilitychange', handleVis);

    let isDark = document.documentElement.dataset.theme !== 'light';
    const themeObserver = new MutationObserver(() => {
      isDark = document.documentElement.dataset.theme !== 'light';
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    let time = 0;
    let lastTime = performance.now();
    const targetFps = performanceMode === 'ultra' ? 60 : 30;
    const frameInterval = 1000 / targetFps;

    const renderLoop = (now: number) => {
      if (!isVisible) return;
      animId = requestAnimationFrame(renderLoop);

      const elapsed = now - lastTime;
      if (elapsed < frameInterval) return;
      lastTime = now - (elapsed % frameInterval);

      time += 0.012;

      mouseX += (targetMouseX - mouseX) * 0.04;
      mouseY += (targetMouseY - mouseY) * 0.04;

      ctx.clearRect(0, 0, width, height);

      ctx.save();
      ctx.globalCompositeOperation = isDark ? 'screen' : 'multiply';

      for (let i = 0; i < orbs.length; i++) {
        const orb = orbs[i];
        const ox = orb.x + Math.sin(time + i * 1.4) * 60 + (mouseX - width / 2) * (0.05 * (i + 1));
        const oy = orb.y + Math.cos(time + i * 1.7) * 45 + (mouseY - height / 2) * (0.05 * (i + 1));

        const grad = ctx.createRadialGradient(ox, oy, 6, ox, oy, orb.radius);
        const col = isDark ? orb.colorDark : orb.colorLight;

        grad.addColorStop(0, isDark ? `${col}cc` : `${col}77`);
        grad.addColorStop(0.35, isDark ? `${col}66` : `${col}33`);
        grad.addColorStop(0.75, isDark ? `${col}18` : `${col}0a`);
        grad.addColorStop(1, 'transparent');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(ox, oy, orb.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();
    };

    animId = requestAnimationFrame(renderLoop);

    return () => {
      isVisible = false;
      themeObserver.disconnect();
      cancelAnimationFrame(animId);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', handleVis);
    };
  }, [useStaticAurora, performanceMode]);

  return (
    <>
      {useStaticAurora ? (
        <div className="liquid-aurora-fallback" aria-hidden="true" />
      ) : (
        <canvas ref={canvasRef} className="liquid-aurora-canvas" aria-hidden="true" />
      )}
      <div className="liquid-noise-overlay" aria-hidden="true" />
    </>
  );
};
