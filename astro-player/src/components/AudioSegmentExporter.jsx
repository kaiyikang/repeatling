/**
 * AudioSegmentExporter.jsx
 *
 * extractSegment(audioFile, srtEntry, options?)
 *   → Promise<{ blobUrl, blob, filename }>
 *
 * srtEntry shape (srt-parser-2):
 *   { id, startTime, endTime, text }
 *   e.g. startTime = "00:00:05,200"
 */

const parseSrtTime = (t) => {
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
 * @param {File}   audioFile
 * @param {Object} srtEntry        - srtData[i]
 * @param {Object} [opts]
 * @param {number} [opts.padding]  - extra seconds before/after (default 0.1)
 * @returns {Promise<{ blobUrl: string, blob: Blob, filename: string }>}
 */
export const extractSegment = async (audioFile, srtEntry, { padding = 0.1 } = {}) => {
  const start = Math.max(0, parseSrtTime(srtEntry.startTime) - padding);
  const end   = parseSrtTime(srtEntry.endTime) + padding;

  const ctx  = new (window.AudioContext || window.webkitAudioContext)();
  const full = await ctx.decodeAudioData(await audioFile.arrayBuffer());
  await ctx.close();

  const sr       = full.sampleRate;
  const ch       = full.numberOfChannels;
  const s0       = Math.floor(start * sr);
  const len      = Math.floor(Math.min(end, full.duration) * sr) - s0;

  const seg = new AudioBuffer({ numberOfChannels: ch, length: len, sampleRate: sr });
  for (let c = 0; c < ch; c++)
    seg.getChannelData(c).set(full.getChannelData(c).subarray(s0, s0 + len));

  const blob = toWavBlob(seg);
  const filename = `${audioFile.name.replace(/\.[^.]+$/, "")}_seg${srtEntry.id}.wav`;
  return { blobUrl: URL.createObjectURL(blob), blob, filename };
};
