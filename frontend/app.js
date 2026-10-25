/**
 * Главный модуль VEORA Music Player
 * Премиальный плеер: полноценная док-панель, громкость, перемотка, плейлисты, офлайн.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  // Элементы представлений и радиального меню CS2
  const viewCs2Hub = document.getElementById('view-cs2-hub');
  const viewSectionTracks = document.getElementById('view-section-tracks');
  const btnBackToWheel = document.getElementById('btn-back-to-wheel');
  const btnQuickWheelHeader = document.getElementById('btn-quick-wheel-header');
  const sectionViewTitle = document.getElementById('section-view-title');
  const sectionViewCount = document.getElementById('section-view-count');
  const cs2CenterHub = document.getElementById('cs2-center-hub');
  const btnQuickRandom = document.getElementById('btn-quick-random');
  const btnQuickContinue = document.getElementById('btn-quick-continue');

  const tracksListEl = document.getElementById('tracks-list');
  const emptyStateEl = document.getElementById('empty-state');
  const spinnerEl = document.getElementById('loading-spinner');
  const searchInput = document.getElementById('search-input');
  const searchClearBtn = document.getElementById('search-clear');
  const soundcloudSection = document.getElementById('soundcloud-section');
  const soundcloudStatus = document.getElementById('soundcloud-status');
  const soundcloudTracksList = document.getElementById('soundcloud-tracks-list');
  const btnSearchScTrigger = document.getElementById('btn-search-sc-trigger');
  const btnCs2QuickSc = document.getElementById('btn-cs2-quick-sc');

  let activeView = 'wheel'; // 'wheel' | 'section'
  let currentTab = 'all';

  const SECTOR_DATA = {
    all: { emoji: '🎵', title: 'Все треки', desc: 'Общий каталог всей музыки' },
    library: { emoji: '🎧', title: 'Моя музыка', desc: 'Ваша личная медиатека' },
    friends: { emoji: '👥', title: 'Друзья', desc: 'Музыка ваших друзей' },
    community: { emoji: '🌍', title: 'Лента', desc: 'Публичные треки сообщества' },
    playlists: { emoji: '💿', title: 'Плейлисты', desc: 'Музыкальные сборники' },
    favorites: { emoji: '❤️', title: 'Избранное', desc: 'Ваши любимые треки' },
    history: { emoji: '🕒', title: 'История', desc: 'Недавно прослушанные' },
    offline: { emoji: '⚡', title: 'Скачанные', desc: 'Офлайн треки в памяти' },
  };

  function updateHubPreview(tabKey) {
    const hubIcon = document.getElementById('cs2-hub-icon');
    const hubTitle = document.getElementById('cs2-hub-title');
    const hubDesc = document.getElementById('cs2-hub-desc');
    if (!hubIcon || !hubTitle || !hubDesc) return;

    if (tabKey && SECTOR_DATA[tabKey]) {
      const s = SECTOR_DATA[tabKey];
      hubIcon.textContent = s.emoji;
      hubTitle.textContent = s.title.toUpperCase();
      hubDesc.textContent = s.desc;
    } else {
      const cur = (typeof player !== 'undefined' && player?.getCurrentTrack) ? player.getCurrentTrack() : null;
      if (cur && player?.isPlaying) {
        hubIcon.textContent = '🔊';
        hubTitle.textContent = (cur.title || 'ИГРАЕТ').toUpperCase();
        hubDesc.textContent = cur.artist || 'VEORA Music';
      } else {
        hubIcon.textContent = '🎵';
        hubTitle.textContent = 'VEORA ПЛЕЕР';
        hubDesc.textContent = 'Нажмите на сектор';
      }
    }
  }

  function openWheelMenu() {
    activeView = 'wheel';
    if (viewCs2Hub) viewCs2Hub.classList.remove('hidden');
    if (viewSectionTracks) viewSectionTracks.classList.add('hidden');
    updateHubPreview(null);
    if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
  }

  async function openSection(tabName) {
    activeView = 'section';
    currentTab = tabName;
    if (viewCs2Hub) viewCs2Hub.classList.add('hidden');
    if (viewSectionTracks) viewSectionTracks.classList.remove('hidden');

    const meta = SECTOR_DATA[tabName] || { emoji: '🎵', title: 'Раздел' };
    if (sectionViewTitle) sectionViewTitle.textContent = `${meta.emoji} ${meta.title}`;
    if (sectionViewCount) sectionViewCount.textContent = 'Загрузка...';

    if (searchInput) searchInput.value = '';
    if (searchClearBtn) searchClearBtn.classList.add('hidden');

    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
    await loadTabContent('');
  }

  // Назначение событий на секторы колеса
  const wedges = document.querySelectorAll('.cs2-wedge');
  const sectorBtns = document.querySelectorAll('.cs2-sector-btn');

  wedges.forEach(wedge => {
    const tab = wedge.dataset.tab;
    const btn = document.querySelector(`.cs2-sector-btn[data-tab="${tab}"]`);

    wedge.addEventListener('mouseenter', () => {
      wedge.classList.add('active');
      if (btn) btn.classList.add('hovered');
      updateHubPreview(tab);
      if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
    });

    wedge.addEventListener('mouseleave', () => {
      wedge.classList.remove('active');
      if (btn) btn.classList.remove('hovered');
      updateHubPreview(null);
    });

    wedge.addEventListener('click', (e) => {
      e.preventDefault();
      openSection(tab);
    });
  });

  sectorBtns.forEach(btn => {
    const tab = btn.dataset.tab;
    const wedge = document.querySelector(`.cs2-wedge[data-tab="${tab}"]`);

    btn.addEventListener('mouseenter', () => {
      if (wedge) wedge.classList.add('active');
      btn.classList.add('hovered');
      updateHubPreview(tab);
      if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
    });

    btn.addEventListener('mouseleave', () => {
      if (wedge) wedge.classList.remove('active');
      btn.classList.remove('hovered');
      updateHubPreview(null);
    });

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openSection(tab);
    });
  });

  if (btnBackToWheel) {
    btnBackToWheel.addEventListener('click', (e) => {
      e.preventDefault();
      openWheelMenu();
    });
  }

  const btnRefreshSection = document.getElementById('btn-refresh-section');
  if (btnRefreshSection) {
    btnRefreshSection.addEventListener('click', async (e) => {
      e.preventDefault();
      btnRefreshSection.classList.add('spinning');
      if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
      try {
        await loadTabContent(searchInput ? searchInput.value.trim() : '');
        showToast('🔄 Список треков обновлен');
      } finally {
        setTimeout(() => btnRefreshSection.classList.remove('spinning'), 600);
      }
    });
  }

  // Авто-обновление при возврате в приложение (после отправки треков боту)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && activeView === 'section') {
      loadTabContent(searchInput ? searchInput.value.trim() : '');
    }
  });


  if (btnQuickWheelHeader) {
    btnQuickWheelHeader.addEventListener('click', (e) => {
      e.preventDefault();
      openWheelMenu();
    });
  }

  if (cs2CenterHub) {
    cs2CenterHub.addEventListener('click', () => {
      const cur = (typeof player !== 'undefined' && player?.getCurrentTrack) ? player.getCurrentTrack() : null;
      if (cur) {
        fullPlayer.classList.remove('hidden');
      } else {
        openSection('all');
      }
    });
  }

  if (btnQuickRandom) {
    btnQuickRandom.addEventListener('click', async () => {
      if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      showToast('🎲 Запуск случайного микса...');
      try {
        const resp = await fetch('/api/tracks?limit=50', { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          const allList = Array.isArray(data) ? data : (data.items || []);
          if (allList.length > 0) {
            const shuffled = [...allList].sort(() => Math.random() - 0.5);
            player.setQueue(shuffled, 0);
            player.play();
          } else {
            showToast('В медиатеке пока нет треков для микса');
          }
        }
      } catch (e) {
        console.warn('Ошибка случайного микса:', e);
      }
    });
  }

  if (btnQuickContinue) {
    btnQuickContinue.addEventListener('click', async () => {
      if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
      try {
        const resp = await fetch('/api/history/recently-played?limit=10', { headers: getAuthHeaders() });
        if (resp.ok) {
          const histTracks = await resp.json();
          if (histTracks && histTracks.length > 0) {
            player.setQueue(histTracks, 0);
            player.play();
            showToast(`▶️ Играет: ${histTracks[0].artist} — ${histTracks[0].title}`);
          } else {
            openSection('all');
          }
        }
      } catch (e) {
        openSection('all');
      }
    });
  }

  const btnChatCloud = document.getElementById('btn-chat-cloud');
  if (btnChatCloud) {
    btnChatCloud.addEventListener('click', (e) => {
      e.preventDefault();
      const chatUrl = 'https://t.me/+grWYykQ5uEY1M2Uy';
      if (tg && typeof tg.openTelegramLink === 'function') {
        tg.openTelegramLink(chatUrl);
      } else {
        window.open(chatUrl, '_blank');
      }
      if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
    });
  }

  const storageSizeEl = document.getElementById('storage-size');
  const storageBadge = document.getElementById('storage-badge');
  const statusDot = document.querySelector('.status-dot');
  const statusText = document.getElementById('status-text');

  // Главная док-панель плеера
  const dockTitle = document.getElementById('dock-title');
  const dockArtist = document.getElementById('dock-artist');
  const dockCover = document.getElementById('dock-cover');
  const dockSoundWave = document.getElementById('dock-sound-wave');
  const dockBtnPlay = document.getElementById('dock-btn-play');
  const dockPlayIcon = document.getElementById('dock-play-icon');
  const dockBtnPrev = document.getElementById('dock-btn-prev');
  const dockBtnNext = document.getElementById('dock-btn-next');
  const dockBtnShuffle = document.getElementById('dock-btn-shuffle');
  const dockBtnRepeat = document.getElementById('dock-btn-repeat');
  const dockBtnFav = document.getElementById('dock-btn-fav');
  const dockBtnDownload = document.getElementById('dock-btn-download');
  const dockBtnExpand = document.getElementById('dock-btn-expand');
  const dockTrackClickArea = document.getElementById('dock-track-click-area');
  const dockProgressFill = document.getElementById('dock-progress-fill');

  // Перемотка (Scrubber)
  const dockSeekSlider = document.getElementById('dock-seek-slider');
  const dockCurrentTime = document.getElementById('dock-current-time');
  const dockTotalDuration = document.getElementById('dock-total-duration');

  // Громкость (Volume)
  const dockVolumeSlider = document.getElementById('dock-volume-slider');
  const dockBtnVolume = document.getElementById('dock-btn-volume');
  const volumeIcon = document.getElementById('volume-icon');

  // Полноэкранный плеер (Cyber & Orbit Design)
  const fullPlayer = document.getElementById('full-player');
  const btnCloseFull = document.getElementById('btn-close-full');
  const fullTitle = document.getElementById('full-title');
  const fullArtist = document.getElementById('full-artist');
  const fullCover = document.getElementById('full-cover');
  const fullBtnPlay = document.getElementById('btn-play-large');
  const fullPlayIcon = document.getElementById('full-play-icon');
  const fullBtnPrev = document.getElementById('btn-prev');
  const fullBtnNext = document.getElementById('btn-next');
  const fullBtnShuffle = document.getElementById('btn-shuffle');
  const fullBtnRepeat = document.getElementById('btn-repeat');
  const fullBtnFavorite = document.getElementById('btn-full-favorite');
  const fullBtnOptions = document.getElementById('btn-full-options');
  const fullBtnAddPl = document.getElementById('btn-full-add-pl');
  const fullBtnOpenEq = document.getElementById('btn-full-open-eq');
  const seekSlider = document.getElementById('seek-slider');
  const currentTimeEl = document.getElementById('current-time');
  const totalDurationEl = document.getElementById('total-duration');
  const soundwaveContainer = document.getElementById('soundwave-container');
  const orbitProgressCircle = document.getElementById('orbit-progress-circle');
  const orbitBead = document.getElementById('orbit-bead');
  const orbitTimeBadge = document.getElementById('orbit-time-badge');

  // EQ Studio Modal
  const eqModal = document.getElementById('eq-studio-modal');
  const btnOpenEq = document.getElementById('btn-open-eq');
  const btnCloseEq = document.getElementById('btn-close-eq');
  const eqMasterToggle = document.getElementById('eq-master-toggle');
  const eqSlider60 = document.getElementById('eq-slider-60');
  const eqSlider250 = document.getElementById('eq-slider-250');
  const eqSlider1000 = document.getElementById('eq-slider-1000');
  const eqSlider4000 = document.getElementById('eq-slider-4000');
  const eqVal60 = document.getElementById('eq-val-60');
  const eqVal250 = document.getElementById('eq-val-250');
  const eqVal1000 = document.getElementById('eq-val-1000');
  const eqVal4000 = document.getElementById('eq-val-4000');
  const eqPresetPills = document.querySelectorAll('.eq-preset-pill');
  const btnResetEq = document.getElementById('btn-reset-eq');
  const eqBassToggle = document.getElementById('eq-bass-toggle');
  const eqBalanceSlider = document.getElementById('eq-balance-slider');
  const eqBalanceVal = document.getElementById('eq-balance-val');

  const fullVolumeSlider = document.getElementById('full-volume-slider');
  const fullVolIcon = document.getElementById('full-vol-icon');
  const fullBtnDownload = document.getElementById('btn-full-download');
  const fullDownloadText = document.getElementById('full-download-text');

  const toastEl = document.getElementById('toast');
  const tabBannerContainer = document.getElementById('tab-banner-container');

  // Модальные окна
  const trackActionsModal = document.getElementById('track-actions-modal');
  const btnCloseActionSheet = document.getElementById('btn-close-action-sheet');
  const actionSheetTrackTitle = document.getElementById('action-sheet-track-title');
  const sheetBtnAddPl = document.getElementById('sheet-btn-add-pl');
  const sheetBtnEdit = document.getElementById('sheet-btn-edit');
  const sheetBtnTogglePrivacy = document.getElementById('sheet-btn-toggle-privacy');
  const sheetPrivacyIcon = document.getElementById('sheet-privacy-icon');
  const sheetPrivacyText = document.getElementById('sheet-privacy-text');
  const sheetBtnDel = document.getElementById('sheet-btn-del');

  const createPlModal = document.getElementById('create-playlist-modal');
  const btnCloseCreatePl = document.getElementById('btn-close-create-pl');
  const btnSubmitCreatePl = document.getElementById('btn-submit-create-pl');
  const inputPlTitle = document.getElementById('new-playlist-title');
  const inputPlDesc = document.getElementById('new-playlist-desc');

  const addToPlModal = document.getElementById('add-to-pl-modal');
  const btnCloseAddPl = document.getElementById('btn-close-add-pl');
  const playlistPickerList = document.getElementById('playlist-picker-list');

  const editTrackModal = document.getElementById('edit-track-modal');
  const btnCloseEditTrack = document.getElementById('btn-close-edit-track');
  const btnSubmitEditTrack = document.getElementById('btn-submit-edit-track');
  const inputEditTitle = document.getElementById('edit-track-title');
  const inputEditArtist = document.getElementById('edit-track-artist');
  const inputEditAlbum = document.getElementById('edit-track-album');

  // Состояние
  const currentUserId = tg?.initDataUnsafe?.user?.id || 1;
  let tracks = [];
  let userPlaylists = [];
  let userFriends = [];
  let downloadedTrackIds = new Set();
  let isSeeking = false;
  let searchTimeout = null;

  let activeModalTrack = null;

  // Вспомогательный тост
  function showToast(msg, duration = 3000) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => {
      toastEl.classList.remove('show');
    }, duration);
  }

  // Инициализация плеера и офлайн БД
  await offlineDB.init();
  const player = new AudioPlayerEngine(document.getElementById('audio-engine'), offlineDB);

  // Инициализация громкости
  const currentVol = player.getVolume();
  dockVolumeSlider.value = Math.round(currentVol * 100);
  if (fullVolumeSlider) fullVolumeSlider.value = Math.round(currentVol * 100);
  updateVolumeIcons(currentVol);

  // Статус сети
  function updateOnlineStatus() {
    if (statusDot && statusText) {
      if (navigator.onLine) {
        statusDot.className = 'status-dot online';
        statusText.textContent = 'В сети';
      } else {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Офлайн';
      }
    }
  }
  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);
  updateOnlineStatus();

  // Размер памяти
  async function refreshStorageBadge() {
    const size = await offlineDB.calculateStorageUsage();
    if (storageSizeEl) storageSizeEl.textContent = size;
  }
  await refreshStorageBadge();

  if (storageBadge) {
    storageBadge.addEventListener('click', async () => {
      const usage = await offlineDB.calculateStorageUsage();
      if (usage === '0.0 МБ' || usage === '0 МБ') {
        alert('Офлайн-память свободна. Скачивайте треки кнопкой ⚡');
        return;
      }
      if (confirm(`Занято ${usage}. Очистить все сохраненные треки из памяти устройства?`)) {
        await offlineDB.clearAll();
        downloadedTrackIds.clear();
        await refreshStorageBadge();
        if (currentTab === 'offline') await loadTabContent();
        if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('warning');
      }
    });
  }

  // Заголовки авторизации
  function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (tg?.initData) {
      headers['X-Telegram-Init-Data'] = tg.initData;
    } else {
      headers['X-Telegram-Init-Data'] = 'mock_user_id=1';
    }
    return headers;
  }

  function formatTime(seconds) {
    const s = Math.floor(seconds || 0);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}:${rem < 10 ? '0' : ''}${rem}`;
  }

  // Загрузка контента вкладки
  async function loadTabContent(query = '') {
    spinnerEl.classList.remove('hidden');
    emptyStateEl.classList.add('hidden');
    tracksListEl.innerHTML = '';
    if (tabBannerContainer) tabBannerContainer.innerHTML = '';

    try {
      const offlineTracks = await offlineDB.getAllTracks();
      downloadedTrackIds = new Set(offlineTracks.map(t => t.id));

      if (currentTab === 'playlists') {
        await loadPlaylistsView();
      } else if (currentTab === 'offline') {
        tracks = offlineTracks.map(t => ({
          ...t,
          stream_url: '',
          download_url: '',
          has_cover: t.has_cover,
          cover_url: t.cover_blob ? URL.createObjectURL(t.cover_blob) : null,
        }));

        if (query) {
          const q = query.toLowerCase();
          tracks = tracks.filter(t =>
            t.title.toLowerCase().includes(q) ||
            t.artist.toLowerCase().includes(q) ||
            (t.album && t.album.toLowerCase().includes(q))
          );
        }
        renderTracksList(tracks);
      } else if (currentTab === 'friends') {
        // Загрузка друзей и формирование баннера
        try {
          const friendsResp = await fetch('/api/social/friends', { headers: getAuthHeaders() });
          userFriends = friendsResp.ok ? await friendsResp.json() : [];
        } catch (_) {
          userFriends = [];
        }

        const myId = tg?.initDataUnsafe?.user?.id || currentUserId;
        const myUsername = tg?.initDataUnsafe?.user?.username ? `@${tg.initDataUnsafe.user.username}` : '';
        const inviteLink = `https://t.me/VEORA_MUSIC_BOT?start=friend_${myId}`;

        if (tabBannerContainer) {
          tabBannerContainer.innerHTML = `
            <div class="social-hero-card">
              <div class="social-hero-header">
                <div class="social-hero-icon">👥</div>
                <div class="social-hero-text">
                  <h3>Музыка с друзьями</h3>
                  <p>Слушайте треки друзей и делитесь своей музыкой в одно касание</p>
                </div>
              </div>
              <div class="my-friend-id-badge" id="btn-copy-my-id" title="Нажмите, чтобы скопировать ID">
                Ваш ID: <strong>${myId}</strong> ${myUsername ? `(${myUsername})` : ''} <span>📋</span>
              </div>
              <button class="btn-social-action" id="btn-invite-friend">
                <span>🔗</span> Пригласить друга / Поделиться ссылкой
              </button>
              <div class="add-friend-box">
                <div class="add-friend-label">➕ Добавить друга по ID или @username:</div>
                <div class="add-friend-row">
                  <input type="text" id="input-add-friend" class="input-add-friend" placeholder="Например: 260397872 или @username" />
                  <button id="btn-submit-add-friend" class="btn-submit-add-friend">Добавить</button>
                </div>
              </div>
            </div>
            ${userFriends && userFriends.length > 0 ? `
              <div class="friends-strip-section">
                <div class="section-label">Ваши друзья (${userFriends.length})</div>
                <div class="friends-strip" id="friends-strip">
                  ${userFriends.map(f => `
                    <div class="friend-chip">
                      <div class="friend-avatar">${escapeHtml((f.first_name || f.username || 'F')[0].toUpperCase())}</div>
                      <div class="friend-chip-info">
                        <div class="friend-chip-name">${escapeHtml(f.first_name || (f.username ? '@' + f.username : 'Друг'))}</div>
                        <div class="friend-chip-count">${f.tracks_count} треков</div>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}
          `;

          const copyIdBtn = document.getElementById('btn-copy-my-id');
          if (copyIdBtn) {
            copyIdBtn.addEventListener('click', () => {
              if (navigator.clipboard) {
                navigator.clipboard.writeText(String(myId)).catch(() => {});
              }
              showToast(`📋 Ваш ID ${myId} скопирован!`);
              if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            });
          }

          const inviteBtn = document.getElementById('btn-invite-friend');
          if (inviteBtn) {
            inviteBtn.addEventListener('click', () => {
              const shareMsg = `🎧 Привет! Слушай музыку со мной в VEORA Music!\nМой ID: ${myId} ${myUsername}\n\n1️⃣ Нажми ссылку и нажми «СТАРТ» внизу чата:\n${inviteLink}\n\n2️⃣ Или открой плеер, перейди в «Друзья 👥» и введи мой ID: ${myId}`;
              if (navigator.clipboard) {
                navigator.clipboard.writeText(inviteLink).catch(() => {});
              }
              if (tg && typeof tg.openTelegramLink === 'function') {
                tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent(shareMsg)}`);
              }
              showToast('📋 Ссылка и ваш ID скопированы в буфер!');
              if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            });
          }

          const submitFriendBtn = document.getElementById('btn-submit-add-friend');
          const inputFriend = document.getElementById('input-add-friend');
          if (submitFriendBtn && inputFriend) {
            submitFriendBtn.addEventListener('click', async () => {
              const q = inputFriend.value.trim();
              if (!q) {
                showToast('Введите ID или @username друга');
                return;
              }
              submitFriendBtn.disabled = true;
              submitFriendBtn.textContent = '⏳';
              try {
                const resp = await fetch('/api/social/friends/connect', {
                  method: 'POST',
                  headers: getAuthHeaders(),
                  body: JSON.stringify({ query: q }),
                });
                const res = await resp.json();
                if (res.success) {
                  showToast(res.message || '🎉 Друг успешно добавлен!');
                  if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                  await loadTabContent('');
                } else {
                  showToast(res.message || 'Пользователь не найден');
                  if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
                }
              } catch (e) {
                showToast('Ошибка сети при добавлении друга');
              } finally {
                submitFriendBtn.disabled = false;
                submitFriendBtn.textContent = 'Добавить';
              }
            });
          }
        }

        const resp = await fetch('/api/social/friends/tracks?offset=0&limit=50', { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          tracks = data.items || [];
        } else {
          tracks = [];
        }

        if (query) {
          const q = query.toLowerCase();
          tracks = tracks.filter(t =>
            t.title.toLowerCase().includes(q) ||
            t.artist.toLowerCase().includes(q) ||
            (t.album && t.album.toLowerCase().includes(q))
          );
        }
        renderTracksList(tracks);
      } else if (currentTab === 'community') {
        if (tabBannerContainer) {
          tabBannerContainer.innerHTML = `
            <div class="social-hero-card">
              <div class="social-hero-header">
                <div class="social-hero-icon">🌍</div>
                <div class="social-hero-text">
                  <h3>Лента сообщества</h3>
                  <p>Публичная музыка, загруженная пользователями VEORA Music</p>
                </div>
              </div>
            </div>
          `;
        }

        let url = '/api/social/community?offset=0&limit=50';
        const resp = await fetch(url, { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          tracks = data.items || [];
        } else {
          tracks = [];
        }

        if (query) {
          const q = query.toLowerCase();
          tracks = tracks.filter(t =>
            t.title.toLowerCase().includes(q) ||
            t.artist.toLowerCase().includes(q) ||
            (t.album && t.album.toLowerCase().includes(q))
          );
        }
        renderTracksList(tracks);
      } else {
        let url = '/api/tracks';
        if (currentTab === 'library') {
          url = '/api/library/tracks';
        } else if (currentTab === 'favorites') {
          url = '/api/library/tracks?favorites_only=true';
        } else if (currentTab === 'history') {
          url = '/api/history/recently-played';
        }

        const separator = url.includes('?') ? '&' : '?';
        if (query && currentTab !== 'history') {
          url += `${separator}q=${encodeURIComponent(query)}`;
        }

        const resp = await fetch(url, { headers: getAuthHeaders() });
        if (resp.ok) {
          const data = await resp.json();
          tracks = Array.isArray(data) ? data : (data.items || []);
        } else {
          tracks = [];
        }

        if (query && currentTab === 'history') {
          const q = query.toLowerCase();
          tracks = tracks.filter(t =>
            t.title.toLowerCase().includes(q) ||
            t.artist.toLowerCase().includes(q) ||
            (t.album && t.album.toLowerCase().includes(q))
          );
        }

        renderTracksList(tracks);
      }

      if (sectionViewCount) {
        if (currentTab === 'playlists') {
          sectionViewCount.textContent = `${userPlaylists.length} плейлистов`;
        } else if (currentTab === 'friends') {
          sectionViewCount.textContent = `${tracks.length} треков (${userFriends.length} друзей)`;
        } else {
          sectionViewCount.textContent = `${tracks.length} треков`;
        }
      }

      // Если плеер еще пустой, предзагружаем первый трек в режиме готовности (строго на паузе)
      if (player.currentIndex === -1 && tracks.length > 0) {
        player.setQueue(tracks, 0, false);
      }

      // Если поиск по медиатеке не дал результатов, автоматически ищем в SoundCloud
      if (query && query.length >= 2 && tracks.length === 0) {
        searchSoundCloud(query);
      } else if (!query) {
        if (soundcloudSection) soundcloudSection.classList.add('hidden');
      }
    } catch (err) {
      console.warn('Ошибка загрузки данных вкладки:', err);
      if (currentTab !== 'offline') {
        const offlineTracks = await offlineDB.getAllTracks();
        downloadedTrackIds = new Set(offlineTracks.map(t => t.id));
        renderTracksList(offlineTracks);
      }
    } finally {
      spinnerEl.classList.add('hidden');
    }
  }

  // Отрисовка списка треков
  function renderTracksList(list) {
    tracksListEl.innerHTML = '';
    const currentTrack = player.getCurrentTrack();

    if (!list || list.length === 0) {
      if (sectionViewCount) sectionViewCount.textContent = '0 треков';
      emptyStateEl.classList.remove('hidden');
      if (currentTab === 'offline') {
        document.getElementById('empty-title').textContent = 'Нет скачанных треков';
        document.getElementById('empty-subtitle').textContent = 'Нажмите ⚡ у любого трека, чтобы слушать его без интернета';
      } else if (currentTab === 'favorites') {
        document.getElementById('empty-title').textContent = 'Избранное пусто';
        document.getElementById('empty-subtitle').textContent = 'Нажмите сердечко ❤️ рядом с треком, чтобы добавить его сюда';
      } else if (currentTab === 'history') {
        document.getElementById('empty-title').textContent = 'История прослушиваний пуста';
        document.getElementById('empty-subtitle').textContent = 'Включайте музыку, и ваши недавние треки появятся здесь';
      } else if (currentTab === 'friends') {
        document.getElementById('empty-title').textContent = 'Музыки друзей пока нет';
        document.getElementById('empty-subtitle').textContent = 'Пригласите друзей по кнопке выше, чтобы слушать их треки!';
      } else if (currentTab === 'community') {
        document.getElementById('empty-title').textContent = 'Лента сообщества пока пуста';
        document.getElementById('empty-subtitle').textContent = 'Загрузите трек боту, и он появится здесь для всех участников!';
      } else {
        document.getElementById('empty-title').textContent = 'В медиатеке пока пусто';
        document.getElementById('empty-subtitle').textContent = 'Отправьте аудиофайл боту в чат, и он сразу появится здесь';
      }
      return;
    }

    emptyStateEl.classList.add('hidden');
    if (sectionViewCount) {
      const n = Math.abs(list.length) % 100;
      const n1 = n % 10;
      let word = 'треков';
      if (n <= 10 || n >= 20) {
        if (n1 === 1) word = 'трек';
        else if (n1 >= 2 && n1 <= 4) word = 'трека';
      }
      sectionViewCount.textContent = `${list.length} ${word}`;
    }

    list.forEach((track, index) => {
      const isDownloaded = downloadedTrackIds.has(track.id);
      const isPlaying = currentTrack && currentTrack.id === track.id;

      const item = document.createElement('div');
      item.className = `track-item ${isPlaying ? 'playing' : ''}`;
      item.dataset.id = track.id;

      const coverHtml = track.cover_url
        ? `<img src="${track.cover_url}" alt="" onerror="this.onerror=null; this.parentElement.innerHTML='🎵';" />`
        : '🎵';

      item.innerHTML = `
        <div class="track-cover">
          ${coverHtml}
          ${isPlaying ? `
            <div class="track-sound-wave">
              <span></span><span></span><span></span><span></span>
            </div>
          ` : ''}
        </div>
        <div class="track-details">
          <div class="track-title">${escapeHtml(track.title)}</div>
          <div class="track-meta-row">
            <span class="track-artist">${escapeHtml(track.artist)}</span>
            <span class="track-duration">${track.duration ? formatTime(track.duration) : ''}</span>
            ${isDownloaded ? '<span class="offline-badge">ОФЛАЙН</span>' : ''}
            ${track.is_private ? '<span class="privacy-badge">🔒 Приватный</span>' : ''}
            ${track.uploader_name ? `<span class="uploader-badge">👤 ${escapeHtml(track.uploader_name)}</span>` : ''}
          </div>
        </div>
        <div class="track-actions">
          <button class="btn-track-action btn-fav ${track.is_favorite ? 'favorited' : ''}" data-id="${track.id}" title="В избранное">
            ${track.is_favorite ? '❤️' : '🤍'}
          </button>
          <button class="btn-track-action btn-download ${isDownloaded ? 'downloaded' : ''}" data-id="${track.id}" title="Скачать офлайн">
            ${isDownloaded ? '⚡' : '⬇️'}
          </button>
          <button class="btn-track-action btn-more-dots" data-id="${track.id}" title="Действия">
            •••
          </button>
        </div>
      `;

      // Клик по треку: запуск воспроизведения
      item.addEventListener('click', (e) => {
        if (e.target.closest('.btn-track-action')) return;
        player.setQueue(list, index);
      });

      // Избранное
      const favBtn = item.querySelector('.btn-fav');
      favBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await toggleFavorite(track, favBtn);
      });

      // Скачивание
      const dlBtn = item.querySelector('.btn-download');
      dlBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await handleDownloadClick(track, dlBtn);
      });

      // Меню действий (3 точки)
      const moreBtn = item.querySelector('.btn-more-dots');
      moreBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openTrackActionSheet(track);
      });

      tracksListEl.appendChild(item);
    });
  }

  // Отрисовка раздела Плейлистов
  async function loadPlaylistsView() {
    tracksListEl.innerHTML = `
      <button id="btn-show-create-pl" class="btn-create-pl-banner">
        ➕ Создать новый плейлист
      </button>
      <div id="playlists-grid" class="playlists-grid"></div>
    `;

    document.getElementById('btn-show-create-pl').addEventListener('click', () => {
      createPlModal.classList.remove('hidden');
      inputPlTitle.focus();
    });

    try {
      const resp = await fetch('/api/playlists', { headers: getAuthHeaders() });
      if (resp.ok) {
        userPlaylists = await resp.json();
        const grid = document.getElementById('playlists-grid');

        if (userPlaylists.length === 0) {
          emptyStateEl.classList.remove('hidden');
          document.getElementById('empty-title').textContent = 'У вас пока нет плейлистов';
          document.getElementById('empty-subtitle').textContent = 'Нажмите кнопку выше, чтобы создать плейлист';
          return;
        }

        emptyStateEl.classList.add('hidden');

        userPlaylists.forEach(pl => {
          const card = document.createElement('div');
          card.className = 'playlist-card';
          card.innerHTML = `
            <div class="playlist-cover-icon">💿</div>
            <div class="playlist-card-title">${escapeHtml(pl.title)}</div>
            <div class="playlist-card-count">${pl.tracks_count} треков</div>
          `;

          card.addEventListener('click', async () => {
            await openPlaylistDetail(pl.id);
          });

          grid.appendChild(card);
        });
      }
    } catch (err) {
      console.error('Ошибка загрузки плейлистов:', err);
    }
  }

  // Детали плейлиста
  async function openPlaylistDetail(playlistId) {
    spinnerEl.classList.remove('hidden');
    try {
      const resp = await fetch(`/api/playlists/${playlistId}`, { headers: getAuthHeaders() });
      if (resp.ok) {
        const pl = await resp.json();
        tracks = pl.tracks || [];

        tracksListEl.innerHTML = `
          <div style="margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <button id="btn-back-to-pls" class="btn-pill-action">⬅️ Все плейлисты</button>
            <div style="display: flex; gap: 8px; align-items: center;">
              <button id="btn-download-all-pl" class="btn-pill-action" style="font-size: 12px;">⚡ Скачать все</button>
              <button id="btn-del-pl" class="btn-track-action" style="color: #ef4444;" title="Удалить плейлист">🗑</button>
            </div>
          </div>
          <h2 style="font-size: 20px; font-weight: 800; margin-bottom: 4px;">${escapeHtml(pl.title)}</h2>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">${escapeHtml(pl.description || '')}</p>
          <div id="pl-tracks-sublist" class="tracks-list"></div>
        `;

        document.getElementById('btn-back-to-pls').addEventListener('click', () => {
          loadPlaylistsView();
        });

        const btnDownloadAll = document.getElementById('btn-download-all-pl');
        btnDownloadAll.addEventListener('click', async () => {
          if (!tracks || tracks.length === 0) return;
          btnDownloadAll.disabled = true;
          for (let i = 0; i < tracks.length; i++) {
            const tr = tracks[i];
            if (!downloadedTrackIds.has(tr.id)) {
              btnDownloadAll.textContent = `⏳ ${i + 1}/${tracks.length}...`;
              try {
                const [blob, coverBlob] = await Promise.all([
                  fetch(`/api/tracks/${tr.id}/download`, { headers: getAuthHeaders() }).then((r) => (r.ok ? r.blob() : null)),
                  tr.cover_url
                    ? fetch(tr.cover_url).then((r) => (r.ok ? r.blob() : null)).catch(() => null)
                    : Promise.resolve(null),
                ]);
                if (blob) {
                  await offlineDB.saveTrack(tr, blob, coverBlob);
                  downloadedTrackIds.add(tr.id);
                }
              } catch (_) {}
            }
          }
          await refreshStorageBadge();
          btnDownloadAll.textContent = '✅ Все скачано!';
          setTimeout(() => {
            btnDownloadAll.disabled = false;
            btnDownloadAll.textContent = '⚡ Скачать все';
          }, 3000);
        });

        document.getElementById('btn-del-pl').addEventListener('click', async () => {
          if (confirm(`Удалить плейлист "${pl.title}"?`)) {
            await fetch(`/api/playlists/${playlistId}`, { method: 'DELETE', headers: getAuthHeaders() });
            loadPlaylistsView();
          }
        });

        const sublist = document.getElementById('pl-tracks-sublist');
        if (tracks.length === 0) {
          sublist.innerHTML = '<div class="empty-subtitle">В этом плейлисте пока нет треков. Добавьте их кнопкой ••• у любого трека!</div>';
        } else {
          tracks.forEach((track, index) => {
            const item = document.createElement('div');
            item.className = 'track-item';
            item.innerHTML = `
              <div class="track-cover">${track.cover_url ? `<img src="${track.cover_url}" alt="" onerror="this.onerror=null; this.parentElement.innerHTML='🎵';" />` : '🎵'}</div>
              <div class="track-details">
                <div class="track-title">${escapeHtml(track.title)}</div>
                <div class="track-meta-row">
                  <span class="track-artist">${escapeHtml(track.artist)}</span>
                  <span class="track-duration">${track.duration ? formatTime(track.duration) : ''}</span>
                </div>
              </div>
              <div class="track-actions">
                <button class="btn-track-action btn-del-from-pl" title="Убрать из плейлиста">✕</button>
              </div>
            `;
            item.addEventListener('click', (e) => {
              if (e.target.closest('.btn-del-from-pl')) return;
              player.setQueue(tracks, index);
            });

            item.querySelector('.btn-del-from-pl').addEventListener('click', async (e) => {
              e.stopPropagation();
              await fetch(`/api/playlists/${playlistId}/tracks/${track.id}`, { method: 'DELETE', headers: getAuthHeaders() });
              item.remove();
            });

            sublist.appendChild(item);
          });
        }
      }
    } finally {
      spinnerEl.classList.add('hidden');
    }
  }

  // Создание плейлиста
  btnSubmitCreatePl.addEventListener('click', async () => {
    const title = inputPlTitle.value.trim();
    if (!title) return;

    try {
      const resp = await fetch('/api/playlists', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          title: title,
          description: inputPlDesc.value.trim() || null,
          is_public: false,
        }),
      });

      if (resp.ok) {
        createPlModal.classList.add('hidden');
        inputPlTitle.value = '';
        inputPlDesc.value = '';
        await loadPlaylistsView();
      }
    } catch (err) {
      console.error('Ошибка создания плейлиста:', err);
    }
  });

  btnCloseCreatePl.addEventListener('click', () => {
    createPlModal.classList.add('hidden');
  });

  // Модальное окно действий с треком (•••)
  function openTrackActionSheet(track) {
    activeModalTrack = track;
    actionSheetTrackTitle.textContent = `${track.artist} — ${track.title}`;

    if (sheetBtnTogglePrivacy) {
      const isMine = !track.uploader_id || track.uploader_id === currentUserId;
      if (isMine) {
        sheetBtnTogglePrivacy.style.display = 'flex';
        if (track.is_private) {
          sheetPrivacyIcon.textContent = '🌍';
          sheetPrivacyText.textContent = 'Сделать публичным для всех';
        } else {
          sheetPrivacyIcon.textContent = '🔒';
          sheetPrivacyText.textContent = 'Сделать приватным (только я)';
        }
      } else {
        sheetBtnTogglePrivacy.style.display = 'none';
      }
    }

    trackActionsModal.classList.remove('hidden');
  }

  if (sheetBtnTogglePrivacy) {
    sheetBtnTogglePrivacy.addEventListener('click', async () => {
      if (!activeModalTrack) return;
      const target = activeModalTrack;
      trackActionsModal.classList.add('hidden');

      try {
        const resp = await fetch(`/api/tracks/${target.id}/toggle-privacy`, {
          method: 'POST',
          headers: getAuthHeaders(),
        });
        if (resp.ok) {
          const res = await resp.json();
          target.is_private = res.is_private;
          showToast(target.is_private ? '🔒 Трек скрыт от всех (приватный)' : '🌍 Трек теперь открыт друзьям и в Ленте!');
          await loadTabContent(searchInput.value.trim());
          if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else {
          showToast('Не удалось изменить приватность');
        }
      } catch (err) {
        console.error('Ошибка toggle-privacy:', err);
      }
    });
  }

  btnCloseActionSheet.addEventListener('click', () => {
    trackActionsModal.classList.add('hidden');
  });

  sheetBtnAddPl.addEventListener('click', () => {
    trackActionsModal.classList.add('hidden');
    openAddToPlaylistModal(activeModalTrack);
  });

  sheetBtnEdit.addEventListener('click', () => {
    trackActionsModal.classList.add('hidden');
    openEditTrackModal(activeModalTrack);
  });

  sheetBtnDel.addEventListener('click', async () => {
    if (!activeModalTrack) return;
    const trackToDelete = activeModalTrack;
    trackActionsModal.classList.add('hidden');

    if (confirm(`Полностью удалить трек "${trackToDelete.title}" из базы и медиатеки?`)) {
      try {
        const resp = await fetch(`/api/tracks/${trackToDelete.id}`, {
          method: 'DELETE',
          headers: getAuthHeaders(),
        });

        if (resp.ok) {
          // Удаляем из офлайн-памяти устройства
          await offlineDB.deleteTrack(trackToDelete.id);
          downloadedTrackIds.delete(trackToDelete.id);

          // Если этот трек сейчас играет или выбран в плеере — сбрасываем плеер
          const current = player.getCurrentTrack();
          if (current && current.id === trackToDelete.id) {
            player.reset();
            dockTitle.textContent = 'Выберите трек';
            dockArtist.textContent = 'VEORA Music';
            dockCover.innerHTML = '🎵';
            dockCurrentTime.textContent = '0:00';
            dockTotalDuration.textContent = '0:00';
            dockSeekSlider.value = 0;
            dockProgressFill.style.width = '0%';
            dockBtnFav.classList.remove('favorited');
            dockBtnDownload.classList.remove('downloaded');
          }

          await refreshStorageBadge();
          await loadTabContent(searchInput.value.trim());
          if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else {
          alert('Не удалось удалить трек (возможно, он был загружен другим пользователем)');
        }
      } catch (err) {
        console.error('Ошибка удаления трека:', err);
      }
    }
  });

  // Диалог добавления в плейлист
  async function openAddToPlaylistModal(track) {
    activeModalTrack = track;
    playlistPickerList.innerHTML = '<div class="spinner"></div>';
    addToPlModal.classList.remove('hidden');

    try {
      const resp = await fetch('/api/playlists', { headers: getAuthHeaders() });
      if (resp.ok) {
        userPlaylists = await resp.json();
        playlistPickerList.innerHTML = '';

        if (userPlaylists.length === 0) {
          playlistPickerList.innerHTML = '<div class="empty-subtitle">Сначала создайте плейлист во вкладке "Плейлисты"</div>';
          return;
        }

        userPlaylists.forEach(pl => {
          const item = document.createElement('div');
          item.className = 'playlist-picker-item';
          item.innerHTML = `
            <span>💿</span>
            <div style="flex:1;">
              <div style="font-weight:700; font-size:13px;">${escapeHtml(pl.title)}</div>
              <div style="font-size:11px; color:var(--text-muted);">${pl.tracks_count} треков</div>
            </div>
            <span>➕</span>
          `;

          item.addEventListener('click', async () => {
            await fetch(`/api/playlists/${pl.id}/tracks`, {
              method: 'POST',
              headers: getAuthHeaders(),
              body: JSON.stringify({ track_id: activeModalTrack.id }),
            });
            addToPlModal.classList.add('hidden');
            if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
          });

          playlistPickerList.appendChild(item);
        });
      }
    } catch (err) {
      console.error('Ошибка загрузки плейлистов:', err);
    }
  }

  btnCloseAddPl.addEventListener('click', () => {
    addToPlModal.classList.add('hidden');
  });

  // Диалог редактирования трека
  function openEditTrackModal(track) {
    activeModalTrack = track;
    inputEditTitle.value = track.title || '';
    inputEditArtist.value = track.artist || '';
    inputEditAlbum.value = track.album || '';
    editTrackModal.classList.remove('hidden');
  }

  btnCloseEditTrack.addEventListener('click', () => {
    editTrackModal.classList.add('hidden');
  });

  btnSubmitEditTrack.addEventListener('click', async () => {
    if (!activeModalTrack) return;

    try {
      const resp = await fetch(`/api/tracks/${activeModalTrack.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          title: inputEditTitle.value.trim(),
          artist: inputEditArtist.value.trim(),
          album: inputEditAlbum.value.trim(),
        }),
      });

      if (resp.ok) {
        editTrackModal.classList.add('hidden');
        loadTabContent(searchInput.value.trim());
      } else {
        alert('Не удалось изменить теги');
      }
    } catch (err) {
      console.error('Ошибка сохранения тегов:', err);
    }
  });

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Переключение избранного
  async function toggleFavorite(track, buttonEl) {
    try {
      const resp = await fetch(`/api/tracks/${track.id}/favorite`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (resp.ok) {
        const data = await resp.json();
        track.is_favorite = data.is_favorite;
        if (buttonEl) {
          buttonEl.innerHTML = track.is_favorite ? '❤️' : '🤍';
          buttonEl.classList.toggle('favorited', track.is_favorite);
        }

        const current = player.getCurrentTrack();
        if (current && current.id === track.id) {
          dockBtnFav.innerHTML = track.is_favorite ? '❤️' : '🤍';
          dockBtnFav.classList.toggle('favorited', track.is_favorite);
          fullBtnFavorite.innerHTML = track.is_favorite ? '❤️' : '🤍';
        }
      }
    } catch (err) {
      console.error('Ошибка добавления в избранное:', err);
    }
  }

  // Скачивание трека в IndexedDB с прогрессом
  async function handleDownloadClick(track, buttonEl) {
    const isDownloaded = downloadedTrackIds.has(track.id);

    if (isDownloaded) {
      if (confirm(`Удалить "${track.title}" из офлайн-памяти устройства?`)) {
        await offlineDB.deleteTrack(track.id);
        downloadedTrackIds.delete(track.id);
        if (buttonEl) {
          buttonEl.innerHTML = '⬇️';
          buttonEl.classList.remove('downloaded');
        }
        await refreshStorageBadge();
        updateDockDownloadButton(track);
        if (currentTab === 'offline') loadTabContent(searchInput.value);
      }
      return;
    }

    if (buttonEl) buttonEl.innerHTML = '⏳';

    try {
      // Параллельное скачивание аудио и обложки для максимальной скорости
      const [audioBlob, coverBlob] = await Promise.all([
        fetch(`/api/tracks/${track.id}/download`, { headers: getAuthHeaders() }).then(async (r) => {
          if (!r.ok) throw new Error('Сетевая ошибка при скачивании аудио');
          return await r.blob();
        }),
        track.cover_url
          ? fetch(track.cover_url)
              .then((r) => (r.ok ? r.blob() : null))
              .catch(() => null)
          : Promise.resolve(null),
      ]);

      await offlineDB.saveTrack(track, audioBlob, coverBlob);
      downloadedTrackIds.add(track.id);

      if (buttonEl) {
        buttonEl.innerHTML = '⚡';
        buttonEl.classList.add('downloaded');
      }
      await refreshStorageBadge();
      updateDockDownloadButton(track);
      if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    } catch (err) {
      console.error('Ошибка сохранения офлайн-трека:', err);
      if (buttonEl) buttonEl.innerHTML = '❌';
      setTimeout(() => { if (buttonEl) buttonEl.innerHTML = '⬇️'; }, 2000);
    }
  }

  function updateDockDownloadButton(track) {
    if (!track) return;
    const isSaved = downloadedTrackIds.has(track.id);
    dockBtnDownload.classList.toggle('downloaded', isSaved);
    if (fullBtnDownload) {
      fullBtnDownload.classList.toggle('saved', isSaved);
      fullDownloadText.textContent = isSaved ? 'Сохранено офлайн ⚡' : 'Сохранить офлайн';
    }
  }

  // Громкость
  function updateVolumeIcons(val) {
    let icon = '🔊';
    if (val === 0) icon = '🔇';
    else if (val < 0.45) icon = '🔉';

    volumeIcon.textContent = icon;
    if (fullVolIcon) fullVolIcon.textContent = icon;
  }

  dockVolumeSlider.addEventListener('input', () => {
    const val = dockVolumeSlider.value / 100;
    player.setVolume(val);
    if (fullVolumeSlider) fullVolumeSlider.value = dockVolumeSlider.value;
    updateVolumeIcons(val);
  });

  if (fullVolumeSlider) {
    fullVolumeSlider.addEventListener('input', () => {
      const val = fullVolumeSlider.value / 100;
      player.setVolume(val);
      dockVolumeSlider.value = fullVolumeSlider.value;
      updateVolumeIcons(val);
    });
  }

  dockBtnVolume.addEventListener('click', () => {
    const newVol = player.toggleMute();
    dockVolumeSlider.value = Math.round(newVol * 100);
    if (fullVolumeSlider) fullVolumeSlider.value = dockVolumeSlider.value;
    updateVolumeIcons(newVol);
  });

  if (fullVolIcon) {
    fullVolIcon.addEventListener('click', () => {
      const newVol = player.toggleMute();
      dockVolumeSlider.value = Math.round(newVol * 100);
      if (fullVolumeSlider) fullVolumeSlider.value = dockVolumeSlider.value;
      updateVolumeIcons(newVol);
    });
  }

  // Инициализация звукового эквалайзера / визуализатора
  const SOUNDWAVE_BARS = 32;
  const waveBars = [];
  if (soundwaveContainer) {
    soundwaveContainer.innerHTML = '';
    for (let i = 0; i < SOUNDWAVE_BARS; i++) {
      const b = document.createElement('div');
      b.className = 'soundwave-bar';
      soundwaveContainer.appendChild(b);
      waveBars.push(b);
    }
  }

  function animateWaveform() {
    if (player.isPlaying && !fullPlayer.classList.contains('hidden')) {
      const data = player.getVisualizerData();
      for (let i = 0; i < waveBars.length; i++) {
        let h = 4;
        if (data && data.length > 0) {
          const val = data[i % data.length];
          h = Math.max(4, Math.round((val / 255) * 28));
        } else {
          const t = Date.now() / 180;
          h = Math.max(4, Math.round(14 + 10 * Math.sin(t + i * 0.4)));
        }
        waveBars[i].style.height = `${h}px`;
      }
    }
    requestAnimationFrame(animateWaveform);
  }
  requestAnimationFrame(animateWaveform);

  // Синхронизация плеера и история прослушиваний
  let historyRecordTimer = null;
  let lastRecordedTrackId = null;

  function scheduleHistoryRecord(track) {
    if (!track || !track.id) return;
    clearTimeout(historyRecordTimer);

    // Фиксируем прослушивание через 2 секунды реального воспроизведения
    historyRecordTimer = setTimeout(async () => {
      try {
        if (!player.isPlaying) return;
        const cur = player.getCurrentTrack();
        if (!cur || cur.id !== track.id) return;

        const playedSec = Math.max(1, Math.round(player.audio.currentTime || 2));
        const resp = await fetch('/api/history', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            track_id: track.id,
            duration_played: playedSec,
          }),
        });

        if (resp.ok) {
          lastRecordedTrackId = track.id;
          // Если пользователь прямо сейчас на вкладке истории, обновляем отображение
          if (currentTab === 'history') {
            loadTabContent(searchInput ? searchInput.value.trim() : '');
          }
        }
      } catch (err) {
        console.warn('Ошибка сохранения истории:', err);
      }
    }, 2000);
  }

  player.onTrackChange = (track) => {
    lastRecordedTrackId = null;
    scheduleHistoryRecord(track);
    updateHubPreview(null);

    // Dock Panel
    dockTitle.textContent = track.title;
    dockArtist.textContent = track.artist;
    dockCover.innerHTML = track.cover_url
      ? `<img src="${track.cover_url}" alt="" onerror="this.onerror=null; this.parentElement.innerHTML='🎵';" />`
      : '🎵';
    dockBtnFav.innerHTML = track.is_favorite ? '❤️' : '🤍';
    dockBtnFav.classList.toggle('favorited', track.is_favorite);
    dockTotalDuration.textContent = track.duration ? formatTime(track.duration) : '0:00';
    updateDockDownloadButton(track);

    // Fullscreen Player (Cyber & Orbit)
    fullTitle.textContent = track.title;
    fullArtist.textContent = track.artist;
    fullCover.innerHTML = track.cover_url
      ? `<img src="${track.cover_url}" alt="" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'orbit-disc-placeholder\\'>🎵</div>';" />`
      : '<div class="orbit-disc-placeholder">🎵</div>';
    fullBtnFavorite.textContent = track.is_favorite ? '❤️' : '♡';
    fullBtnFavorite.classList.toggle('favorited', track.is_favorite);
    totalDurationEl.textContent = track.duration ? formatTime(track.duration) : '0:00';

    if (orbitProgressCircle) orbitProgressCircle.style.strokeDashoffset = '716.28';
    if (orbitBead) {
      orbitBead.setAttribute('cx', '130');
      orbitBead.setAttribute('cy', '16');
    }
    if (orbitTimeBadge) {
      orbitTimeBadge.textContent = `0:00 / ${track.duration ? formatTime(track.duration) : '0:00'}`;
    }

    // Подсветка в списке
    document.querySelectorAll('.track-item').forEach(el => {
      const isThis = parseInt(el.dataset.id, 10) === track.id;
      el.classList.toggle('playing', isThis);
    });
  };

  player.onStateChange = (isPlaying) => {
    updateHubPreview(null);
    dockPlayIcon.textContent = isPlaying ? '⏸' : '▶';
    if (fullPlayIcon) fullPlayIcon.textContent = isPlaying ? '⏸' : '▶';
    dockSoundWave.classList.toggle('active', isPlaying);
    if (fullCover) fullCover.classList.toggle('rotating', isPlaying);

    if (isPlaying) {
      const cur = player.getCurrentTrack();
      if (cur && cur.id !== lastRecordedTrackId) {
        scheduleHistoryRecord(cur);
      }
    } else {
      clearTimeout(historyRecordTimer);
    }
  };

  player.onTimeUpdate = (current, duration) => {
    if (!isSeeking && duration > 0) {
      const percent = (current / duration) * 100;
      dockProgressFill.style.width = `${percent}%`;
      dockSeekSlider.value = percent;
      seekSlider.value = percent;

      const curStr = formatTime(current);
      dockCurrentTime.textContent = curStr;
      currentTimeEl.textContent = curStr;

      if (duration) {
        const durStr = formatTime(duration);
        dockTotalDuration.textContent = durStr;
        totalDurationEl.textContent = durStr;
      }

      // Обновление орбитального кольца и бегунка
      const progress = Math.min(1, Math.max(0, current / duration));
      const circumference = 716.28;
      const dashoffset = circumference * (1 - progress);
      if (orbitProgressCircle) {
        orbitProgressCircle.style.strokeDashoffset = dashoffset.toFixed(2);
      }
      const angle = (progress * 2 * Math.PI) - (Math.PI / 2);
      const cx = 130 + 114 * Math.cos(angle);
      const cy = 130 + 114 * Math.sin(angle);
      if (orbitBead) {
        orbitBead.setAttribute('cx', cx.toFixed(2));
        orbitBead.setAttribute('cy', cy.toFixed(2));
      }
      if (orbitTimeBadge) {
        orbitTimeBadge.textContent = `${curStr} / ${formatTime(duration)}`;
      }
    }
  };

  // EQ Studio Presets & Controls
  const EQ_PRESETS = {
    flat: { gains: [0, 0, 0, 0], bass: false },
    deep: { gains: [4.0, -1.5, 2.5, -0.5], bass: true }, // Из скриншота пользователя
    vocal: { gains: [-1.0, 2.0, 4.0, 1.0], bass: false },
    electronic: { gains: [5.0, 2.0, -1.0, 3.5], bass: true },
    rock: { gains: [3.5, 1.0, -1.0, 4.0], bass: true },
    bass: { gains: [6.0, 3.0, 0.0, 1.0], bass: true },
  };

  function applyEqSliders(g60, g250, g1000, g4000) {
    if (eqSlider60) eqSlider60.value = g60;
    if (eqSlider250) eqSlider250.value = g250;
    if (eqSlider1000) eqSlider1000.value = g1000;
    if (eqSlider4000) eqSlider4000.value = g4000;

    if (eqVal60) eqVal60.textContent = (g60 >= 0 ? '+' : '') + Number(g60).toFixed(1);
    if (eqVal250) eqVal250.textContent = (g250 >= 0 ? '+' : '') + Number(g250).toFixed(1);
    if (eqVal1000) eqVal1000.textContent = (g1000 >= 0 ? '+' : '') + Number(g1000).toFixed(1);
    if (eqVal4000) eqVal4000.textContent = (g4000 >= 0 ? '+' : '') + Number(g4000).toFixed(1);

    player.setEqGains(g60, g250, g1000, g4000);
  }

  [eqSlider60, eqSlider250, eqSlider1000, eqSlider4000].forEach((slider) => {
    if (slider) {
      slider.addEventListener('input', () => {
        const g60 = parseFloat(eqSlider60.value);
        const g250 = parseFloat(eqSlider250.value);
        const g1000 = parseFloat(eqSlider1000.value);
        const g4000 = parseFloat(eqSlider4000.value);
        applyEqSliders(g60, g250, g1000, g4000);
        eqPresetPills.forEach(p => p.classList.remove('active'));
      });
    }
  });

  eqPresetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const presetKey = pill.dataset.preset;
      const p = EQ_PRESETS[presetKey];
      if (p) {
        applyEqSliders(p.gains[0], p.gains[1], p.gains[2], p.gains[3]);
        if (eqBassToggle) {
          eqBassToggle.checked = p.bass;
          player.setBassBoost(p.bass, 4.0);
        }
        eqPresetPills.forEach(b => b.classList.remove('active'));
        pill.classList.add('active');
        if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
      }
    });
  });

  if (eqMasterToggle) {
    eqMasterToggle.addEventListener('change', () => {
      player.setEqEnabled(eqMasterToggle.checked);
      showToast(eqMasterToggle.checked ? '🎚️ Эквалайзер включен' : 'Эквалайзер выключен');
    });
  }

  if (eqBassToggle) {
    eqBassToggle.addEventListener('change', () => {
      player.setBassBoost(eqBassToggle.checked, 4.0);
      showToast(eqBassToggle.checked ? '🔊 Bass Boost активен' : 'Bass Boost выключен');
    });
  }

  if (eqBalanceSlider) {
    eqBalanceSlider.addEventListener('input', () => {
      const pan = parseFloat(eqBalanceSlider.value);
      player.setStereoBalance(pan);
      if (pan === 0) {
        eqBalanceVal.textContent = '0';
      } else if (pan < 0) {
        eqBalanceVal.textContent = `L ${Math.round(-pan * 100)}%`;
      } else {
        eqBalanceVal.textContent = `R ${Math.round(pan * 100)}%`;
      }
    });
  }

  if (btnResetEq) {
    btnResetEq.addEventListener('click', () => {
      const flat = EQ_PRESETS.flat;
      applyEqSliders(flat.gains[0], flat.gains[1], flat.gains[2], flat.gains[3]);
      if (eqBassToggle) {
        eqBassToggle.checked = false;
        player.setBassBoost(false, 0);
      }
      if (eqBalanceSlider) {
        eqBalanceSlider.value = 0;
        player.setStereoBalance(0);
        eqBalanceVal.textContent = '0';
      }
      eqPresetPills.forEach(b => b.classList.toggle('active', b.dataset.preset === 'flat'));
    });
  }

  if (btnOpenEq) btnOpenEq.addEventListener('click', () => eqModal.classList.remove('hidden'));
  if (fullBtnOpenEq) fullBtnOpenEq.addEventListener('click', () => eqModal.classList.remove('hidden'));
  if (btnCloseEq) btnCloseEq.addEventListener('click', () => eqModal.classList.add('hidden'));

  if (fullBtnOptions) {
    fullBtnOptions.addEventListener('click', () => {
      const current = player.getCurrentTrack();
      if (current) openTrackActionSheet(current);
    });
  }

  if (fullBtnAddPl) {
    fullBtnAddPl.addEventListener('click', () => {
      const current = player.getCurrentTrack();
      if (current) openAddToPlaylistModal(current);
    });
  }

  // Перемотка на док-панели
  dockSeekSlider.addEventListener('input', () => {
    isSeeking = true;
    if (player.audio.duration) {
      const time = (dockSeekSlider.value / 100) * player.audio.duration;
      dockCurrentTime.textContent = formatTime(time);
    }
  });

  dockSeekSlider.addEventListener('change', () => {
    if (player.audio.duration) {
      const time = (dockSeekSlider.value / 100) * player.audio.duration;
      player.seek(time);
    }
    isSeeking = false;
  });

  // Перемотка в полноэкранном режиме
  seekSlider.addEventListener('input', () => {
    isSeeking = true;
    if (player.audio.duration) {
      const time = (seekSlider.value / 100) * player.audio.duration;
      currentTimeEl.textContent = formatTime(time);
    }
  });

  seekSlider.addEventListener('change', () => {
    if (player.audio.duration) {
      const time = (seekSlider.value / 100) * player.audio.duration;
      player.seek(time);
    }
    isSeeking = false;
  });

  // Кнопки управления
  dockBtnPlay.addEventListener('click', (e) => {
    e.stopPropagation();
    player.togglePlay();
  });

  dockBtnNext.addEventListener('click', (e) => {
    e.stopPropagation();
    player.next();
  });

  dockBtnPrev.addEventListener('click', (e) => {
    e.stopPropagation();
    player.prev();
  });

  dockBtnShuffle.addEventListener('click', (e) => {
    e.stopPropagation();
    const active = player.toggleShuffle();
    dockBtnShuffle.classList.toggle('active', active);
    fullBtnShuffle.classList.toggle('active', active);
  });

  dockBtnRepeat.addEventListener('click', (e) => {
    e.stopPropagation();
    const mode = player.toggleRepeat();
    dockBtnRepeat.classList.toggle('active', mode !== 'off');
    fullBtnRepeat.classList.toggle('active', mode !== 'off');
  });

  dockBtnFav.addEventListener('click', async (e) => {
    e.stopPropagation();
    const current = player.getCurrentTrack();
    if (current) await toggleFavorite(current, dockBtnFav);
  });

  dockBtnDownload.addEventListener('click', async (e) => {
    e.stopPropagation();
    const current = player.getCurrentTrack();
    if (current) await handleDownloadClick(current, null);
  });

  dockTrackClickArea.addEventListener('click', () => {
    fullPlayer.classList.remove('hidden');
  });

  dockBtnExpand.addEventListener('click', (e) => {
    e.stopPropagation();
    fullPlayer.classList.remove('hidden');
  });

  btnCloseFull.addEventListener('click', () => {
    fullPlayer.classList.add('hidden');
  });

  fullBtnPlay.addEventListener('click', () => player.togglePlay());
  fullBtnNext.addEventListener('click', () => player.next());
  fullBtnPrev.addEventListener('click', () => player.prev());
  fullBtnShuffle.addEventListener('click', () => {
    const active = player.toggleShuffle();
    dockBtnShuffle.classList.toggle('active', active);
    fullBtnShuffle.classList.toggle('active', active);
  });
  fullBtnRepeat.addEventListener('click', () => {
    const mode = player.toggleRepeat();
    dockBtnRepeat.classList.toggle('active', mode !== 'off');
    fullBtnRepeat.classList.toggle('active', mode !== 'off');
  });
  if (fullBtnFavorite) {
    fullBtnFavorite.addEventListener('click', async () => {
      const current = player.getCurrentTrack();
      if (current) await toggleFavorite(current, dockBtnFav);
    });
  }

  if (fullBtnDownload) {
    fullBtnDownload.addEventListener('click', async () => {
      const current = player.getCurrentTrack();
      if (current) await handleDownloadClick(current, null);
    });
  }

  // Поиск
  searchInput.addEventListener('input', () => {
    const val = searchInput.value.trim();
    searchClearBtn.classList.toggle('hidden', val.length === 0);
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      loadTabContent(val);
    }, 300);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = searchInput.value.trim();
      if (val) searchSoundCloud(val);
    }
  });

  searchClearBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchClearBtn.classList.add('hidden');
    if (soundcloudSection) soundcloudSection.classList.add('hidden');
    loadTabContent('');
  });

  if (btnSearchScTrigger) {
    btnSearchScTrigger.addEventListener('click', () => {
      const val = searchInput ? searchInput.value.trim() : '';
      searchSoundCloud(val);
    });
  }

  if (btnCs2QuickSc) {
    btnCs2QuickSc.addEventListener('click', async () => {
      await openSection('all');
      if (searchInput) {
        searchInput.focus();
        const val = searchInput.value.trim();
        if (val) {
          searchSoundCloud(val);
        } else {
          showToast('🔍 Введите название песни в поле поиска');
        }
      }
    });
  }

  let scSearchController = null;

  async function searchSoundCloud(q) {
    if (!q || !q.trim()) {
      showToast('Введите название трека или артиста');
      searchInput?.focus();
      return;
    }
    const cleanQ = q.trim();

    if (soundcloudSection) soundcloudSection.classList.remove('hidden');
    if (soundcloudStatus) soundcloudStatus.textContent = '⏳ Поиск...';
    if (soundcloudTracksList) soundcloudTracksList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px 0;">🔍 Ищем треки в SoundCloud...</div>';

    if (scSearchController) {
      try { scSearchController.abort(); } catch(_) {}
    }
    scSearchController = new AbortController();

    try {
      const resp = await fetch(`/api/search/soundcloud?q=${encodeURIComponent(cleanQ)}&limit=8`, {
        headers: getAuthHeaders(),
        signal: scSearchController.signal,
      });

      if (!resp.ok) {
        if (soundcloudStatus) soundcloudStatus.textContent = 'Ошибка';
        if (soundcloudTracksList) soundcloudTracksList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;">Не удалось загрузить данные из SoundCloud</div>';
        return;
      }

      const data = await resp.json();
      const items = data.items || [];

      if (items.length === 0) {
        if (soundcloudStatus) soundcloudStatus.textContent = '0 найдено';
        if (soundcloudTracksList) soundcloudTracksList.innerHTML = `<div style="color:var(--text-muted);font-size:12px;">По запросу «${escapeHtml(cleanQ)}» ничего не найдено в SoundCloud</div>`;
        return;
      }

      if (soundcloudStatus) soundcloudStatus.textContent = `${items.length} треков`;
      renderSoundCloudTracks(items);

    } catch (err) {
      if (err.name === 'AbortError') return;
      if (soundcloudStatus) soundcloudStatus.textContent = 'Ошибка';
      if (soundcloudTracksList) soundcloudTracksList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;">Ошибка соединения с SoundCloud</div>';
    }
  }

  function renderSoundCloudTracks(items) {
    if (!soundcloudTracksList) return;
    soundcloudTracksList.innerHTML = items.map(item => `
      <div class="sc-track-card">
        <div class="sc-track-art">
          ${item.thumbnail ? `<img src="${escapeHtml(item.thumbnail)}" alt="art" onerror="this.onerror=null;this.src='logo.jpg'" />` : '<span class="sc-track-art-placeholder">🎵</span>'}
        </div>
        <div class="sc-track-meta">
          <div class="sc-track-title">${escapeHtml(item.title)}</div>
          <div class="sc-track-artist">${escapeHtml(item.artist)} • ${formatTime(item.duration)}</div>
        </div>
        <div class="sc-track-actions">
          <button class="btn-sc-play" data-url="${escapeHtml(item.url)}" title="Играть сразу">
            ▶️ Играть
          </button>
          <button class="btn-sc-save" data-url="${escapeHtml(item.url)}" title="Сохранить в мою музыку">
            📥 В медиатеку
          </button>
        </div>
      </div>
    `).join('');

    soundcloudTracksList.querySelectorAll('.btn-sc-play').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const url = btn.dataset.url;
        await playSoundCloudTrack(url, btn);
      });
    });

    soundcloudTracksList.querySelectorAll('.btn-sc-save').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const url = btn.dataset.url;
        await importSoundCloudTrack(url, btn);
      });
    });
  }

  async function playSoundCloudTrack(url, btn) {
    if (!url) return;
    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ Загрузка...';

    try {
      const resp = await fetch('/api/search/soundcloud/import', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ url }),
      });
      const data = await resp.json();
      if (data.success && data.track) {
        btn.textContent = '🔊 Играет';
        player.playTrack(data.track);
        showToast(`🎶 Играет: ${data.track.artist} — ${data.track.title}`);
        if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      } else {
        btn.textContent = oldText;
        btn.disabled = false;
        showToast(data.message || 'Ошибка загрузки трека');
      }
    } catch (err) {
      btn.textContent = oldText;
      btn.disabled = false;
      showToast('Ошибка сети при загрузке трека');
    }
  }

  async function importSoundCloudTrack(url, btn) {
    if (!url) return;
    btn.disabled = true;
    btn.textContent = '⏳ Сохраняю...';

    try {
      const resp = await fetch('/api/search/soundcloud/import', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ url }),
      });
      const data = await resp.json();
      if (data.success && data.track) {
        btn.textContent = '✅ Сохранен';
        showToast(data.message || '✅ Трек добавлен в вашу медиатеку!');
        if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        if (currentTab === 'all' || currentTab === 'library') {
          await loadTabContent(searchInput ? searchInput.value.trim() : '');
        }
      } else {
        btn.disabled = false;
        btn.textContent = '📥 В медиатеку';
        showToast(data.message || 'Ошибка сохранения');
      }
    } catch (err) {
      btn.disabled = false;
      btn.textContent = '📥 В медиатеку';
      showToast('Ошибка сети при сохранении трека');
    }
  }

  // Проверка deep-link инвайта при открытии WebApp (например ?friend=12345 или ?startapp=friend_12345)
  async function checkStartParam() {
    let targetFriendId = null;

    // 1. Telegram стандартный start_param
    const startParam = tg?.initDataUnsafe?.start_param;
    if (startParam && startParam.startsWith('friend_')) {
      targetFriendId = parseInt(startParam.replace('friend_', ''), 10);
    }

    // 2. Hash параметры (Telegram Desktop и Web: #tgWebAppStartParam=friend_12345)
    if (!targetFriendId && window.location.hash) {
      try {
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        const p = hashParams.get('tgWebAppStartParam') || hashParams.get('startapp') || hashParams.get('start') || hashParams.get('friend');
        if (p) {
          const cleanP = p.replace(/^friend_/, '');
          if (/^\d+$/.test(cleanP)) targetFriendId = parseInt(cleanP, 10);
        }
      } catch (_) {}
    }

    // 3. Search query параметры (?friend=12345 или ?startapp=friend_12345)
    if (!targetFriendId && window.location.search) {
      try {
        const searchParams = new URLSearchParams(window.location.search);
        const p = searchParams.get('friend') || searchParams.get('startapp') || searchParams.get('start');
        if (p) {
          const cleanP = p.replace(/^friend_/, '');
          if (/^\d+$/.test(cleanP)) targetFriendId = parseInt(cleanP, 10);
        }
      } catch (_) {}
    }

    if (targetFriendId && targetFriendId !== currentUserId) {
      try {
        const resp = await fetch('/api/social/friends/connect', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ friend_id: targetFriendId }),
        });
        const res = await resp.json();
        if (res.success) {
          showToast(res.message || '🎉 Вы успешно подключились к другу!');
          await openSection('friends');
          if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
        } else if (res.message) {
          showToast(res.message);
        }
      } catch (err) {
        console.warn('Ошибка подключения по инвайт-ссылке:', err);
      }
    }
  }

  // Стартовая проверка deep-link и инициализация
  await checkStartParam();

  // Если не было перехода по ссылке, остаемся в круговом CS2 меню!
  if (activeView === 'wheel') {
    openWheelMenu();
    try {
      const resp = await fetch('/api/tracks?limit=20', { headers: getAuthHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        const initTracks = Array.isArray(data) ? data : (data.items || []);
        if (player.currentIndex === -1 && initTracks.length > 0) {
          player.setQueue(initTracks, 0, false);
        }
      }
    } catch (_) {}
  }
});
