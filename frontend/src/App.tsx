import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { LiquidBackdrop } from './components/LiquidBackdrop';
import { CursorGlow } from './components/CursorGlow';
import { Preloader } from './components/Preloader';
import { Header } from './components/Header';
import { DocumentStudio } from './components/DocumentStudio';
import { ConflictSimulator } from './components/ConflictSimulator';
import { DeviceFleet } from './components/DeviceFleet';
import { ObsidianExportModal } from './components/ObsidianExportModal';

export const App: React.FC = () => {
  const [showPreloader, setShowPreloader] = useState(true);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('synclab_theme') as 'dark' | 'light') || 'dark';
  });

  // Performance Mode: 'lite' for 120 FPS high-refresh mobile & low-end devices, 'ultra' for high-end desktop
  const [performanceMode, setPerformanceMode] = useState<'ultra' | 'balanced' | 'lite'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('synclab_perf_mode') as 'ultra' | 'balanced' | 'lite' | null;
      if (saved && ['ultra', 'balanced', 'lite'].includes(saved)) return saved;
      const isMobile =
        window.innerWidth <= 860 ||
        'ontouchstart' in window ||
        (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
      const isLowPower =
        (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) ||
        ((navigator as any).deviceMemory && (navigator as any).deviceMemory <= 4);
      if (isMobile || isLowPower) return 'lite';
    }
    return 'balanced';
  });

  const [activeTab, setActiveTab] = useState<'studio' | 'simulator' | 'devices'>('studio');
  const [audioEnabled, setAudioEnabled] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('gdg-sound-enabled');
      if (saved !== null) return saved === 'true';
      // Mute audio by default on mobile phones to eliminate Web Audio latency
      const isMobile = window.innerWidth <= 860 || 'ontouchstart' in window;
      return !isMobile;
    }
    return true;
  });
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [obsidianDocId, setObsidianDocId] = useState<number | null>(null);

  // Synchronize theme with document element
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('synclab_theme', theme);
  }, [theme]);

  // Synchronize performance mode with document element
  useEffect(() => {
    document.documentElement.dataset.performance = performanceMode;
    localStorage.setItem('synclab_perf_mode', performanceMode);
  }, [performanceMode]);

  const flashNotice = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  return (
    <div className="whistle-studio-app synclab-app">
      {/* Luxury Skippable Preloader */}
      <AnimatePresence>
        {showPreloader && <Preloader onDone={() => setShowPreloader(false)} />}
      </AnimatePresence>

      {/* Dynamic Colorful Liquid Mesh & Ambient Glow */}
      <LiquidBackdrop performanceMode={performanceMode} />
      <CursorGlow />

      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        audioEnabled={audioEnabled}
        setAudioEnabled={setAudioEnabled}
        theme={theme}
        setTheme={setTheme}
        performanceMode={performanceMode}
        setPerformanceMode={setPerformanceMode}
      />

      <main className="studio-main-content">
        <AnimatePresence mode="wait">
          {activeTab === 'studio' && (
            <motion.div
              key="studio"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
            >
              <DocumentStudio
                flashNotice={flashNotice}
                onOpenObsidianExport={(id) => setObsidianDocId(id)}
              />
            </motion.div>
          )}

          {activeTab === 'simulator' && (
            <motion.div
              key="simulator"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
            >
              <ConflictSimulator flashNotice={flashNotice} />
            </motion.div>
          )}

          {activeTab === 'devices' && (
            <motion.div
              key="devices"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
            >
              <DeviceFleet flashNotice={flashNotice} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Obsidian Export Modal */}
      <AnimatePresence>
        {obsidianDocId !== null && (
          <ObsidianExportModal
            docId={obsidianDocId}
            onClose={() => setObsidianDocId(null)}
            flashNotice={flashNotice}
          />
        )}
      </AnimatePresence>

      {/* Interactive Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            className="toast-notification"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            transition={{ duration: 0.2 }}
          >
            <span className="toast-beacon" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="studio-footer">
        <div className="footer-content">
          <span>SyncLab Architecture · Offline-First Document Engine · 3-Way Line Merge (diff3) · Zero Silent Overwrite</span>
          <span className="footer-tag">GDG on Campus SRM · Distributed Systems & Offline-First Track</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
