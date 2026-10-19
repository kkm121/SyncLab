import React, { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';

export const CursorGlow: React.FC = () => {
  const [enabled] = useState(() => {
    if (typeof window === 'undefined') return false;
    const isTouch = 'ontouchstart' in window || (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
    const isMobile = window.innerWidth <= 860;
    if (isTouch || isMobile) return false;
    return Boolean(
      window.matchMedia?.('(pointer: fine)').matches &&
      !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    );
  });

  const x = useMotionValue(-600);
  const y = useMotionValue(-600);
  const sx = useSpring(x, { stiffness: 90, damping: 22 });
  const sy = useSpring(y, { stiffness: 90, damping: 22 });

  useEffect(() => {
    if (!enabled) return;
    const onMove = (e: PointerEvent) => {
      if (e.pointerType === 'touch') return;
      x.set(e.clientX);
      y.set(e.clientY);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => window.removeEventListener('pointermove', onMove);
  }, [enabled, x, y]);

  if (!enabled) return null;
  return <motion.div className="cursor-glow synclab-cursor-glow" style={{ x: sx, y: sy }} aria-hidden="true" />;
};
