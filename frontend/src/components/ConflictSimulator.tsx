import React, { useState, useEffect } from 'react';
import { getDocuments, executeSync } from '../lib/api';
import { sounds } from '../lib/sound';
import { DocumentOut, SyncResult, MergeStrategy } from '../types';
import {
  LaptopIcon,
  SmartphoneIcon,
  GitMergeIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  SparklesIcon,
  RefreshCwIcon,
  WifiOffIcon,
} from './Icons';

interface Props {
  flashNotice: (msg: string) => void;
}

export const ConflictSimulator: React.FC<Props> = ({ flashNotice }) => {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [targetDoc, setTargetDoc] = useState<DocumentOut | null>(null);

  // Device Alpha (Laptop)
  const [alphaBaseVer, setAlphaBaseVer] = useState(1);
  const [alphaText, setAlphaText] = useState('');
  const [alphaStrategy, setAlphaStrategy] = useState<MergeStrategy>('diff3');
  const [alphaSyncing, setAlphaSyncing] = useState(false);
  const [alphaResult, setAlphaResult] = useState<SyncResult | null>(null);

  // Device Beta (Smartphone)
  const [betaBaseVer, setBetaBaseVer] = useState(1);
  const [betaText, setBetaText] = useState('');
  const [betaStrategy, setBetaStrategy] = useState<MergeStrategy>('diff3');
  const [betaSyncing, setBetaSyncing] = useState(false);
  const [betaResult, setBetaResult] = useState<SyncResult | null>(null);

  const fetchDocs = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data);
      if (data.length > 0 && !targetDoc) {
        loadDocIntoSimulator(data[0]);
      }
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const loadDocIntoSimulator = (doc: DocumentOut) => {
    setTargetDoc(doc);
    setAlphaBaseVer(doc.version);
    setAlphaText(doc.body);
    setBetaBaseVer(doc.version);
    setBetaText(doc.body);
    setAlphaResult(null);
    setBetaResult(null);
  };

  const handleDemoDisjoint = () => {
    sounds.playTap();
    if (!targetDoc) return;
    const baseLines = [
      '# Architecture Guidelines',
      'SECTION 1: Core sync invariants and idempotency rules.',
      'SECTION 2: Transport layer protocols and websocket gateways.',
      'SECTION 3: Obsidian markdown export with frontmatter.',
    ];
    const baseBody = baseLines.join('\n');

    // Alpha edits line 2
    const alphaLines = [...baseLines];
    alphaLines[1] = 'SECTION 1: [ALPHA UPDATED] Verified local-first sync invariants with SHA-256.';

    // Beta edits line 4
    const betaLines = [...baseLines];
    betaLines[3] = 'SECTION 3: [BETA UPDATED] Obsidian vault export with automatic bidirectional backlinks.';

    setAlphaBaseVer(targetDoc.version);
    setBetaBaseVer(targetDoc.version);
    setAlphaText(alphaLines.join('\n'));
    setBetaText(betaLines.join('\n'));
    setAlphaResult(null);
    setBetaResult(null);
    flashNotice('Loaded Disjoint Edits scenario: Device Alpha edited Section 1, Device Beta edited Section 3.');
  };

  const handleDemoConflict = () => {
    sounds.playTap();
    if (!targetDoc) return;
    const baseLines = [
      '# Security Specifications',
      'PROTOCOL: AES-256-GCM authenticated encryption on local store.',
      'TIMEOUT: Keep-alive ping interval set to 30 seconds.',
    ];

    // Alpha edits line 2
    const alphaLines = [...baseLines];
    alphaLines[1] = 'PROTOCOL: [ALPHA CHOICE] ChaCha20-Poly1305 lightweight high-throughput cipher.';

    // Beta edits SAME line 2 differently
    const betaLines = [...baseLines];
    betaLines[1] = 'PROTOCOL: [BETA CHOICE] Post-Quantum Kyber-1024 hybrid key encapsulation.';

    setAlphaBaseVer(targetDoc.version);
    setBetaBaseVer(targetDoc.version);
    setAlphaText(alphaLines.join('\n'));
    setBetaText(betaLines.join('\n'));
    setAlphaResult(null);
    setBetaResult(null);
    flashNotice('Loaded Concurrent Conflict scenario: Both devices modified the same PROTOCOL line.');
  };

  const syncDevice = async (device: 'alpha' | 'beta') => {
    if (!targetDoc) return;
    sounds.playTap();

    const isAlpha = device === 'alpha';
    if (isAlpha) setAlphaSyncing(true);
    else setBetaSyncing(true);

    try {
      const res = await executeSync({
        device_id: isAlpha ? 'device-laptop-alpha' : 'device-mobile-beta',
        document_id: targetDoc.id,
        base_version: isAlpha ? alphaBaseVer : betaBaseVer,
        body: isAlpha ? alphaText : betaText,
        strategy: isAlpha ? alphaStrategy : betaStrategy,
      });

      if (isAlpha) setAlphaResult(res);
      else setBetaResult(res);

      if (res.outcome === 'accepted' || res.outcome === 'merged') {
        sounds.playSuccess();
        flashNotice(`${isAlpha ? 'Device Alpha' : 'Device Beta'} synchronized: Outcome ${res.outcome.toUpperCase()} (Target v${res.target_version})`);
      } else if (res.outcome === 'conflict') {
        sounds.playConflict();
        flashNotice(`Concurrent Conflict Detected! ${res.resolution}`);
      }

      // Refresh target doc
      const docs = await getDocuments();
      setDocuments(docs);
      const updated = docs.find((d) => d.id === targetDoc.id);
      if (updated) {
        setTargetDoc(updated);
      }
    } catch (err: any) {
      sounds.playConflict();
      flashNotice(err.message || 'Sync failed');
    } finally {
      if (isAlpha) setAlphaSyncing(false);
      else setBetaSyncing(false);
    }
  };

  return (
    <div className="simulator-container">
      {/* Hero */}
      <section className="dropbox-hero">
        <div className="hero-kicker-strip">
          <span className="hero-kicker-beacon" />
          <span className="hero-kicker">CONCURRENT OFFLINE SIMULATION</span>
        </div>
        <h2 className="hero-heading">Multi-Device 3-Way Merge Lab</h2>
        <p className="hero-tagline">
          Simulate two disconnected peer nodes modifying divergent sections offline. Verify automatic diff3 line merging and honest conflict preservation.
        </p>

        {/* Demo Scenario Buttons */}
        <div className="scenario-action-bar">
          <button className="btn-scenario-demo" onClick={handleDemoDisjoint}>
            <SparklesIcon size={14} />
            <span>Preset: Disjoint Non-Conflicting Edits (Auto-Merge)</span>
          </button>
          <button className="btn-scenario-demo conflict" onClick={handleDemoConflict}>
            <AlertTriangleIcon size={14} />
            <span>Preset: Same-Line Collision (Honest Conflict)</span>
          </button>
        </div>
      </section>

      {/* Target Doc Selection Bar */}
      <div className="sim-target-bar glass-panel">
        <span className="section-label">ACTIVE SIMULATION DOCUMENT:</span>
        <select
          className="filter-dropdown"
          value={targetDoc?.id || ''}
          onChange={(e) => {
            const found = documents.find((d) => d.id === Number(e.target.value));
            if (found) loadDocIntoSimulator(found);
          }}
        >
          {documents.map((d) => (
            <option key={d.id} value={d.id}>
              #{d.id} · {d.title} (Server Current: v{d.version})
            </option>
          ))}
        </select>
        <span className="sim-server-badge">Server Head: Version v{targetDoc?.version || 1}</span>
      </div>

      {/* Side-by-Side Simulation Devices */}
      <div className="simulator-devices-grid">
        
        {/* DEVICE ALPHA (Laptop) */}
        <div className="device-card glass-panel">
          <div className="device-header">
            <div className="device-title-wrap">
              <LaptopIcon size={20} className="device-icon" />
              <div>
                <h3 className="device-name">Device Alpha (Laptop)</h3>
                <span className="device-state-pill offline">
                  <WifiOffIcon size={12} />
                  <span>Offline Staging Buffer</span>
                </span>
              </div>
            </div>

            <div className="base-ver-badge">
              <span>Forked from: </span>
              <strong>v{alphaBaseVer}</strong>
            </div>
          </div>

          <div className="device-editor-body">
            <label className="section-label">OFFLINE BUFFER CONTENT</label>
            <textarea
              className="incident-textarea sim-textarea"
              rows={9}
              value={alphaText}
              onChange={(e) => setAlphaText(e.target.value)}
              placeholder="Edit content on Device Alpha..."
            />
          </div>

          <div className="device-sync-controls">
            <div className="strat-select-group">
              <label className="section-label">MERGE STRATEGY</label>
              <select
                className="filter-dropdown"
                value={alphaStrategy}
                onChange={(e) => setAlphaStrategy(e.target.value as MergeStrategy)}
              >
                <option value="diff3">diff3 (3-Way Line Merge)</option>
                <option value="server_wins">server_wins (Keep Server)</option>
                <option value="client_wins">client_wins (Client Overrides)</option>
                <option value="manual">manual (Never Auto-apply)</option>
              </select>
            </div>

            <button
              className="btn-primary btn-sync-node"
              onClick={() => syncDevice('alpha')}
              disabled={alphaSyncing}
            >
              <RefreshCwIcon size={14} className={alphaSyncing ? 'spin-slow' : ''} />
              <span>{alphaSyncing ? 'Pushing...' : 'Sync Device Alpha →'}</span>
            </button>
          </div>

          {alphaResult && (
            <div className={`sync-result-box ${alphaResult.outcome}`}>
              <div className="res-top">
                {alphaResult.outcome === 'accepted' || alphaResult.outcome === 'merged' ? (
                  <CheckCircleIcon size={16} />
                ) : (
                  <AlertTriangleIcon size={16} />
                )}
                <strong>OUTCOME: {alphaResult.outcome.toUpperCase()}</strong>
                <span className="res-target">Target v{alphaResult.target_version}</span>
              </div>
              <p className="res-desc">{alphaResult.resolution}</p>
            </div>
          )}
        </div>

        {/* DEVICE BETA (Smartphone) */}
        <div className="device-card glass-panel">
          <div className="device-header">
            <div className="device-title-wrap">
              <SmartphoneIcon size={20} className="device-icon highlight-cyan" />
              <div>
                <h3 className="device-name">Device Beta (Smartphone)</h3>
                <span className="device-state-pill offline">
                  <WifiOffIcon size={12} />
                  <span>Offline Staging Buffer</span>
                </span>
              </div>
            </div>

            <div className="base-ver-badge">
              <span>Forked from: </span>
              <strong>v{betaBaseVer}</strong>
            </div>
          </div>

          <div className="device-editor-body">
            <label className="section-label">OFFLINE BUFFER CONTENT</label>
            <textarea
              className="incident-textarea sim-textarea"
              rows={9}
              value={betaText}
              onChange={(e) => setBetaText(e.target.value)}
              placeholder="Edit content on Device Beta..."
            />
          </div>

          <div className="device-sync-controls">
            <div className="strat-select-group">
              <label className="section-label">MERGE STRATEGY</label>
              <select
                className="filter-dropdown"
                value={betaStrategy}
                onChange={(e) => setBetaStrategy(e.target.value as MergeStrategy)}
              >
                <option value="diff3">diff3 (3-Way Line Merge)</option>
                <option value="server_wins">server_wins (Keep Server)</option>
                <option value="client_wins">client_wins (Client Overrides)</option>
                <option value="manual">manual (Never Auto-apply)</option>
              </select>
            </div>

            <button
              className="btn-primary btn-sync-node btn-cyan"
              onClick={() => syncDevice('beta')}
              disabled={betaSyncing}
            >
              <RefreshCwIcon size={14} className={betaSyncing ? 'spin-slow' : ''} />
              <span>{betaSyncing ? 'Pushing...' : 'Sync Device Beta →'}</span>
            </button>
          </div>

          {betaResult && (
            <div className={`sync-result-box ${betaResult.outcome}`}>
              <div className="res-top">
                {betaResult.outcome === 'accepted' || betaResult.outcome === 'merged' ? (
                  <CheckCircleIcon size={16} />
                ) : (
                  <AlertTriangleIcon size={16} />
                )}
                <strong>OUTCOME: {betaResult.outcome.toUpperCase()}</strong>
                <span className="res-target">Target v{betaResult.target_version}</span>
              </div>
              <p className="res-desc">{betaResult.resolution}</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
