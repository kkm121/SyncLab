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
  const [activeTab, setActiveTab] = useState<'studio' | 'simulator' | 'devices'>('studio');
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [obsidianDocId, setObsidianDocId] = useState<number | null>(null);

  // Synchronize theme with document element
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('synclab_theme', theme);
  }, [theme]);

  const flashNotice = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  return (
    <div className="whistle-studio-app synclab-app">
      {/* Luxury Skippable Preloader */}
      <AnimatePresence>
        {showPreloader && <Preloader onDone={() => setShowPreloader(false)} />}
      </AnimatePresence>

      {/* Dynamic Colorful Liquid Mesh & Ambient Glow */}
      <LiquidBackdrop />
      <CursorGlow />

      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        audioEnabled={audioEnabled}
        setAudioEnabled={setAudioEnabled}
        theme={theme}
        setTheme={setTheme}
      />

      <main className="studio-main-content">
        <AnimatePresence mode="wait">
          {activeTab === 'studio' && (
            <motion.div
              key="studio"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
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
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <ConflictSimulator flashNotice={flashNotice} />
            </motion.div>
          )}

          {activeTab === 'devices' && (
            <motion.div
              key="devices"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
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
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
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
