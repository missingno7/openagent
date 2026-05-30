from __future__ import annotations

import io
import math
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None

from .loader import Campaign, ensure_editor_importable

ROOT = Path(__file__).resolve().parents[1]
ensure_editor_importable(ROOT)

from secret_agent_editor.crypto import decrypt_secret_agent


# Gameplay sound IDs recovered from SAM1 call sites that push an ID and call
# the common PC-speaker routine at 0x287E.  Keep these as raw numeric IDs so
# each episode still uses its own SAM?0?E.SND records.
SOUND_JUMP = 0x01             # SAM1:0xBCE4..0xBCED starts DS:6EC1 jump phase.
SOUND_PLAYER_SHOT_SPAWN = 0x02  # SAM1:0x02B0/0x0B92 spawns/continues player shot slot.
SOUND_FIRE = 0x02             # Player fire/no-ammo branch uses 0x02 when a shot is actually spawned.
SOUND_ENEMY_PROJECTILE = 0x03 # SAM1:0x57A7 projectile helper path when actor sound flag is set.
SOUND_HURT = 0x07             # SAM1:0x5451 generic non-lethal player damage helper.
SOUND_FALLING_BAG_DROP = 0x09 # SAM1:0xB173 for raw 0x5B falling money bag.
SOUND_EXIT_DYNAMITE = 0x0B    # SAM1:0xCBFA..0xCC03 after using dynamite on exit door visual 0x027D.
SOUND_MENU_OR_LEVEL_START = 0x15  # SAM1:0x1B440 startup/title/level-load style chime.
SOUND_NO_AMMO = 0x14          # SAM1:0x016F..0x017A denied fire when ammo is zero.
SOUND_PLAYER_DEATH = 0x16     # SAM1:0x1A93 and hard-death branches set DS:69F5/69F6.
SOUND_TELEPORT = 0x17         # SAM1:0xD4DE teleporter dispatcher.
SOUND_SCORE_1000 = 0x04
SOUND_PICKUP = 0x05
SOUND_ENEMY_DEATH = 0x13

RECORD_SIZE = 610
MAX_FREQUENCIES = 300


@dataclass(frozen=True)
class PcSpeakerSound:
    data: tuple[int, ...]
    priority: int
    unknown0: int
    vibrate: int
    unknown1: int
    unknown2: int


def decode_snd_file(path: Path) -> list[PcSpeakerSound]:
    """Decode one Secret Agent SND file.

    Secret Agent keeps the Crystal Caves 610-byte PC-speaker records, but the
    whole file is encrypted with the same bit-reverse/XOR stream used by other
    assets.
    """
    raw = path.read_bytes()
    if len(raw) % RECORD_SIZE:
        raise ValueError(f"{path} has {len(raw)} bytes, not a multiple of {RECORD_SIZE}")
    decoded = bytes(decrypt_secret_agent(raw, row_key_reset=None))
    sounds: list[PcSpeakerSound] = []
    for offset in range(0, len(decoded), RECORD_SIZE):
        record = decoded[offset : offset + RECORD_SIZE]
        values = struct.unpack("<300h5H", record)
        sounds.append(PcSpeakerSound(tuple(values[:MAX_FREQUENCIES]), *values[MAX_FREQUENCIES:]))
    return sounds


def decode_episode_sounds(paths: list[Path]) -> list[PcSpeakerSound]:
    sounds: list[PcSpeakerSound] = []
    for path in paths:
        sounds.extend(decode_snd_file(path))
    return sounds


def synthesize_sound(sound: PcSpeakerSound, *, sample_rate: int = 44100) -> bytes:
    """Synthesize unsigned 8-bit PCM using the OpenCrystalCaves timing model."""
    freq_len = max(1, int(320 * sample_rate / 44100))
    src_len = 0
    for value in sound.data:
        if value == -1:
            break
        src_len += 1

    pcm = bytearray(src_len * freq_len)
    vibrate = max(1, sound.vibrate)
    phase = 0.0
    out_index = 0
    for i, freq in enumerate(sound.data[:src_len]):
        if freq <= 0 or i % vibrate != 0:
            pcm[out_index : out_index + freq_len] = b"\x80" * freq_len
            out_index += freq_len
            continue
        # The decoded Secret Agent/Crystal Caves SND words are already the
        # pitch values consumed by the 610-byte PC-speaker record player.
        # Pass 56 incorrectly treated them as raw PIT divisors; that inverted
        # effects such as jump.  Keep the OpenCrystalCaves model: use the word
        # as the square-wave frequency-like value.
        tone_hz = float(freq)
        phase_step = 2.0 * math.pi * tone_hz / sample_rate
        for _ in range(freq_len):
            pcm[out_index] = 160 if math.sin(phase) >= 0 else 96
            out_index += 1
            phase += phase_step
            if phase >= 2.0 * math.pi:
                phase -= 2.0 * math.pi
    return bytes(pcm)


def make_wav(sound: PcSpeakerSound, *, sample_rate: int = 44100) -> bytes:
    pcm = synthesize_sound(sound, sample_rate=sample_rate)
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return out.getvalue()


class SoundPlayer:
    def __init__(self) -> None:
        self.enabled = winsound is not None
        self.sounds: list[PcSpeakerSound] = []
        self._tempdir: tempfile.TemporaryDirectory[str] | None = None
        self._wav_paths: list[Path] = []

    @classmethod
    def from_campaign(cls, campaign: Campaign, episode: int) -> "SoundPlayer":
        player = cls()
        player.load_episode(campaign, episode)
        return player

    def load_episode(self, campaign: Campaign, episode: int) -> None:
        self._clear_files()
        assets = campaign.assets.get(episode)
        if assets is None or not assets.sounds:
            self.sounds = []
            return
        self.sounds = decode_episode_sounds(assets.sounds)
        self._tempdir = tempfile.TemporaryDirectory(prefix=f"openagent_ep{episode}_sounds_")
        root = Path(self._tempdir.name)
        self._wav_paths = []
        for index, sound in enumerate(self.sounds):
            path = root / f"{index:02d}.wav"
            path.write_bytes(make_wav(sound))
            self._wav_paths.append(path)

    def play(self, sound_id: int) -> None:
        # The EXE pushes sound ids in the range 1..29 before calling the common
        # PC-speaker routine.  The SND files are decoded into a zero-based Python
        # list, so raw id 1 must play record 0.  Earlier passes used the raw id as
        # the list index, which shifted gameplay sounds such as jump by one slot.
        index = sound_id - 1
        if not self.enabled or index < 0 or index >= len(self._wav_paths):
            return
        try:
            winsound.PlaySound(
                str(self._wav_paths[index]),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
        except RuntimeError:
            pass

    def close(self) -> None:
        if winsound is not None:
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError:
                pass
        self._clear_files()

    def _clear_files(self) -> None:
        self._wav_paths = []
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None
