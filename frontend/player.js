/**
 * Custom Audio Player Engine
 * Поддерживает гибридный режим: Range Streaming (онлайн) и IndexedDB Blob (офлайн).
 * Интегрирован с MediaSession API для управления со шторки и экрана блокировки.
 */
class AudioPlayerEngine {
  constructor(audioElement, db) {
    this.audio = audioElement;
    this.db = db;

    this.queue = [];
    this.currentIndex = -1;
    this.isPlaying = false;
    this.repeatMode = 'all'; // 'off' | 'one' | 'all'
    this.isShuffle = false;
    this.currentBlobUrl = null;
    this.previousVolume = 1.0;

    // Инициализация громкости из localStorage
    const savedVol = localStorage.getItem('player_volume');
    this.audio.volume = savedVol !== null ? parseFloat(savedVol) : 0.8;

    // Callbacks
    this.onTrackChange = null;
    this.onStateChange = null;
    this.onTimeUpdate = null;
    this.onVolumeChange = null;
    this.onError = null;

    // Web Audio API EQ & FX State
    this.audioCtx = null;
    this.sourceNode = null;
    this.filter60 = null;
    this.filter250 = null;
    this.filter1000 = null;
    this.filter4000 = null;
    this.bassBoostNode = null;
    this.pannerNode = null;
    this.analyser = null;
    this.eqEnabled = true;
    this.bassBoostEnabled = true;
    this.currentGains = [4.0, -1.5, 2.5, -0.5]; // Пресет Deep по умолчанию (как на макете)

    this._bindEvents();
    this._initMediaSession();
  }

  initWebAudio() {
    if (this.audioCtx) {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume().catch(() => {});
      }
      return;
    }

    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      this.audioCtx = new AudioContext();

      // Источник
      this.sourceNode = this.audioCtx.createMediaElementSource(this.audio);

      // 4-полосный эквалайзер
      this.filter60 = this.audioCtx.createBiquadFilter();
      this.filter60.type = 'lowshelf';
      this.filter60.frequency.value = 60;
      this.filter60.gain.value = this.currentGains[0];

      this.filter250 = this.audioCtx.createBiquadFilter();
      this.filter250.type = 'peaking';
      this.filter250.frequency.value = 250;
      this.filter250.Q.value = 1.0;
      this.filter250.gain.value = this.currentGains[1];

      this.filter1000 = this.audioCtx.createBiquadFilter();
      this.filter1000.type = 'peaking';
      this.filter1000.frequency.value = 1000;
      this.filter1000.Q.value = 1.0;
      this.filter1000.gain.value = this.currentGains[2];

      this.filter4000 = this.audioCtx.createBiquadFilter();
      this.filter4000.type = 'highshelf';
      this.filter4000.frequency.value = 4000;
      this.filter4000.gain.value = this.currentGains[3];

      // Bass Boost (80 Hz lowshelf)
      this.bassBoostNode = this.audioCtx.createBiquadFilter();
      this.bassBoostNode.type = 'lowshelf';
      this.bassBoostNode.frequency.value = 80;
      this.bassBoostNode.gain.value = 4.0;

      // Stereo Panner (Balance)
      if (this.audioCtx.createStereoPanner) {
        this.pannerNode = this.audioCtx.createStereoPanner();
        this.pannerNode.pan.value = 0;
      }

      // Analyser Node (Waveform / Frequency)
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 64;
      this.analyser.smoothingTimeConstant = 0.8;

      // Соединение графа звука
      let node = this.sourceNode;
      node = node.connect(this.filter60);
      node = node.connect(this.filter250);
      node = node.connect(this.filter1000);
      node = node.connect(this.filter4000);
      node = node.connect(this.bassBoostNode);
      if (this.pannerNode) {
        node = node.connect(this.pannerNode);
      }
      node.connect(this.analyser);
      this.analyser.connect(this.audioCtx.destination);
    } catch (e) {
      console.warn('Web Audio API EQ init warning (будет использован обычный стереовывод):', e);
    }
  }

  setEqGains(g60, g250, g1000, g4000) {
    this.initWebAudio();
    this.currentGains = [g60, g250, g1000, g4000];
    if (!this.filter60) return;
    if (this.eqEnabled) {
      this.filter60.gain.value = g60;
      this.filter250.gain.value = g250;
      this.filter1000.gain.value = g1000;
      this.filter4000.gain.value = g4000;
    }
  }

  setEqEnabled(enabled) {
    this.initWebAudio();
    this.eqEnabled = enabled;
    if (!this.filter60) return;
    if (enabled) {
      const [g60, g250, g1000, g4000] = this.currentGains;
      this.filter60.gain.value = g60;
      this.filter250.gain.value = g250;
      this.filter1000.gain.value = g1000;
      this.filter4000.gain.value = g4000;
    } else {
      this.filter60.gain.value = 0;
      this.filter250.gain.value = 0;
      this.filter1000.gain.value = 0;
      this.filter4000.gain.value = 0;
    }
  }

  setBassBoost(enabled, intensity = 4.0) {
    this.initWebAudio();
    this.bassBoostEnabled = enabled;
    if (!this.bassBoostNode) return;
    this.bassBoostNode.gain.value = enabled ? intensity : 0;
  }

  setStereoBalance(pan) {
    this.initWebAudio();
    if (!this.pannerNode) return;
    const clamped = Math.max(-1, Math.min(1, pan));
    this.pannerNode.pan.value = clamped;
  }

  getVisualizerData() {
    if (!this.analyser) return null;
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    return dataArray;
  }

  _bindEvents() {
    this.audio.addEventListener('play', () => {
      this.isPlaying = true;
      if (this.onStateChange) this.onStateChange(true);
      this._updateMediaSessionState();
    });

    this.audio.addEventListener('pause', () => {
      this.isPlaying = false;
      if (this.onStateChange) this.onStateChange(false);
      this._updateMediaSessionState();
    });

    this.audio.addEventListener('timeupdate', () => {
      if (this.onTimeUpdate) {
        this.onTimeUpdate(this.audio.currentTime, this.audio.duration || 0);
      }
    });

    this.audio.addEventListener('ended', () => {
      this._handleTrackEnd();
    });

    this.audio.addEventListener('error', (e) => {
      console.error('Ошибка воспроизведения аудио:', e);
      if (this.onError) this.onError(this.audio.error);
    });
  }

  _initMediaSession() {
    if (!('mediaSession' in navigator)) return;

    navigator.mediaSession.setActionHandler('play', () => this.play());
    navigator.mediaSession.setActionHandler('pause', () => this.pause());
    navigator.mediaSession.setActionHandler('previoustrack', () => this.prev());
    navigator.mediaSession.setActionHandler('nexttrack', () => this.next());
    navigator.mediaSession.setActionHandler('seekto', (details) => {
      if (details.seekTime !== undefined) {
        this.seek(details.seekTime);
      }
    });
  }

  _updateMediaSessionMetadata(track) {
    if (!('mediaSession' in navigator) || !track) return;

    const artwork = [];
    if (track.cover_url) {
      artwork.push({ src: track.cover_url, sizes: '512x512', type: 'image/jpeg' });
    }

    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: track.album || '',
      artwork: artwork,
    });
  }

  _updateMediaSessionState() {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.playbackState = this.isPlaying ? 'playing' : 'paused';
  }

  setQueue(tracks, startIndex = 0) {
    this.queue = [...tracks];
    this.currentIndex = startIndex;
    if (this.queue.length > 0 && startIndex >= 0 && startIndex < this.queue.length) {
      this.loadTrack(this.queue[this.currentIndex], true);
    }
  }

  async loadTrack(track, autoPlay = true) {
    if (!track) return;

    // Очищаем предыдущий Blob URL во избежание утечек памяти
    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = null;
    }

    try {
      // 1. Проверяем локальное хранилище IndexedDB
      const offlineBlob = await this.db.getAudioBlob(track.id);

      if (offlineBlob) {
        // Воспроизведение из офлайн-памяти без сети
        this.currentBlobUrl = URL.createObjectURL(offlineBlob);
        this.audio.src = this.currentBlobUrl;
      } else {
        // Онлайн стриминг с поддержкой HTTP Range
        this.audio.src = track.stream_url;
      }

      this._updateMediaSessionMetadata(track);
      if (this.onTrackChange) this.onTrackChange(track);

      if (autoPlay) {
        await this.play();
      }
    } catch (err) {
      console.error('Не удалось загрузить трек:', err);
      if (this.onError) this.onError(err);
    }
  }

  getCurrentTrack() {
    if (this.currentIndex >= 0 && this.currentIndex < this.queue.length) {
      return this.queue[this.currentIndex];
    }
    return null;
  }

  async play() {
    this.initWebAudio();
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      try {
        await this.audioCtx.resume();
      } catch (_) {}
    }

    try {
      await this.audio.play();
    } catch (err) {
      console.warn('Автовоспроизведение заблокировано браузером до первого клика:', err);
    }
  }

  pause() {
    this.audio.pause();
  }

  reset() {
    this.pause();
    this.currentIndex = -1;
    this.queue = [];
    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = null;
    }
    this.audio.removeAttribute('src');
    this.audio.load();
    if (this.onStateChange) this.onStateChange(false);
  }

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  seek(seconds) {
    if (this.audio.duration) {
      this.audio.currentTime = Math.min(Math.max(0, seconds), this.audio.duration);
    }
  }

  next() {
    if (this.queue.length === 0) return;

    if (this.isShuffle) {
      this.currentIndex = Math.floor(Math.random() * this.queue.length);
    } else {
      this.currentIndex = (this.currentIndex + 1) % this.queue.length;
    }

    this.loadTrack(this.queue[this.currentIndex], true);
  }

  prev() {
    if (this.queue.length === 0) return;

    // Если прошло больше 3 секунд, сначала возвращаем в начало трека
    if (this.audio.currentTime > 3) {
      this.seek(0);
      return;
    }

    this.currentIndex = (this.currentIndex - 1 + this.queue.length) % this.queue.length;
    this.loadTrack(this.queue[this.currentIndex], true);
  }

  toggleRepeat() {
    if (this.repeatMode === 'all') {
      this.repeatMode = 'one';
    } else if (this.repeatMode === 'one') {
      this.repeatMode = 'off';
    } else {
      this.repeatMode = 'all';
    }
    return this.repeatMode;
  }

  toggleShuffle() {
    this.isShuffle = !this.isShuffle;
    return this.isShuffle;
  }

  setVolume(val) {
    const clamped = Math.max(0, Math.min(1, val));
    this.audio.volume = clamped;
    localStorage.setItem('player_volume', clamped.toString());
    if (this.onVolumeChange) this.onVolumeChange(clamped);
    return clamped;
  }

  getVolume() {
    return this.audio.volume;
  }

  toggleMute() {
    if (this.audio.volume > 0) {
      this.previousVolume = this.audio.volume;
      return this.setVolume(0);
    } else {
      return this.setVolume(this.previousVolume || 0.8);
    }
  }

  _handleTrackEnd() {
    if (this.repeatMode === 'one') {
      this.seek(0);
      this.play();
    } else if (this.repeatMode === 'all') {
      this.next();
    } else {
      // repeat off
      if (this.currentIndex < this.queue.length - 1) {
        this.next();
      } else {
        this.pause();
        this.seek(0);
      }
    }
  }
}

if (typeof window !== 'undefined') {
  window.AudioPlayerEngine = AudioPlayerEngine;
}
