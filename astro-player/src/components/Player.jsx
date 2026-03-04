import { useState, useEffect, useRef, useCallback } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";
import srtParser2 from "srt-parser-2";
import { extractSegment } from "./AudioSegmentExporter";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Repeat,
  Repeat1,
  Eye,
  EyeOff,
  Copy,
  Music,
  Type,
  Command,
  RefreshCw,
} from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// ==============================================================================
// ⚙️ 全局配置
// ==============================================================================
const CONFIG = {
  PADDING_SEC: 0.1,
  TOAST_DURATION: 1500,
  WAVE_HEIGHT: 64,
};

// --- Utils ---
const cn = (...inputs) => twMerge(clsx(inputs));

const parseTime = (timeStr) => {
  if (!timeStr) return 0;
  const [h, m, s] = timeStr.split(":");
  const [sec, ms] = s.split(",");
  return (
    parseInt(h) * 3600 + parseInt(m) * 60 + parseInt(sec) + parseInt(ms) / 1000
  );
};

const maskText = (text) => text;

const useLatest = (value) => {
  const ref = useRef(value);
  ref.current = value;
  return ref;
};

// --- Sub-Components ---

const IconButton = ({
  icon: Icon,
  onClick,
  active,
  disabled,
  title,
  variant = "default",
}) => (
  <button
    onClick={onClick}
    disabled={disabled}
    title={title}
    className={cn(
      "p-2 rounded-lg transition-all duration-200 flex items-center justify-center active:scale-95",
      "disabled:opacity-20 disabled:cursor-not-allowed",
      variant === "primary"
        ? "bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]"
        : active
          ? "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/50"
          : "text-slate-400 hover:text-slate-100 hover:bg-white/5",
    )}
  >
    <Icon size={20} fill={variant === "primary" ? "currentColor" : "none"} />
  </button>
);

const Toast = ({ message, visible }) => (
  <div
    className={cn(
      "absolute top-4 left-1/2 -translate-x-1/2 z-50 px-3 py-1.5 bg-emerald-500/90 backdrop-blur text-slate-950 text-xs font-bold rounded-full shadow-lg transition-all duration-300 pointer-events-none",
      visible ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-2",
    )}
  >
    {message}
  </div>
);

const ShortcutRow = ({ label, keys }) => (
  <div className="flex items-center justify-between text-[10px]">
    <span className="text-slate-400 font-medium">{label}</span>
    <div className="flex gap-1">
      {keys.map((k) => (
        <span
          key={k}
          className="min-w-[18px] h-[18px] px-1 flex items-center justify-center bg-white/10 rounded text-slate-200 font-mono shadow-sm border border-white/5"
        >
          {k}
        </span>
      ))}
    </div>
  </div>
);

// --- Main Component ---

const Player = ({ session, onReset }) => {
  const containerRef = useRef(null);
  const wavesurfer = useRef(null);
  const wsRegions = useRef(null);
  const reachedEndRef = useRef(false);

  const srtData = useState(() =>
    session.srtText ? new srtParser2().fromSrt(session.srtText) : [],
  )[0];

  // 👈 核心修复 1：引入同步的 Ref 来追踪索引，防止 React setState 异步导致的错乱
  const syncIdxRef = useRef(srtData.length > 0 ? 0 : -1);

  const [state, setState] = useState({
    currentIdx: srtData.length > 0 ? 0 : -1,
    playMode: "sequential",
    showSubtitle: true,
    isPlaying: false,
    isReady: false,
    duration: 0,
  });

  const [toast, setToast] = useState({ msg: "", visible: false });
  const toastTimeout = useRef(null);
  const stateRef = useLatest(state);

  const showToast = (msg) => {
    if (toastTimeout.current) clearTimeout(toastTimeout.current);
    setToast({ msg, visible: true });
    toastTimeout.current = setTimeout(
      () => setToast((p) => ({ ...p, visible: false })),
      CONFIG.TOAST_DURATION,
    );
  };

  const srtDataRef = useRef(srtData);

  // --- Logic: Segment Playback ---
  const playSegment = useCallback((index, forceRestart = true) => {
    const { duration, playMode } = stateRef.current;
    const srtData = srtDataRef.current;
    if (!wavesurfer.current || !srtData[index]) return;

    reachedEndRef.current = false;
    const sub = srtData[index];
    const start = Math.max(0, parseTime(sub.startTime) - CONFIG.PADDING_SEC);
    const end = Math.min(duration || wavesurfer.current.getDuration(), parseTime(sub.endTime) + CONFIG.PADDING_SEC);

    syncIdxRef.current = index; // 👈 每次切换段落，立刻同步最新索引
    setState((prev) => ({ ...prev, currentIdx: index }));

    wsRegions.current.clearRegions();
    const region = wsRegions.current.addRegion({
      start,
      end,
      color: "rgba(16, 185, 129, 0.15)",
      drag: false,
      resize: false,
    });

    if (forceRestart) {
      if (playMode === "single") {
        region.play();
      } else {
        wavesurfer.current.setTime(start);
        wavesurfer.current.play();
      }
    }
  }, []);

  // --- Logic: Toggle Play/Pause ---
  const togglePlayPause = useCallback(() => {
    const { isPlaying, playMode } = stateRef.current;
    const currentIdx = syncIdxRef.current; // 使用同步的索引
    
    if (isPlaying) {
      wavesurfer.current?.pause();
    } else {
      if (playMode === "single") {
        if (reachedEndRef.current) {
          playSegment(currentIdx, true); 
        } else {
          wavesurfer.current?.play(); 
        }
      } else {
        wavesurfer.current?.play();
      }
    }
  }, [playSegment]);

  // --- Effect: WaveSurfer Setup ---
  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#334155",
      progressColor: "#10b981",
      cursorColor: "#ffffff",
      height: CONFIG.WAVE_HEIGHT,
      normalize: true,
      backend: "WebAudio",
      barWidth: 2,
      barGap: 2,
      barRadius: 2,
    });

    const wsRegionsInstance = ws.registerPlugin(RegionsPlugin.create());
    wsRegions.current = wsRegionsInstance;

    ws.on("ready", () => {
      setState((p) => ({ ...p, isReady: true, duration: ws.getDuration() }));
      if (srtDataRef.current.length > 0) {
        setTimeout(() => playSegment(0, false), 0);
      }
    });

    ws.on("play", () => setState((p) => ({ ...p, isPlaying: true })));
    ws.on("pause", () => setState((p) => ({ ...p, isPlaying: false })));

    wsRegionsInstance.on("region-out", (region) => {
      if (stateRef.current.playMode === "single" && ws.isPlaying()) {
        ws.pause();
        reachedEndRef.current = true;
      }
    });

    // 👈 核心修复 2：防止幽灵跳跃
    ws.on("timeupdate", (currentTime) => {
      // 过滤掉暂停状态下、因为音频节点卸载导致的异常时间偏移！
      if (!ws.isPlaying()) return; 

      if (stateRef.current.playMode === "sequential") {
        const srtData = srtDataRef.current;
        const currentIdx = syncIdxRef.current; // 使用最新、最准确的底层索引！
        
        const newIdx = srtData.findIndex(
          (s) => currentTime >= parseTime(s.startTime) && currentTime <= parseTime(s.endTime)
        );
        
        const regions = wsRegionsInstance.getRegions();
        if (newIdx !== -1 && (newIdx !== currentIdx || regions.length === 0)) {
          playSegment(newIdx, false);
        }
      }
    });

    ws.on("interaction", (newTime) => {
      reachedEndRef.current = false;
      const srtData = srtDataRef.current;
      const newIdx = srtData.findIndex(
        (s) =>
          newTime >= parseTime(s.startTime) && newTime <= parseTime(s.endTime),
      );
      if (newIdx !== -1) playSegment(newIdx, false);
    });

    wavesurfer.current = ws;
    return () => ws.destroy();
  }, [playSegment]);

  // --- Effect: Load Audio ---
  useEffect(() => {
    if (session.audioFile) {
      wavesurfer.current?.load(URL.createObjectURL(session.audioFile));
    }
  }, [session.audioFile]);

  // --- Effect: Keyboard Shortcuts ---
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      const srtData = srtDataRef.current;
      const { isReady } = stateRef.current;
      const currentIdx = syncIdxRef.current; // 👈 快捷键同样依赖同步的索引
      
      if (!isReady || srtData.length === 0) return;

      const actions = {
        Space: () => {
          e.preventDefault();
          togglePlayPause();
        },
        ArrowUp: () => {
          e.preventDefault();
          if (currentIdx !== -1) playSegment(currentIdx, true);
        },
        ArrowDown: () => {
          e.preventDefault();
          setState((p) => ({ ...p, showSubtitle: !p.showSubtitle }));
        },
        ArrowLeft: () => {
          e.preventDefault();
          if (currentIdx > 0) playSegment(currentIdx - 1, true);
        },
        ArrowRight: () => {
          e.preventDefault();
          if (currentIdx < srtDataRef.current.length - 1)
            playSegment(currentIdx + 1, true);
        },
        KeyR: () => {
          setState((p) => {
            const newMode = p.playMode === "sequential" ? "single" : "sequential";
            showToast(`Mode: ${newMode === "single" ? "Single Pause" : "Sequential"}`);
            return { ...p, playMode: newMode };
          });
        },
        KeyC: () => {
          if ((e.metaKey || e.ctrlKey) && currentIdx !== -1) {
            e.preventDefault();
            navigator.clipboard.writeText(srtDataRef.current[currentIdx].text);
            showToast("Copied");
          }
        },
        KeyX: () => {
          if (!session.audioFile || currentIdx === -1) return;
          showToast("Exporting…");
          extractSegment(session.audioFile, srtDataRef.current[currentIdx]).then(({ blobUrl, filename }) => {
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = filename;
            a.click();
            setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
            showToast(`${filename} downloaded!`);
          }).catch(() => showToast("Export failed"));
        },
      };

      if (actions[e.code]) actions[e.code]();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [playSegment, togglePlayPause]);

  const currentSub = state.currentIdx !== -1 ? srtData[state.currentIdx] : null;

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <div className="w-full max-w-[640px] bg-slate-900/50 backdrop-blur-md rounded-2xl border border-white/5 shadow-2xl relative overflow-hidden transition-all duration-500">
        <Toast message={toast.msg} visible={toast.visible} />

        {/* --- Header --- */}
        <div className="py-2 px-4 flex justify-between items-center border-b border-white/5 bg-white/5">
          <div className="flex items-center gap-3 text-xs font-medium text-slate-400">
            <div className="flex items-center gap-1.5">
              <Music size={12} />
              <span className="max-w-[150px] truncate">
                {session.audioFile?.name || "-"}
              </span>
            </div>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-1.5">
              <Type size={12} />
              <span>{srtData.length} lines</span>
            </div>
          </div>
          <button
            onClick={onReset}
            title="换一个文件"
            className="flex items-center gap-1.5 text-[10px] text-slate-600 uppercase tracking-widest font-bold hover:text-emerald-400 transition-colors"
          >
            <RefreshCw size={10} />
            Reset
          </button>
        </div>

        {/* --- Main Content --- */}
        <div className="p-6">
          <div className="min-h-[140px] flex flex-col items-center justify-center text-center mb-6 px-4 gap-4">
            {currentSub ? (
              <>
                <div
                  className={cn(
                    "text-xl md:text-2xl font-medium leading-relaxed max-w-prose transition-all duration-300",
                    state.showSubtitle
                      ? "text-slate-200 drop-shadow-md"
                      : "text-slate-800 blur-[4px] select-none",
                  )}
                >
                  {state.showSubtitle
                    ? currentSub.text
                    : maskText(currentSub.text)}
                </div>

                <div className="text-[10px] font-mono font-medium text-slate-500 bg-white/5 px-3 py-1 rounded-full border border-white/5 select-none">
                  {currentSub.startTime}
                  <span className="mx-2 text-slate-700">/</span>
                  {currentSub.endTime}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center gap-2 opacity-50">
                <div className="w-1 h-1 bg-slate-600 rounded-full animate-ping" />
                <span className="text-slate-600 text-xs font-medium tracking-widest uppercase">
                  Ready
                </span>
              </div>
            )}
          </div>

          <div className="mb-6 rounded-lg overflow-hidden ring-1 ring-white/5 bg-slate-950/50 relative h-[64px]">
            <div
              ref={containerRef}
              className="w-full opacity-80 hover:opacity-100 transition-opacity"
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between bg-white/5 rounded-xl p-2 border border-white/5">
            <div className="flex gap-1">
              <IconButton
                icon={state.playMode === "single" ? Repeat1 : Repeat}
                onClick={() => {
                  const newMode = state.playMode === "sequential" ? "single" : "sequential";
                  setState((p) => ({ ...p, playMode: newMode }));
                  showToast(`Mode: ${newMode === "single" ? "Single Pause" : "Sequential"}`);
                }}
                active={state.playMode === "single"}
                title={state.playMode === "single" ? "Single Sentence (R)" : "Sequential Play (R)"}
              />
              <IconButton
                icon={state.showSubtitle ? Eye : EyeOff}
                onClick={() =>
                  setState((p) => ({ ...p, showSubtitle: !p.showSubtitle }))
                }
                title="Toggle Text (Down)"
              />
            </div>

            <div className="flex items-center gap-3">
              <IconButton
                icon={SkipBack}
                onClick={() => playSegment(state.currentIdx - 1, true)}
                disabled={state.currentIdx <= 0}
              />
              <IconButton
                icon={state.isPlaying ? Pause : Play}
                variant="primary"
                onClick={togglePlayPause}
                disabled={!state.isReady}
              />
              <IconButton
                icon={SkipForward}
                onClick={() => playSegment(state.currentIdx + 1, true)}
                disabled={state.currentIdx >= srtData.length - 1}
              />
            </div>

            <div className="flex gap-1">
              <IconButton
                icon={Copy}
                onClick={() => {
                  if (currentSub) {
                    navigator.clipboard.writeText(currentSub.text);
                    showToast("Copied");
                  }
                }}
                disabled={!currentSub}
                title="Copy (Cmd+C)"
              />
              <div className="w-px h-6 bg-white/10 mx-1 self-center" />

              <div className="relative group flex items-center">
                <div className="flex items-center px-3 py-1.5 text-[10px] font-mono font-medium text-slate-500 hover:text-emerald-400 transition-colors cursor-help select-none bg-transparent hover:bg-white/5 rounded-lg">
                  <Command size={12} className="mr-1.5" />
                  <span>Keys</span>
                </div>
                <div className="absolute bottom-full right-0 mb-3 w-56 p-3 bg-slate-900/95 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl opacity-0 translate-y-2 pointer-events-none group-hover:opacity-100 group-hover:translate-y-0 group-hover:pointer-events-auto transition-all duration-200 z-50 origin-bottom-right">
                  <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      Shortcuts
                    </span>
                    <span className="text-[10px] text-slate-600">v1.0</span>
                  </div>
                  <div className="space-y-1.5">
                    <ShortcutRow label="Play / Pause" keys={["Space"]} />
                    <ShortcutRow label="Replay Segment" keys={["↑"]} />
                    <ShortcutRow label="Prev / Next" keys={["←", "→"]} />
                    <ShortcutRow label="Toggle Mode" keys={["R"]} />
                    <ShortcutRow label="Toggle Text" keys={["↓"]} />
                    <ShortcutRow label="Copy Text" keys={["⌘", "C"]} />
                  </div>
                  <div className="absolute -bottom-1 right-6 w-2 h-2 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Player;