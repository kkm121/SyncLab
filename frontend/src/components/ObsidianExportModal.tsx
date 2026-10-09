import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { exportMarkdownText } from '../lib/api';
import { sounds } from '../lib/sound';
import {
  FileTextIcon,
  DownloadIcon,
  CopyIcon,
  CheckCircleIcon,
  TagIcon,
} from './Icons';

interface Props {
  docId: number;
  onClose: () => void;
  flashNotice: (msg: string) => void;
}

export const ObsidianExportModal: React.FC<Props> = ({ docId, onClose, flashNotice }) => {
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchMd = async () => {
      try {
        const text = await exportMarkdownText(docId);
        setMarkdown(text);
      } catch (err: any) {
        flashNotice(err.message || 'Export failed');
      } finally {
        setLoading(false);
      }
    };
    fetchMd();
  }, [docId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      sounds.playSuccess();
      flashNotice('Obsidian markdown copied to clipboard.');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      flashNotice('Clipboard copy failed.');
    }
  };

  const handleDownload = () => {
    sounds.playTap();
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `synclab-doc-${docId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    flashNotice(`Downloaded synclab-doc-${docId}.md into Obsidian vault.`);
  };

  return (
    <div className="modal-backdrop-overlay">
      <motion.div
        className="case-pass-modal glass-panel obsidian-modal"
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
      >
        <div className="modal-badge-row">
          <span className="secure-pass-tag" style={{ color: '#a855f7' }}>
            OBSIDIAN VAULT COMPLIANT EXPORTER
          </span>
          <button className="modal-close-x" onClick={onClose} title="Close modal">
            ×
          </button>
        </div>

        <div className="pass-header-content">
          <div className="pass-icon-ring" style={{ color: '#a855f7', background: 'rgba(168, 85, 247, 0.15)' }}>
            <FileTextIcon size={28} />
          </div>
          <h3 className="pass-title">Obsidian Markdown Vault Export</h3>
          <p className="pass-description">
            Exports document with YAML frontmatter, collection taxonomy, immutable revision metadata, and backlinks.
          </p>
        </div>

        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
            Compiling Obsidian frontmatter and markdown...
          </div>
        ) : (
          <div className="obsidian-preview-box">
            <pre className="obsidian-pre">{markdown}</pre>
          </div>
        )}

        <div className="modal-button-actions" style={{ marginTop: '20px' }}>
          <button className={`btn-secondary ${copied ? 'copied' : ''}`} onClick={handleCopy}>
            {copied ? <CheckCircleIcon size={14} /> : <CopyIcon size={14} />}
            <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
          </button>
          <button className="btn-primary" onClick={handleDownload}>
            <DownloadIcon size={14} />
            <span>Download .md Note</span>
          </button>
        </div>
      </motion.div>
    </div>
  );
};
