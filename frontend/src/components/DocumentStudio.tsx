import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  getDocuments,
  createDocument,
  getDocument,
  getDocumentVersions,
  restoreDocumentVersion,
  executeSync,
} from '../lib/api';
import { sounds } from '../lib/sound';
import { DocumentOut, VersionOut } from '../types';
import {
  FileTextIcon,
  PlusIcon,
  SearchIcon,
  RotateCwIcon,
  RefreshCwIcon,
  LaptopIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  WifiOffIcon,
  ClockIcon,
  DownloadIcon,
  GitMergeIcon,
  ArrowRightIcon,
} from './Icons';

interface Props {
  flashNotice: (msg: string) => void;
  onOpenObsidianExport: (docId: number) => void;
}

export const DocumentStudio: React.FC<Props> = ({ flashNotice, onOpenObsidianExport }) => {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentOut | null>(null);
  const [versions, setVersions] = useState<VersionOut[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Mobile Navigation: switch between list view and editor view on phone screens
  const [mobileView, setMobileView] = useState<'list' | 'editor'>('editor');

  // Multi-Device Identity & Network State
  const [deviceId, setDeviceId] = useState<string>(() => {
    return localStorage.getItem('synclab_device_id') || 'laptop-macbook';
  });
  const [isOffline, setIsOffline] = useState<boolean>(false);
  const [pendingConflict, setPendingConflict] = useState<any | null>(null);

  // Active Edit Form
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editTags, setEditTags] = useState('');

  // Persist device ID
  useEffect(() => {
    localStorage.setItem('synclab_device_id', deviceId);
  }, [deviceId]);

  // Keep a stable ref to selectedDoc so WebSocket doesn't reconnect on doc change
  const selectedDocRef = useRef<DocumentOut | null>(selectedDoc);
  useEffect(() => {
    selectedDocRef.current = selectedDoc;
  }, [selectedDoc]);

  // Atomic data refresh for active document and fleet
  const refreshActiveDoc = useCallback(async (docId: number) => {
    try {
      const [docs, vList] = await Promise.all([
        getDocuments(searchQuery || undefined),
        getDocumentVersions(docId),
      ]);
      setDocuments(docs);
      setVersions(vList);
      const refreshed = docs.find((d) => d.id === docId);
      if (refreshed) {
        setSelectedDoc(refreshed);
        const offlineKey = `synclab_offline_draft_${docId}`;
        const localDraft = localStorage.getItem(offlineKey);
        if (!localDraft) {
          setEditTitle(refreshed.title);
          setEditBody(refreshed.body);
          setEditTags(refreshed.tags.join(', '));
        }
      }
    } catch {
      /* ignore */
    }
  }, [searchQuery]);

  // Persistent WebSocket Fleet Listener (Re-connects ONLY if network or deviceId changes)
  useEffect(() => {
    if (isOffline) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/sync`;
    let ws: WebSocket | null = null;
    let isMounted = true;

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const payload = JSON.parse(event.data);
          if (payload.type && payload.type.startsWith('SYNC_')) {
            const evData = payload.data || {};
            const sender = evData.device_id;
            const docId = evData.document_id;
            const activeDoc = selectedDocRef.current;
            if (sender !== deviceId && activeDoc && docId === activeDoc.id) {
              sounds.playTap();
              flashNotice(`⚡ Live Event: Device '${sender}' pushed revision v${evData.current_version} (${evData.outcome})!`);
              refreshActiveDoc(activeDoc.id);
            }
          }
        } catch {
          /* ignore */
        }
      };
    } catch {
      /* ignore */
    }

    return () => {
      isMounted = false;
      ws?.close();
    };
  }, [deviceId, isOffline, refreshActiveDoc, flashNotice]);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await getDocuments(searchQuery || undefined);
      setDocuments(data);
      if (!selectedDoc && data.length > 0) {
        handleSelectDoc(data[0]);
      } else if (selectedDoc) {
        const refreshed = data.find((d) => d.id === selectedDoc.id);
        if (refreshed) {
          setSelectedDoc(refreshed);
          const offlineKey = `synclab_offline_draft_${selectedDoc.id}`;
          const localDraft = localStorage.getItem(offlineKey);
          if (!localDraft) {
            setEditTitle(refreshed.title);
            setEditBody(refreshed.body);
            setEditTags(refreshed.tags.join(', '));
          }
        }
      }
    } catch (err: any) {
      flashNotice(err.message || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [searchQuery]);

  const handleSelectDoc = async (doc: DocumentOut) => {
    sounds.playTap();
    setSelectedDoc(doc);
    setPendingConflict(null);
    setMobileView('editor');

    // Check if there is an offline staged draft for this document
    const offlineKey = `synclab_offline_draft_${doc.id}`;
    const localDraft = localStorage.getItem(offlineKey);
    if (localDraft) {
      try {
        const draftObj = JSON.parse(localDraft);
        setEditTitle(draftObj.title || doc.title);
        setEditBody(draftObj.body || doc.body);
        setEditTags(draftObj.tags || doc.tags.join(', '));
        flashNotice(`Loaded offline staged mutation (Base v${draftObj.base_version}).`);
      } catch {
        setEditTitle(doc.title);
        setEditBody(doc.body);
        setEditTags(doc.tags.join(', '));
      }
    } else {
      setEditTitle(doc.title);
      setEditBody(doc.body);
      setEditTags(doc.tags.join(', '));
    }

    setIsFlipped(false);
    try {
      const v = await getDocumentVersions(doc.id);
      setVersions(v);
    } catch {
      /* ignore */
    }
  };

  const handleCreateNew = async () => {
    sounds.playTap();
    if (isOffline) {
      flashNotice('Cannot create new server document while in OFFLINE mode. Reconnect first.');
      return;
    }
    try {
      const doc = await createDocument({
        title: 'Untitled Collaborative Draft',
        body: '# SyncLab Document\n\nThis note is tracked with versioned writes and 3-way merge.\n\n- Line A: Local-first architecture\n- Line B: Zero silent overwrite guarantee\n- Line C: Obsidian markdown compatible',
        collection: 'notes',
        tags: ['draft', 'offline-first'],
        device_id: deviceId,
      });
      sounds.playSuccess();
      flashNotice(`New document created by ${deviceId}.`);
      setMobileView('editor');
      await fetchDocs();
      handleSelectDoc(doc);
    } catch (err: any) {
      flashNotice(err.message || 'Creation failed');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDoc) return;
    setSaving(true);
    sounds.playTap();

    const offlineKey = `synclab_offline_draft_${selectedDoc.id}`;

    // If device is currently OFFLINE: Save locally into outbox storage!
    if (isOffline) {
      const draftObj = {
        document_id: selectedDoc.id,
        base_version: selectedDoc.version,
        title: editTitle.trim(),
        body: editBody,
        tags: editTags,
        timestamp: Date.now(),
      };
      localStorage.setItem(offlineKey, JSON.stringify(draftObj));
      sounds.playSuccess();
      flashNotice(`⚡ [SAVED OFFLINE] Mutation staged locally for ${deviceId} (Base v${selectedDoc.version}). Reconnect to sync.`);
      setSaving(false);
      return;
    }

    // Device is ONLINE: Execute sync operation!
    try {
      const parsedTags = editTags.split(',').map((t) => t.trim()).filter(Boolean);
      const localDraft = localStorage.getItem(offlineKey);
      let baseVersion = selectedDoc.version;
      if (localDraft) {
        try {
          baseVersion = JSON.parse(localDraft).base_version || selectedDoc.version;
        } catch {
          /* ignore */
        }
      }

      const res = await executeSync({
        device_id: deviceId,
        document_id: selectedDoc.id,
        base_version: baseVersion,
        title: editTitle.trim(),
        body: editBody,
        tags: parsedTags,
        strategy: 'diff3',
      });

      const outcome = res.outcome;
      const targetVer = res.current_version || (res as any).target_version || selectedDoc.version + 1;

      if (outcome === 'accepted' || outcome === 'merged') {
        localStorage.removeItem(offlineKey);
        setPendingConflict(null);
        sounds.playSuccess();
        flashNotice(`✓ Synchronized successfully (Version v${targetVer} - ${outcome.toUpperCase()}).`);
        if (res.document) {
          setSelectedDoc(res.document);
          setEditBody(res.document.body);
          setEditTitle(res.document.title);
        }
      } else if (outcome === 'conflict') {
        sounds.playConflict();
        setPendingConflict(res);
        flashNotice(`⚠ Overlap conflict detected on v${res.current_version}! Zero overwrite guarantee.`);
      } else if (outcome === 'resolved') {
        localStorage.removeItem(offlineKey);
        setPendingConflict(null);
        sounds.playSuccess();
        flashNotice(`✓ Conflict resolved: ${res.resolution}`);
      }

      // Parallel data sync
      const [docs, vList] = await Promise.all([
        getDocuments(searchQuery || undefined),
        getDocumentVersions(selectedDoc.id),
      ]);
      setDocuments(docs);
      setVersions(vList);
    } catch (err: any) {
      sounds.playConflict();
      flashNotice(err.message || 'Sync failed');
    } finally {
      setSaving(false);
    }
  };

  const handleResolveConflict = async (strategy: 'server_wins' | 'client_wins' | 'diff3_markers') => {
    if (!selectedDoc) return;
    setSaving(true);
    sounds.playTap();

    try {
      if (strategy === 'diff3_markers') {
        const serverDoc = await getDocument(selectedDoc.id);
        const markers = (
          `<<<<<<< LOCAL (${deviceId})\n` +
          `${editBody}\n` +
          `=======\n` +
          `${serverDoc.body}\n` +
          `>>>>>>> SERVER (v${serverDoc.version})`
        );
        setEditBody(markers);
        setPendingConflict(null);
        flashNotice('Diff3 conflict markers placed in editor. Review and click Save & Sync.');
        setSaving(false);
        return;
      }

      const parsedTags = editTags.split(',').map((t) => t.trim()).filter(Boolean);
      const res = await executeSync({
        device_id: deviceId,
        document_id: selectedDoc.id,
        base_version: selectedDoc.version,
        title: editTitle.trim(),
        body: editBody,
        tags: parsedTags,
        strategy: strategy as any,
      });

      localStorage.removeItem(`synclab_offline_draft_${selectedDoc.id}`);
      setPendingConflict(null);
      sounds.playSuccess();
      flashNotice(`Conflict resolved using ${strategy}: ${res.resolution}`);

      const [docs, vList] = await Promise.all([
        getDocuments(searchQuery || undefined),
        getDocumentVersions(selectedDoc.id),
      ]);
      setDocuments(docs);
      setVersions(vList);
      if (res.document) {
        setSelectedDoc(res.document);
      }
    } catch (err: any) {
      flashNotice(err.message || 'Resolution failed');
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = async (versionNum: number) => {
    if (!selectedDoc) return;
    sounds.playTap();
    try {
      const restored = await restoreDocumentVersion(selectedDoc.id, versionNum, deviceId);
      sounds.playSuccess();
      flashNotice(`Restored to Version ${versionNum} as new Version ${restored.version}.`);
      await fetchDocs();
      handleSelectDoc(restored);
    } catch (err: any) {
      flashNotice(err.message || 'Restore failed');
    }
  };

  const hasOfflineDraft = selectedDoc ? Boolean(localStorage.getItem(`synclab_offline_draft_${selectedDoc.id}`)) : false;

  return (
    <div className="document-studio-container">
      {/* Telemetry Header */}
      <section className="mod-telemetry-grid">
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">ACTIVE VAULT DOCUMENTS</span>
          <strong className="telemetry-val">{documents.length}</strong>
        </div>
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">CURRENT REVISION</span>
          <strong className="telemetry-val highlight-green">v{selectedDoc?.version || 1}</strong>
        </div>
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">ACTIVE DEVICE IDENTITY</span>
          <strong className="telemetry-val highlight-cyan">{deviceId}</strong>
        </div>
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">NETWORK STATUS</span>
          <strong className={`telemetry-val ${isOffline ? 'highlight-amber' : 'highlight-green'}`}>
            {isOffline ? 'OFFLINE ⚡' : 'ONLINE 🟢'}
          </strong>
        </div>
      </section>

      {/* Mobile Screen View Switcher Pill */}
      <div className="mobile-view-bar">
        <button
          type="button"
          className={`mobile-view-pill ${mobileView === 'list' ? 'active' : ''}`}
          onClick={() => setMobileView('list')}
        >
          <FileTextIcon size={14} />
          <span>Notes List ({documents.length})</span>
        </button>
        <button
          type="button"
          className={`mobile-view-pill ${mobileView === 'editor' ? 'active' : ''}`}
          onClick={() => setMobileView('editor')}
          disabled={!selectedDoc}
        >
          <GitMergeIcon size={14} />
          <span>Editor {selectedDoc ? `(#${selectedDoc.id} v${selectedDoc.version})` : ''}</span>
        </button>
      </div>

      {/* Main Split Layout */}
      <div className="cases-split-layout">
        {/* Document Sidebar (Hidden on mobile if user is editing) */}
        <div className={`cases-list-card glass-panel doc-sidebar-panel ${mobileView === 'editor' ? 'hide-on-mobile' : ''}`}>
          <div className="doc-sidebar-header">
            <div className="search-input-wrap">
              <SearchIcon size={14} className="search-icon-field" />
              <input
                type="text"
                className="mod-search-input doc-search-input"
                placeholder="Search notes & tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <button className="btn-primary btn-new-doc" onClick={handleCreateNew} disabled={isOffline}>
              <PlusIcon size={14} />
              <span>New Doc</span>
            </button>
          </div>

          <div className="doc-items-list">
            {loading ? (
              <div className="empty-state-desc" style={{ padding: '24px', textAlign: 'center' }}>
                Loading documents...
              </div>
            ) : documents.length === 0 ? (
              <div className="empty-state-luxury" style={{ padding: '36px 20px' }}>
                <FileTextIcon size={32} />
                <h4 className="empty-state-title" style={{ fontSize: '15px', marginTop: '10px' }}>
                  No Documents Found
                </h4>
                <p className="empty-state-desc" style={{ fontSize: '12px' }}>
                  Create your first offline-synced note to begin.
                </p>
                <button className="btn-primary" onClick={handleCreateNew} disabled={isOffline}>
                  <PlusIcon size={14} />
                  <span>Create Note</span>
                </button>
              </div>
            ) : (
              documents.map((doc) => {
                const isSelected = selectedDoc?.id === doc.id;
                const isDraftStaged = Boolean(localStorage.getItem(`synclab_offline_draft_${doc.id}`));
                return (
                  <div
                    key={doc.id}
                    className={`case-item-row ${isSelected ? 'is-selected' : ''}`}
                    onClick={() => handleSelectDoc(doc)}
                  >
                    <div className="case-row-main">
                      <div className="case-code-line">
                        <FileTextIcon size={13} className="case-code-icon" />
                        <span className="case-code-text">#{doc.id} · {doc.title}</span>
                      </div>
                      <div className="case-preview-text">
                        {doc.body.replace(/^#+\s+/gm, '').slice(0, 75)}...
                      </div>
                      <div className="case-meta-tags">
                        <span className="doc-ver-badge">v{doc.version}</span>
                        {isDraftStaged && (
                          <span className="doc-tag-badge" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', borderColor: '#f59e0b' }}>
                            OFFLINE DRAFT
                          </span>
                        )}
                        {doc.tags.slice(0, 2).map((t) => (
                          <span key={t} className="doc-tag-badge">#{t}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 3D Flip Card: Editor & Merge Inspector (Hidden on mobile if user is browsing notes) */}
        <div className={`case-detail-container ${mobileView === 'list' ? 'hide-on-mobile' : ''}`}>
          <div className={`flip-card-3d ${isFlipped ? 'is-flipped' : ''}`}>
            
            {/* FRONT FACE: Document Editor */}
            <div className="flip-card-face flip-card-front">
              {selectedDoc ? (
                <form className="dropbox-main-card glass-panel" onSubmit={handleSave}>
                  <div className="card-top-action-bar">
                    <div className="card-header-bar">
                      <span className="step-num-badge">DOC</span>
                      <div>
                        <h3 className="card-section-title">Collaborative Document Canvas</h3>
                        <p className="card-section-desc">Version {selectedDoc.version} · Offline sync with zero data loss</p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                      {/* Mobile back button */}
                      <button
                        type="button"
                        className="btn-secondary mobile-only-btn"
                        onClick={() => setMobileView('list')}
                        title="Back to notes list"
                      >
                        <span>← Notes</span>
                      </button>

                      {/* Device Identity Selector */}
                      <select
                        className="mod-search-input"
                        style={{ padding: '6px 10px', fontSize: '12px', fontWeight: '600' }}
                        value={deviceId}
                        onChange={(e) => {
                          setDeviceId(e.target.value);
                          sounds.playTap();
                          flashNotice(`Switched device identity to: ${e.target.value}`);
                        }}
                      >
                        <option value="laptop-macbook">💻 Laptop-MacBook</option>
                        <option value="phone-iphone15">📱 Phone-Xiaomi/iPhone</option>
                        <option value="tablet-ipad">📟 Tablet-iPad</option>
                        <option value="desktop-workstation">🖥️ Workstation</option>
                      </select>

                      {/* Network Toggle Button */}
                      <button
                        type="button"
                        className={isOffline ? 'btn-primary' : 'btn-secondary'}
                        style={isOffline ? { background: '#f59e0b', borderColor: '#d97706', color: '#000' } : {}}
                        onClick={() => {
                          sounds.playTap();
                          setIsOffline(!isOffline);
                          flashNotice(!isOffline ? 'Switched to OFFLINE mode (Airplane mode).' : 'Switched to ONLINE mode.');
                        }}
                        title="Toggle Network connectivity to simulate offline editing"
                      >
                        {isOffline ? <WifiOffIcon size={14} /> : <CheckCircleIcon size={14} />}
                        <span>{isOffline ? 'OFFLINE ⚡' : 'ONLINE 🟢'}</span>
                      </button>

                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => onOpenObsidianExport(selectedDoc.id)}
                        title="Export document with Obsidian YAML frontmatter and backlinks"
                      >
                        <DownloadIcon size={14} />
                        <span>Obsidian</span>
                      </button>

                      <button
                        type="button"
                        className="card-flip-btn"
                        onClick={() => {
                          sounds.playTap();
                          setIsFlipped(true);
                        }}
                        title="Inspect 3-Way diff matrix and merge engine"
                      >
                        <RotateCwIcon size={14} />
                        <span>Diff3 Matrix</span>
                      </button>
                    </div>
                  </div>

                  {/* Conflict Notification Banner */}
                  {pendingConflict && (
                    <div className="glass-panel" style={{ margin: '14px 0', padding: '14px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444', fontWeight: '700' }}>
                        <AlertTriangleIcon size={18} />
                        <span>CONCURRENT WRITE CONFLICT DETECTED (Server v{pendingConflict.current_version})</span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '8px 0 12px 0' }}>
                        {pendingConflict.resolution || 'Server state has diverged from your base version. Silent overwrite prevented.'}
                      </p>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button type="button" className="btn-secondary" onClick={() => handleResolveConflict('server_wins')}>
                          Accept Server v{pendingConflict.current_version}
                        </button>
                        <button type="button" className="btn-secondary" onClick={() => handleResolveConflict('client_wins')}>
                          Force My Changes (Client Wins)
                        </button>
                        <button type="button" className="btn-primary" onClick={() => handleResolveConflict('diff3_markers')}>
                          Insert Conflict Markers
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Offline Staged Draft Banner */}
                  {hasOfflineDraft && !isOffline && (
                    <div className="glass-panel" style={{ margin: '12px 0', padding: '12px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontSize: '13px' }}>
                        <ClockIcon size={16} />
                        <span>Offline staged mutations detected. Click below to synchronize with server!</span>
                      </div>
                    </div>
                  )}

                  {/* Title & Tags */}
                  <div className="doc-fields-grid">
                    <div className="field-group">
                      <label className="section-label">DOCUMENT TITLE</label>
                      <input
                        type="text"
                        className="mod-search-input"
                        style={{ width: '100%', fontSize: '15px', fontWeight: '700' }}
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        required
                      />
                    </div>

                    <div className="field-group">
                      <label className="section-label">OBSIDIAN TAGS</label>
                      <input
                        type="text"
                        className="mod-search-input"
                        style={{ width: '100%' }}
                        value={editTags}
                        onChange={(e) => setEditTags(e.target.value)}
                        placeholder="research, architecture, sprint"
                      />
                    </div>
                  </div>

                  {/* Body Editor */}
                  <div className="textarea-wrapper" style={{ marginTop: '16px' }}>
                    <label className="section-label">MARKDOWN CONTENT</label>
                    <textarea
                      className="incident-textarea"
                      rows={12}
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      placeholder="Write your document content here in Markdown format..."
                      required
                    />
                    <div className="textarea-footer">
                      <span>{editBody.length} characters · {editBody.split('\n').length} lines</span>
                      <span className="ml-analyzing-indicator">
                        <CheckCircleIcon size={13} />
                        <span>Base v{selectedDoc.version} locked</span>
                      </span>
                    </div>
                  </div>

                  {/* Save & Telemetry Row */}
                  <div className="form-submit-row">
                    <div className="anonymity-pledge-note">
                      <GitMergeIcon size={16} />
                      <span>Sync engine computes diff3 line-level deltas before committing revision.</span>
                    </div>

                    <button type="submit" className="submit-report-btn" disabled={saving}>
                      <RefreshCwIcon size={15} className={saving ? 'spin-slow' : ''} />
                      <span>
                        {saving
                          ? 'Synchronizing...'
                          : isOffline
                          ? 'Save Offline Draft (Local)'
                          : hasOfflineDraft
                          ? 'Sync Staged Revision →'
                          : 'Save & Sync Revision →'}
                      </span>
                    </button>
                  </div>

                  {/* Version History Timeline */}
                  <div className="doc-history-drawer" style={{ marginTop: '20px' }}>
                    <span className="section-label">IMMUTABLE REVISION HISTORY ({versions.length})</span>
                    <div className="versions-timeline-horizontal">
                      {versions.map((v) => (
                        <div key={v.version} className="version-history-chip">
                          <div className="v-chip-top">
                            <span className="v-num">v{v.version}</span>
                            <span className={`v-outcome ${v.outcome}`}>{v.outcome}</span>
                          </div>
                          <span className="v-date">{new Date(v.created_at).toLocaleTimeString()}</span>
                          <span className="v-dev">{v.device_id}</span>
                          {v.version !== selectedDoc.version && (
                            <button
                              type="button"
                              className="v-restore-btn"
                              onClick={() => handleRestore(v.version)}
                              title={`Restore content from revision v${v.version}`}
                              disabled={isOffline}
                            >
                              Restore
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </form>
              ) : (
                <div className="dropbox-main-card glass-panel empty-state-luxury">
                  <FileTextIcon size={44} />
                  <h4 className="empty-state-title">Select a Document</h4>
                  <p className="empty-state-desc">Choose a document from the left vault to begin editing and syncing.</p>
                </div>
              )}
            </div>

            {/* BACK FACE: Visual 3-Way Merge & Sync Conflict Graph */}
            <div className="flip-card-face flip-card-back">
              <div className="dropbox-main-card glass-panel ml-back-panel">
                <div className="card-top-action-bar">
                  <div className="card-header-bar">
                    <span className="step-num-badge">DIFF3</span>
                    <div>
                      <h3 className="card-section-title">Visual 3-Way Merge Engine</h3>
                      <p className="card-section-desc">Ancestor base version, client mutation, and concurrent resolution analysis</p>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="card-flip-btn return-btn"
                    onClick={() => {
                      sounds.playTap();
                      setIsFlipped(false);
                    }}
                    title="Return to document editor"
                  >
                    <RotateCwIcon size={14} />
                    <span>Return to Canvas</span>
                  </button>
                </div>

                {/* Only render diff matrix when card is actually flipped to optimize render times */}
                {isFlipped && (
                  <div className="diff-matrix-grid">
                    <div className="diff-column glass-panel">
                      <div className="diff-col-header">
                        <ClockIcon size={14} />
                        <span>COMMON ANCESTOR (BASE v{selectedDoc?.version || 1})</span>
                      </div>
                      <pre className="diff-pre">{selectedDoc?.body || 'No base document loaded'}</pre>
                    </div>

                    <div className="diff-column glass-panel">
                      <div className="diff-col-header highlight-cyan">
                        <LaptopIcon size={14} />
                        <span>ACTIVE CLIENT REVISION (STAGING)</span>
                      </div>
                      <pre className="diff-pre">{editBody || 'No active edits'}</pre>
                    </div>
                  </div>
                )}

                <div className="diff-strategies-card glass-panel" style={{ marginTop: '16px', padding: '16px' }}>
                  <span className="section-label">SYNC RESOLUTION BEHAVIOR</span>
                  <div className="strategy-descriptions-list">
                    <div className="strat-item">
                      <strong>diff3 (Automatic 3-Way Line Merge):</strong>
                      <p>Disjoint non-overlapping line edits are merged seamlessly into a clean target revision.</p>
                    </div>
                    <div className="strat-item">
                      <strong>Explicit Conflict Recording:</strong>
                      <p>If two peers edit the same line, the engine never blindly overwrites; it records a conflict outcome.</p>
                    </div>
                    <div className="strat-item">
                      <strong>Audit Trail:</strong>
                      <p>History is immutable. Every restore or merge commits a monotonically increasing version number.</p>
                    </div>
                  </div>
                </div>

                <div className="ml-back-footer">
                  <span className="ml-engine-badge">SyncLab Distributed Protocol · Diff3 Engine · SQLite Store</span>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => {
                      sounds.playTap();
                      setIsFlipped(false);
                    }}
                  >
                    Return to Editor →
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};
