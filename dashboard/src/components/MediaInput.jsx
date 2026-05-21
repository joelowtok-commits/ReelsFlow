import React, { useState, useEffect } from 'react';
import { Youtube, Upload, FileVideo, X } from 'lucide-react';
import { getApiUrl } from '../config';

export default function MediaInput({ onProcess, isProcessing }) {
    const [youtubeUrlEnabled, setYoutubeUrlEnabled] = useState(true);
    const [mode, setMode] = useState('url'); // 'url' | 'file'
    const [url, setUrl] = useState('');
    const [file, setFile] = useState(null);
    const [acknowledged, setAcknowledged] = useState(true);
    const [autoEdit, setAutoEdit] = useState(true);

    useEffect(() => {
        fetch(getApiUrl('/api/config'))
            .then((r) => r.ok ? r.json() : null)
            .then((cfg) => {
                if (cfg && cfg.youtubeUrlEnabled === false) {
                    setYoutubeUrlEnabled(false);
                    setMode('file');
                }
            })
            .catch(() => {});
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!acknowledged) return;
        if (mode === 'url' && url) {
            onProcess({ type: 'url', payload: url, acknowledged: true, autoEdit });
        } else if (mode === 'file' && file) {
            onProcess({ type: 'file', payload: file, acknowledged: true, autoEdit });
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
            setMode('file');
        }
    };

    return (
        <div className="bg-surface border border-white/5 rounded-2xl p-6 animate-[fadeIn_0.6s_ease-out]">
            <div className="flex gap-4 mb-6 border-b border-white/5 pb-4">
                {youtubeUrlEnabled && (
                    <button
                        onClick={() => setMode('url')}
                        className={`flex items-center gap-2 pb-2 px-2 transition-all ${mode === 'url'
                            ? 'text-primary border-b-2 border-primary -mb-[17px]'
                            : 'text-zinc-400 hover:text-white'
                            }`}
                    >
                        <Youtube size={18} />
                        Video URL
                    </button>
                )}
                <button
                    onClick={() => setMode('file')}
                    className={`flex items-center gap-2 pb-2 px-2 transition-all ${mode === 'file'
                        ? 'text-primary border-b-2 border-primary -mb-[17px]'
                        : 'text-zinc-400 hover:text-white'
                        }`}
                >
                    <Upload size={18} />
                    Upload File
                </button>
            </div>

            <form onSubmit={handleSubmit}>
                {mode === 'url' ? (
                    <div className="space-y-4">
                        <input
                            type="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://www.youtube.com/watch?v=... or TikTok, Instagram URL"
                            className="input-field"
                            required
                        />
                    </div>
                ) : (
                    <div
                        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${file ? 'border-primary/50 bg-primary/5' : 'border-zinc-700 hover:border-zinc-500 bg-white/5'
                            }`}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={handleDrop}
                    >
                        {file ? (
                            <div className="flex items-center justify-center gap-3 text-white">
                                <FileVideo className="text-primary" />
                                <span className="font-medium">{file.name}</span>
                                <button
                                    type="button"
                                    onClick={() => setFile(null)}
                                    className="p-1 hover:bg-white/10 rounded-full"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ) : (
                            <label className="cursor-pointer block">
                                <input
                                    type="file"
                                    accept="video/*"
                                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                                    className="hidden"
                                />
                                <Upload className="mx-auto mb-3 text-zinc-500" size={24} />
                                <p className="text-zinc-400">Click to upload or drag and drop</p>
                                <p className="text-xs text-zinc-600 mt-1">MP4, MOV up to 500MB</p>
                            </label>
                        )}
                    </div>
                )}

                {/* Auto-edit checkbox */}
                <label className="flex items-center gap-3 mt-5 p-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/40 hover:bg-primary/5 transition-all cursor-pointer select-none group">
                    <div className="relative shrink-0">
                        <input
                            type="checkbox"
                            id="auto-edit-checkbox"
                            checked={autoEdit}
                            onChange={(e) => setAutoEdit(e.target.checked)}
                            className="sr-only"
                        />
                        <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                            autoEdit ? 'bg-primary border-primary' : 'border-zinc-600 bg-transparent group-hover:border-zinc-400'
                        }`}>
                            {autoEdit && (
                                <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                                    <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                            )}
                        </div>
                    </div>
                    <div className="min-w-0">
                        <p className="text-sm font-semibold text-white leading-none mb-0.5">⚡ Auto-editar y descargar clips</p>
                        <p className="text-xs text-zinc-500 leading-snug">Quema subtítulos + hook al terminar y descarga todo automáticamente</p>
                    </div>
                </label>

                <label className="flex items-start gap-2 mt-3 text-xs text-zinc-400 cursor-pointer select-none">
                    <input
                        type="checkbox"
                        checked={acknowledged}
                        onChange={(e) => setAcknowledged(e.target.checked)}
                        className="mt-0.5 accent-primary cursor-pointer"
                    />
                    <span>
                        I confirm I own this content or have the rights to process it. I am responsible for any content I submit. See our <a href="/#legal" target="_blank" rel="noopener noreferrer" className="text-primary underline" onClick={(e) => e.stopPropagation()}>Terms & Privacy</a>.
                    </span>
                </label>

                <button
                    type="submit"
                    disabled={isProcessing || !acknowledged || (mode === 'url' && !url) || (mode === 'file' && !file)}
                    className="w-full btn-primary mt-4 flex items-center justify-center gap-2"
                >
                    {isProcessing ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Processing Video...
                        </>
                    ) : (
                        <>
                            Generate Clips
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
