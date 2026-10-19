import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { sounds } from '../lib/sound';

const STEPS = [
  { word: 'INITIALIZE', subtitle: 'Mounting local document store and offline state buffer' },
  { word: 'NODES', subtitle: 'Registering client device cryptographic signature and peers' },
  { word: 'DIFF3', subtitle: 'Activating 3-way merge matrix and honest conflict arbiter' },
  { word: 'READY', subtitle: 'SyncLab Studio initialized and offline-sync ready' },
];

interface Props {
  onDone: () => void;
}

export const Preloader: React.FC<Props> = ({ onDone }) => {
  const [count, setCount] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [isExiting, setIsExiting] = useState(false);
  const doneRef = useRef(onDone);

  useEffect(() => {
    doneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    // If on a mobile device or previously seen, bypass immediately
    const isMobile =
      typeof window !== 'undefined' &&
      (window.innerWidth <= 860 ||
        'ontouchstart' in window ||
        (navigator.maxTouchPoints && navigator.maxTouchPoints > 0));
    const seen = typeof window !== 'undefined' && localStorage.getItem('synclab_preloader_seen');

    if (isMobile || seen === 'true') {
      doneRef.current();
      return;
    }

    // High performance snappier duration (900ms total)
    const TOTAL_MS = 900;
    const start = performance.now();
    let frameId = 0;
    const timers: number[] = [];

    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / TOTAL_MS, 1);

      const eased =
        progress < 0.75
          ? (progress / 0.75) * 0.85
          : 0.85 + Math.pow((progress - 0.75) / 0.25, 2) * 0.15;

      const currentVal = Math.min(Math.round(eased * 100), 100);
      setCount(currentVal);

      const idx = Math.min(Math.floor((currentVal / 100) * 4), 3);
      setStepIndex(currentVal >= 100 ? 3 : idx);

      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      } else {
        localStorage.setItem('synclab_preloader_seen', 'true');
        timers.push(
          window.setTimeout(() => {
            setIsExiting(true);
            sounds.playSuccess();
            timers.push(
              window.setTimeout(() => {
                doneRef.current();
              }, 400)
            );
          }, 150)
        );
      }
    };

    frameId = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frameId);
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, []);

  const handleSkip = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      localStorage.setItem('synclab_preloader_seen', 'true');
    } catch {
      /* ignore */
    }
    sounds.playTap();
    setIsExiting(true);
    setTimeout(() => {
      doneRef.current();
    }, 250);
  };

  const activeStep = STEPS[stepIndex] || STEPS[0];

  return (
    <div onClick={() => handleSkip()} style={{ cursor: 'pointer' }}>
      <motion.div
        className="clean-preloader-backdrop synclab-preloader-backdrop"
        initial={{ y: 0 }}
        animate={isExiting ? { y: '-100%' } : { y: 0 }}
        transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
        aria-hidden="true"
      />

      <motion.div
        className="clean-preloader synclab-preloader"
        initial={{ y: 0 }}
        animate={isExiting ? { y: '-100%' } : { y: 0 }}
        transition={{ duration: 0.45, ease: [0.76, 0, 0.24, 1] }}
        aria-hidden="true"
      >
        <div className="clean-ambient-glow synclab-ambient-glow" />

        {/* Top precision telemetry bar */}
        <div className="clean-top-bar">
          <div className="clean-progress-track" />
          <div className="clean-progress-fill synclab-progress-fill" style={{ width: `${count}%` }}>
            <span className="clean-progress-spark" />
          </div>
        </div>

        {/* Tactical HUD Header */}
        <header className="clean-hud-header">
          <div className="clean-hud-left">
            <span className="clean-beacon-dot" />
            <span className="clean-hud-title">SyncLab Studio</span>
          </div>
          <div className="clean-hud-right">
            <button className="clean-skip-btn" onClick={handleSkip} title="Skip loading sequence">
              Skip (Tap Anywhere)
            </button>
          </div>
        </header>

        {/* Centered Typography */}
        <motion.div
          className="clean-center-box"
          animate={isExiting ? { opacity: 0, y: -24, scale: 0.98 } : { opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className="clean-category-badge">
            <span>Offline-First Distributed Engine · Version 1.0</span>
          </div>

          <div className="clean-word-wrapper">
            <motion.h2
              className="clean-kinetic-word"
              key={activeStep.word}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -20, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            >
              {activeStep.word}
            </motion.h2>
          </div>

          <motion.p
            className="clean-kinetic-subtitle"
            key={activeStep.subtitle}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            {activeStep.subtitle}
          </motion.p>

          <div className="clean-counter-block">
            <span className="clean-counter-digits">
              {count < 10 ? `00${count}` : count < 100 ? `0${count}` : count}
            </span>
            <span className="clean-counter-unit synclab-unit">%</span>
          </div>
        </motion.div>

        {/* Tactical Bottom Telemetry */}
        <footer className="clean-hud-footer">
          <div className="clean-footer-col">
            <span className="clean-col-label">MERGE ENGINE</span>
            <span className="clean-col-val">3-WAY LINE MERGE · DIFF3</span>
          </div>
          <div className="clean-footer-col center">
            <span className="clean-col-label">CONFLICT MODEL</span>
            <span className="clean-col-val">HONEST EXPLICIT · ZERO OVERWRITE</span>
          </div>
          <div className="clean-footer-col right">
            <span className="clean-col-label">DESIGN ARCHITECTURE</span>
            <span className="clean-col-val">APPLE LIQUID GLASS · ADM</span>
          </div>
        </footer>

        {/* Curved Exit Arch */}
        <svg className="clean-preloader-curve synclab-preloader-curve" viewBox="0 0 1440 120" preserveAspectRatio="none">
          <path d="M0,120 L0,50 Q720,0 1440,50 L1440,120 Z" />
        </svg>
      </motion.div>
    </div>
  );
};
