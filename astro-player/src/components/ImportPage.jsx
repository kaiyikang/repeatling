import { useState } from "react";
import LocalDropZone from "./LocalDropZone";
import Player from "./Player";

/**
 * ImportPage
 * 顶层容器，持有 session 状态。
 * session === null  → 显示导入界面
 * session !== null  → 显示播放器
 */
const ImportPage = () => {
  const [session, setSession] = useState(null);

  if (session) {
    return <Player session={session} onReset={() => setSession(null)} />;
  }

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <div className="w-full max-w-[640px] flex flex-col gap-6">
        {/* Title */}
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Repeatling
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Audio + SRT segment player
          </p>
        </div>

        {/* Local file import */}
        <LocalDropZone onImport={setSession} />

        {/* Future: Dropbox, YouTube, etc. */}
        {/* <DropboxPicker onImport={setSession} /> */}
      </div>
    </div>
  );
};

export default ImportPage;
