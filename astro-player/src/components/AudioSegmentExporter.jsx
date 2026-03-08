/**
 * AudioSegmentExporter.jsx
 */

const parseSrtTime = (t) => {
  if (!t) return 0;
  const [h, m, s] = t.split(":");
  const [sec, ms] = s.split(",");
  return parseInt(h) * 3600 + parseInt(m) * 60 + parseInt(sec) + parseInt(ms) / 1000;
};

const toWavBlob = (buf) => {
  const ch = buf.numberOfChannels;
  const sr = buf.sampleRate;
  const n  = buf.length;
  const out = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const str = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));

  str(0, "RIFF"); out.setUint32(4, 36 + n * ch * 2, true);
  str(8, "WAVE"); str(12, "fmt ");
  out.setUint32(16, 16, true); out.setUint16(20, 1, true);
  out.setUint16(22, ch, true); out.setUint32(24, sr, true);
  out.setUint32(28, sr * ch * 2, true); out.setUint16(32, ch * 2, true);
  out.setUint16(34, 16, true);
  str(36, "data"); out.setUint32(40, n * ch * 2, true);

  let o = 44;
  const channels = Array.from({ length: ch }, (_, c) => buf.getChannelData(c));
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < ch; c++) {
      const s = Math.max(-1, Math.min(1, channels[c][i]));
      out.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      o += 2;
    }
  }

  return new Blob([out.buffer], { type: "audio/wav" });
};

/**
 * 提取并压缩片段
 * @param {AudioBuffer} audioBuffer  - 从 WaveSurfer 获取的解码数据
 * @param {string} baseFilename      - 原始文件名
 * @param {Object} srtEntry          - srtData[i]
 * @param {Object} [opts]
 */
export const extractSegment = async (audioBuffer, baseFilename, srtEntry, { padding = 0.1, targetSampleRate = 22050 } = {}) => {
  const start = Math.max(0, parseSrtTime(srtEntry.startTime) - padding);
  
  // 确保结束时间不超过音频总时长
  const end = Math.min(parseSrtTime(srtEntry.endTime) + padding, audioBuffer.duration);
  const duration = end - start;

  if (duration <= 0) throw new Error("无效的裁切区间");

  // 核心魔法：使用 OfflineAudioContext 一次性完成【裁切】+【单声道混合】+【降采样】
  // 参数: (声道数 1, 总采样数, 目标采样率 16000)
  const offlineCtx = new window.OfflineAudioContext(1, duration * targetSampleRate, targetSampleRate);
  
  const source = offlineCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineCtx.destination);
  
  // 从原音频的 start 秒开始播放，持续 duration 秒
  source.start(0, start, duration);

  // 渲染出新的轻量级 AudioBuffer
  const downsampledSeg = await offlineCtx.startRendering();

  // 转换为 WAV Blob
  const blob = toWavBlob(downsampledSeg);
  const filename = `${baseFilename.replace(/\.[^.]+$/, "")}_seg${srtEntry.id}.wav`;
  
  return { blobUrl: URL.createObjectURL(blob), blob, filename };
};