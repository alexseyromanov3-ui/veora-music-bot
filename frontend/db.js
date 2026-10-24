/**
 * IndexedDB модуль для надежного офлайн-хранилища Telegram Music Player.
 */
class OfflineStorageDB {
  constructor() {
    this.dbName = 'MusicBotOfflineDB';
    this.dbVersion = 1;
    this.db = null;
  }

  async init() {
    if (this.db) return this.db;
    if (typeof indexedDB === 'undefined') {
      console.warn('IndexedDB недоступен в данном окружении');
      return null;
    }

    return new Promise((resolve) => {
      try {
        const request = indexedDB.open(this.dbName, this.dbVersion);

        request.onupgradeneeded = (event) => {
          const db = event.target.result;

          // Хранилище метаданных треков
          if (!db.objectStoreNames.contains('tracks')) {
            db.createObjectStore('tracks', { keyPath: 'id' });
          }

          // Хранилище бинарных аудиофайлов (Blob)
          if (!db.objectStoreNames.contains('audio_blobs')) {
            db.createObjectStore('audio_blobs', { keyPath: 'id' });
          }
        };

        request.onsuccess = (event) => {
          this.db = event.target.result;
          resolve(this.db);
        };

        request.onerror = (event) => {
          console.warn('Ошибка инициализации IndexedDB:', event?.target?.error);
          resolve(null);
        };
      } catch (err) {
        console.warn('IndexedDB open error:', err);
        resolve(null);
      }
    });
  }

  /**
   * Сохраняет трек и его аудио Blob в IndexedDB.
   */
  async saveTrack(track, audioBlob, coverBlob = null) {
    await this.init();

    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(['tracks', 'audio_blobs'], 'readwrite');
      const trackStore = tx.objectStore('tracks');
      const blobStore = tx.objectStore('audio_blobs');

      const meta = {
        id: track.id,
        title: track.title,
        artist: track.artist,
        album: track.album,
        duration: track.duration,
        mime_type: track.mime_type || 'audio/mpeg',
        file_size: audioBlob.size,
        has_cover: !!coverBlob || track.has_cover,
        cover_blob: coverBlob,
        downloaded_at: Date.now(),
      };

      trackStore.put(meta);
      blobStore.put({ id: track.id, blob: audioBlob, size: audioBlob.size });

      tx.oncomplete = () => resolve(true);
      tx.onerror = (e) => reject(e.target.error);
    });
  }

  /**
   * Проверяет, сохранен ли трек локально.
   */
  async isTrackDownloaded(trackId) {
    await this.init();

    return new Promise((resolve) => {
      const tx = this.db.transaction('tracks', 'readonly');
      const store = tx.objectStore('tracks');
      const request = store.get(trackId);

      request.onsuccess = () => resolve(!!request.result);
      request.onerror = () => resolve(false);
    });
  }

  /**
   * Получает аудио Blob сохраненного трека.
   */
  async getAudioBlob(trackId) {
    await this.init();

    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('audio_blobs', 'readonly');
      const store = tx.objectStore('audio_blobs');
      const request = store.get(trackId);

      request.onsuccess = () => {
        if (request.result && request.result.blob) {
          resolve(request.result.blob);
        } else {
          resolve(null);
        }
      };
      request.onerror = (e) => reject(e.target.error);
    });
  }

  /**
   * Возвращает список всех сохраненных для офлайна треков.
   */
  async getAllTracks() {
    try {
      const db = await this.init();
      if (!db) return [];

      return new Promise((resolve) => {
        try {
          const tx = this.db.transaction('tracks', 'readonly');
          const store = tx.objectStore('tracks');
          const request = store.getAll();

          request.onsuccess = () => resolve(request.result || []);
          request.onerror = () => resolve([]);
        } catch (_) {
          resolve([]);
        }
      });
    } catch (_) {
      return [];
    }
  }

  /**
   * Удаляет трек из локального офлайн-хранилища.
   */
  async deleteTrack(trackId) {
    await this.init();

    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(['tracks', 'audio_blobs'], 'readwrite');
      tx.objectStore('tracks').delete(trackId);
      tx.objectStore('audio_blobs').delete(trackId);

      tx.oncomplete = () => resolve(true);
      tx.onerror = (e) => reject(e.target.error);
    });
  }

  /**
   * Считает общий объем занятой памяти офлайн-хранилищем в МБ.
   */
  async calculateStorageUsage() {
    await this.init();

    return new Promise((resolve) => {
      const tx = this.db.transaction('audio_blobs', 'readonly');
      const store = tx.objectStore('audio_blobs');
      const request = store.getAll();

      request.onsuccess = () => {
        const items = request.result || [];
        const totalBytes = items.reduce((sum, item) => sum + (item.size || 0), 0);
        const mb = (totalBytes / (1024 * 1024)).toFixed(1);
        resolve(`${mb} МБ`);
      };

      request.onerror = () => resolve('0 МБ');
    });
  }

  /**
   * Полная очистка офлайн-кэша.
   */
  async clearAll() {
    await this.init();

    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(['tracks', 'audio_blobs'], 'readwrite');
      tx.objectStore('tracks').clear();
      tx.objectStore('audio_blobs').clear();

      tx.oncomplete = () => resolve(true);
      tx.onerror = (e) => reject(e.target.error);
    });
  }
}

const offlineDB = new OfflineStorageDB();
if (typeof window !== 'undefined') {
  window.offlineDB = offlineDB;
}
