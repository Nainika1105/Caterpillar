// Cab Voice & Industrial Audio Alert Engine

class CabAudioAlertService {
  private audioCtx: AudioContext | null = null;
  private lastSpokenTime: Record<string, number> = {};
  private muted: boolean = false;

  constructor() {
    // AudioContext will be initialized on first user interaction
  }

  private initAudio() {
    if (!this.audioCtx && typeof window !== 'undefined') {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  public setMuted(muted: boolean) {
    this.muted = muted;
  }

  public isMuted(): boolean {
    return this.muted;
  }

  /**
   * Play heavy equipment dual-tone warning chime
   */
  public playIndustrialChirp(critical = false) {
    if (this.muted) return;
    try {
      this.initAudio();
      if (!this.audioCtx) return;

      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = critical ? 'sawtooth' : 'triangle';
      
      // Dual burst
      osc.frequency.setValueAtTime(critical ? 980 : 750, now);
      osc.frequency.exponentialRampToValueAtTime(critical ? 520 : 440, now + 0.15);

      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.26);

      // Repeat second chime if critical
      if (critical) {
        setTimeout(() => {
          if (!this.audioCtx) return;
          const now2 = this.audioCtx.currentTime;
          const osc2 = this.audioCtx.createOscillator();
          const gain2 = this.audioCtx.createGain();
          osc2.type = 'sawtooth';
          osc2.frequency.setValueAtTime(1100, now2);
          osc2.frequency.exponentialRampToValueAtTime(580, now2 + 0.18);
          gain2.gain.setValueAtTime(0.35, now2);
          gain2.gain.exponentialRampToValueAtTime(0.01, now2 + 0.28);
          osc2.connect(gain2);
          gain2.connect(this.audioCtx.destination);
          osc2.start(now2);
          osc2.stop(now2 + 0.29);
        }, 180);
      }
    } catch {
      // Audio autoplay policy fallback
    }
  }

  /**
   * Speak clear in-cab voice instruction using Web Speech API
   */
  public speak(message: string, key = 'general', cooldownSecs = 10) {
    if (this.muted) return;
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    const now = Date.now();
    const lastTime = this.lastSpokenTime[key] || 0;
    if (now - lastTime < cooldownSecs * 1000) {
      return; // respect cab cooldown so operator isn't distracted
    }

    this.lastSpokenTime[key] = now;

    // Play tone first
    this.playIndustrialChirp(true);

    setTimeout(() => {
      window.speechSynthesis.cancel(); // cancel any active queue
      const utterance = new SpeechSynthesisUtterance(message);
      utterance.rate = 1.05;
      utterance.pitch = 0.95; // deeper, authoritative voice
      utterance.volume = 1.0;

      // Select natural English voice if present
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('David') || v.name.includes('George')));
      if (preferred) {
        utterance.voice = preferred;
      }

      window.speechSynthesis.speak(utterance);
    }, 280);
  }
}

export const cabAudio = new CabAudioAlertService();
