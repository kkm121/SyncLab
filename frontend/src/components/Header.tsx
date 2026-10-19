import React from 'react';
import { sounds } from '../lib/sound';
import {
  GitMergeIcon,
  FileTextIcon,
  LaptopIcon,
  DatabaseIcon,
  SunIcon,
  MoonIcon,
  VolumeIcon,
  VolumeMuteIcon,
  ZapIcon,
  SparklesIcon,
} from './Icons';

interface Props {
  activeTab: 'studio' | 'simulator' | 'devices';
  setActiveTab: (t: 'studio' | 'simulator' | 'devices') => void;
  audioEnabled: boolean;
  setAudioEnabled: (val: boolean) => void;
  theme: 'dark' | 'light';
  setTheme: (t: 'dark' | 'light') => void;
  performanceMode: 'ultra' | 'balanced' | 'lite';
  setPerformanceMode: (m: 'ultra' | 'balanced' | 'lite') => void;
}

export const Header: React.FC<Props> = ({
  activeTab,
  setActiveTab,
  audioEnabled,
  setAudioEnabled,
  theme,
  setTheme,
  performanceMode,
  setPerformanceMode,
}) => {
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    sounds.playTap();
  };

  const togglePerformance = () => {
    sounds.playTap();
    // Toggle between Lite (high performance 120 FPS mobile) and Ultra
    const nextMode = performanceMode === 'lite' ? 'ultra' : 'lite';
    setPerformanceMode(nextMode);
  };

  return (
    <header className="whistle-header synclab-header">
      <div className="header-left">
        <div
          className="brand-lockup"
          onClick={() => {
            sounds.playTap();
            setActiveTab('studio');
          }}
        >
          <div className="brand-icon-shield synclab-brand-icon">
            <GitMergeIcon size={24} />
          </div>
          <div>
            <h1 className="brand-title">SyncLab Pro</h1>
            <p className="brand-subtitle">Offline-First Engine · Honest 3-Way Merge · Zero Silent Overwrite</p>
          </div>
        </div>

        <div className="anonymity-pill-badge synclab-status-badge" title="Local-first offline store with diff3 synchronization">
          <span className="pulsing-green-dot" />
          <span>Local Node Active · Peer Mesh Ready</span>
        </div>
      </div>

      <div className="header-nav-segmented">
        <button
          className={`nav-tab-btn ${activeTab === 'studio' ? 'active' : ''}`}
          onClick={() => {
            sounds.playTap();
            setActiveTab('studio');
          }}
        >
          <FileTextIcon size={16} />
          <span>Document Studio</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'simulator' ? 'active' : ''}`}
          onClick={() => {
            sounds.playTap();
            setActiveTab('simulator');
          }}
        >
          <LaptopIcon size={16} />
          <span>Multi-Device Simulator</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'devices' ? 'active' : ''}`}
          onClick={() => {
            sounds.playTap();
            setActiveTab('devices');
          }}
        >
          <DatabaseIcon size={16} />
          <span>Device Fleet</span>
        </button>
      </div>

      <div className="header-actions">
        {/* Performance Mode Switcher: Essential for Xiaomi 12 Pro & Mid/Low-end phones */}
        <button
          className={`icon-action-btn perf-toggle-btn ${performanceMode === 'lite' ? 'active-lite' : ''}`}
          onClick={togglePerformance}
          title={`Active Mode: ${performanceMode === 'lite' ? '⚡ 120 FPS Lite (Mobile/Low-End Optimized)' : '🎨 Ultra Glass (Desktop)'}. Click to switch.`}
          aria-label="Toggle Performance Mode"
        >
          {performanceMode === 'lite' ? <ZapIcon size={18} className="highlight-amber" /> : <SparklesIcon size={18} />}
        </button>

        <button
          className="icon-action-btn theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          aria-label="Toggle color theme"
        >
          {theme === 'dark' ? <SunIcon size={18} /> : <MoonIcon size={18} />}
        </button>

        <button
          className="icon-action-btn"
          onClick={() => {
            const next = !audioEnabled;
            sounds.setEnabled(next);
            setAudioEnabled(next);
            if (next) sounds.playSuccess();
          }}
          title={audioEnabled ? 'Mute audio' : 'Enable audio feedback'}
          aria-label="Toggle audio feedback"
        >
          {audioEnabled ? <VolumeIcon size={18} /> : <VolumeMuteIcon size={18} />}
        </button>
      </div>
    </header>
  );
};
