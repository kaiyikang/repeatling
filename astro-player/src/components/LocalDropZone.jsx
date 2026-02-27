import { useRef } from "react";
import { Upload } from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const cn = (...inputs) => twMerge(clsx(inputs));

/**
 * LocalDropZone
 * 负责本地文件的拖拽/点击选取，解析后通过 onImport 上报统一格式。
 *
 * @param {{ onImport: (session: { audioFile: File|null, srtText: string|null }) => void }} props
 */
const LocalDropZone = ({ onImport }) => {
  const inputRef = useRef(null);

  const handleFiles = async (files) => {
    const audioFile =
      files.find(
        (f) => f.type.startsWith("audio/") || /\.(mp3|wav|m4a)$/i.test(f.name),
      ) ?? null;
    const srtFile = files.find((f) => /\.srt$/i.test(f.name)) ?? null;
    const srtText = srtFile ? await srtFile.text() : null;
    onImport({ audioFile, srtText });
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDrop={(e) => {
        e.preventDefault();
        handleFiles(Array.from(e.dataTransfer.files));
      }}
      onDragOver={(e) => e.preventDefault()}
      className={cn(
        "cursor-pointer group",
        "py-12 flex flex-col items-center gap-4",
        "rounded-2xl border border-dashed border-white/10",
        "bg-white/[0.02] hover:bg-white/[0.05] hover:border-emerald-500/30",
        "transition-all duration-300",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        accept=".mp3,.wav,.srt,audio/*"
        onChange={(e) => handleFiles(Array.from(e.target.files))}
      />

      <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 group-hover:text-emerald-400 group-hover:scale-110 transition-all">
        <Upload size={20} />
      </div>
      <p className="text-sm text-slate-500 font-medium group-hover:text-slate-400 transition-colors">
        Drop Audio &amp; SRT here
      </p>
    </div>
  );
};

export default LocalDropZone;
