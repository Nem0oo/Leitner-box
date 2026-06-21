const MUTE_KEY = "leitner.sound_muted";

export function isMuted(): boolean {
  return localStorage.getItem(MUTE_KEY) === "true";
}

export function setMuted(muted: boolean): void {
  localStorage.setItem(MUTE_KEY, muted ? "true" : "false");
}

type SoundKind = "flip" | "success" | "fail";

// Short synthesized beeps via WebAudio so no binary audio assets are needed.
const TONES: Record<SoundKind, { freq: number; duration: number }> = {
  flip: { freq: 440, duration: 0.05 },
  success: { freq: 880, duration: 0.12 },
  fail: { freq: 220, duration: 0.18 },
};

let audioCtx: AudioContext | null = null;

export function playSound(kind: SoundKind): void {
  if (isMuted()) return;
  try {
    audioCtx ??= new AudioContext();
    const { freq, duration } = TONES[kind];
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.frequency.value = freq;
    osc.type = kind === "fail" ? "sawtooth" : "sine";
    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch {
    // ignore (e.g. audio context blocked before first user gesture)
  }
}
