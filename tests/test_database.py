import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Track, UserTrack, Playlist, PlaylistTrack, ListeningHistory


@pytest.mark.asyncio
async def test_user_creation(test_session: AsyncSession) -> None:
    """Проверка создания пользователя и сохранения в БД."""
    user = User(
        id=123456789,
        username="music_fan",
        first_name="Alex",
        last_name="Smith",
        is_admin=False,
    )
    test_session.add(user)
    await test_session.commit()

    result = await test_session.execute(select(User).where(User.id == 123456789))
    fetched_user = result.scalar_one_or_none()

    assert fetched_user is not None
    assert fetched_user.username == "music_fan"
    assert fetched_user.first_name == "Alex"
    assert fetched_user.created_at is not None


@pytest.mark.asyncio
async def test_track_and_user_library(test_session: AsyncSession) -> None:
    """Проверка создания трека и добавления в библиотеку пользователя."""
    user = User(id=111, first_name="John")
    test_session.add(user)
    await test_session.commit()

    track = Track(
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        title="Midnight City",
        artist="M83",
        album="Hurry Up, We're Dreaming",
        duration=244,
        bit_rate=320,
        file_size=9800000,
        file_path="media/audio/sample.mp3",
        uploader_id=user.id,
    )
    test_session.add(track)
    await test_session.commit()

    assert track.id is not None

    # Добавление в персональную библиотеку и избранное
    user_track = UserTrack(
        user_id=user.id,
        track_id=track.id,
        is_favorite=True,
    )
    test_session.add(user_track)
    await test_session.commit()

    query = select(UserTrack).where(
        UserTrack.user_id == user.id, UserTrack.track_id == track.id
    )
    res = await test_session.execute(query)
    link = res.scalar_one_or_none()

    assert link is not None
    assert link.is_favorite is True


@pytest.mark.asyncio
async def test_duplicate_file_hash_constraint(test_session: AsyncSession) -> None:
    """Проверка, что одинаковый SHA-256 хеш файла отклоняется базой (защита от дубликатов)."""
    track1 = Track(
        file_hash="same_hash_123",
        title="Track 1",
        artist="Artist 1",
        duration=180,
        file_size=5000,
        file_path="media/audio/t1.mp3",
    )
    test_session.add(track1)
    await test_session.commit()

    track2 = Track(
        file_hash="same_hash_123",  # дубликат
        title="Track 2",
        artist="Artist 2",
        duration=190,
        file_size=5000,
        file_path="media/audio/t2.mp3",
    )
    test_session.add(track2)
    with pytest.raises(IntegrityError):
        await test_session.commit()


@pytest.mark.asyncio
async def test_playlist_and_tracks(test_session: AsyncSession) -> None:
    """Проверка создания плейлиста и добавления в него упорядоченных треков."""
    user = User(id=222, first_name="DJ")
    test_session.add(user)
    await test_session.commit()

    playlist = Playlist(
        user_id=user.id,
        title="Workout Mix",
        description="High energy tracks",
        is_public=True,
    )
    test_session.add(playlist)
    await test_session.commit()

    track = Track(
        file_hash="hash_workout_1",
        title="Stronger",
        artist="Kanye West",
        duration=312,
        file_size=8000000,
        file_path="media/audio/stronger.mp3",
    )
    test_session.add(track)
    await test_session.commit()

    pl_track = PlaylistTrack(
        playlist_id=playlist.id,
        track_id=track.id,
        position=1,
    )
    test_session.add(pl_track)
    await test_session.commit()

    res = await test_session.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id)
    )
    found_items = res.scalars().all()
    assert len(found_items) == 1
    assert found_items[0].position == 1
