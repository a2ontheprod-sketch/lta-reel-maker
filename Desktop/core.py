"""Pure audio, MIDI and export logic for LTA Reel Maker.
No FL Studio metadata or exact notes are inferred from the master mix.
"""
from __future__ import annotations
import os
import sys
import tempfile
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import mido
from imageio_ffmpeg import get_ffmpeg_exe

def documents_folder():
    if sys.platform == 'win32':
        try:
            import ctypes
            buffer = ctypes.create_unicode_buffer(32768)
            # CSIDL_PERSONAL = actual Windows Documents location, incl. OneDrive redirects
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
                return Path(buffer.value)
        except Exception:
            pass
    return Path.home() / 'Documents'

APP_HOME = documents_folder() / 'LTA Reel Maker'
CAPTURE_DIR = APP_HOME / 'Captures'
EXPORT_DIR = APP_HOME / 'Exports'
for folder in (CAPTURE_DIR, EXPORT_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def ffmpeg_bin() -> str:
    return get_ffmpeg_exe()


def run_ffmpeg(args, **kwargs):
    cmd = [ffmpeg_bin(), '-hide_banner', '-loglevel', 'error', '-y'] + list(args)
    return subprocess.run(cmd, check=True, **kwargs)


@dataclass
class MidiNote:
    pitch: int
    start: float
    end: float
    velocity: int
    channel: int
    track: str


class MidiData:
    def __init__(self, notes=None, bpm=140.0):
        self.notes = sorted(notes or [], key=lambda n: n.start)
        self.bpm = bpm

    def active(self, t: float, duration=0.1, max_notes=80):
        # binary search to avoid scanning all notes on every frame
        import bisect
        if not hasattr(self, '_times') or len(self._times) != len(self.notes):
            self._times = [n.start for n in self.notes]
        end = bisect.bisect_right(self._times, t + duration)
        return [n for n in self.notes[:end] if n.end >= t - duration][-max_notes:]

    def in_window(self, a: float, b: float, max_notes=300):
        import bisect
        if not hasattr(self, '_times') or len(self._times) != len(self.notes):
            self._times = [n.start for n in self.notes]
        end = bisect.bisect_right(self._times, b)
        return [n for n in self.notes[:end] if n.end >= a][-max_notes:]


def parse_midi(path: str | Path) -> MidiData:
    midi = mido.MidiFile(str(path))
    events = []
    for track_idx, track in enumerate(midi.tracks):
        tick = 0
        label = f'Track {track_idx+1}'
        for msg in track:
            tick += msg.time
            if msg.type == 'track_name' and msg.name:
                label = msg.name
            if msg.type in ('note_on', 'note_off', 'set_tempo'):
                events.append((tick, track_idx, label, msg))
    events.sort(key=lambda x: (x[0], 0 if x[3].type == 'set_tempo' else 1))
    tempo = 500000
    prev_tick = 0
    now = 0.0
    stacks = {}
    notes = []
    initial_tempo = None
    for tick, track_idx, label, msg in events:
        now += mido.tick2second(tick - prev_tick, midi.ticks_per_beat, tempo)
        prev_tick = tick
        if msg.type == 'set_tempo':
            tempo = msg.tempo
            if initial_tempo is None:
                initial_tempo = tempo
            continue
        key = (track_idx, msg.channel, msg.note)
        if msg.type == 'note_on' and msg.velocity > 0:
            stacks.setdefault(key, []).append((now, msg.velocity, label))
        else:
            if stacks.get(key):
                start, velocity, track_name = stacks[key].pop(0)
                notes.append(MidiNote(msg.note, start, max(now, start+0.025), velocity, msg.channel, track_name))
    for (track_idx, channel, pitch), stack in stacks.items():
        for start, velocity, label in stack:
            notes.append(MidiNote(pitch, start, start+0.2, velocity, channel, label))
    bpm = 60000000.0 / (initial_tempo or 500000)
    return MidiData(notes, bpm)


@dataclass
class AudioData:
    source: str
    audio_file: str
    duration: float
    rate: int
    rms: np.ndarray
    bass: np.ndarray
    mids: np.ndarray
    treble: np.ndarray
    attack: np.ndarray
    fps: float

    def at(self, t: float):
        i = max(0.0, min((len(self.rms)-1.001), t * self.fps))
        k = int(i)
        a = i-k
        return tuple(float(x[k]*(1-a) + x[k+1]*a) for x in (self.rms, self.bass, self.mids, self.treble, self.attack))


def load_audio(path: str | Path, cache_dir: Optional[Path]=None) -> AudioData:
    """Decode formats through FFmpeg to 22.05kHz mono WAV; analyse amplitude and bands."""
    source = str(path)
    if not Path(source).is_file():
        raise FileNotFoundError(source)
    cache_dir = cache_dir or (APP_HOME / 'Cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    src = Path(source)
    cache_key = hashlib.sha1(f'{src.resolve()}|{src.stat().st_mtime_ns}|{src.stat().st_size}'.encode()).hexdigest()[:16]
    decoded = cache_dir / f'{cache_key}.wav'
    if not decoded.is_file():
        run_ffmpeg(['-i', source, '-vn', '-ac', '1', '-ar', '22050', '-acodec', 'pcm_s16le', str(decoded)])
    samples, rate = sf.read(str(decoded), dtype='float32', always_2d=False)
    if samples.ndim > 1:
        samples = np.mean(samples, axis=1)
    if samples.size < 32:
        raise ValueError('Audio is too short')
    hop = 882  # 25 analysis samples per second
    fft_n = 2048
    length = int(np.ceil(len(samples)/hop))+1
    bins = np.fft.rfftfreq(fft_n, 1/rate)
    low_mask = (bins >= 25) & (bins < 180)
    mid_mask = (bins >= 180) & (bins < 2000)
    high_mask = (bins >= 2000) & (bins <= 10000)
    rms = np.zeros(length, np.float32)
    low = np.zeros(length, np.float32)
    mid = np.zeros(length, np.float32)
    high = np.zeros(length, np.float32)
    flux = np.zeros(length, np.float32)
    prior = np.zeros(len(bins), np.float32)
    win = np.hanning(fft_n)
    for k in range(length):
        start = k*hop
        part = samples[start:start+fft_n]
        if len(part) < fft_n:
            part = np.pad(part, (0, fft_n-len(part)))
        rms[k] = np.sqrt(np.mean(part*part))
        mag = abs(np.fft.rfft(part*win))
        low[k] = np.sqrt(np.sum(mag[low_mask]**2))
        mid[k] = np.sqrt(np.sum(mag[mid_mask]**2))
        high[k] = np.sqrt(np.sum(mag[high_mask]**2))
        flux[k] = np.maximum(0, mag-prior).sum()
        prior = mag
    def normalise(x, multiplier=1.0):
        scale = max(np.percentile(x, 95), 1e-7)
        return np.clip(x / scale * multiplier, 0.0, 1.0).astype(np.float32)
    return AudioData(source, str(decoded), len(samples)/rate, rate,
                     normalise(rms), normalise(low), normalise(mid), normalise(high),
                     normalise(flux, 0.85), float(rate/hop))


def make_preview_wav(audio: AudioData, start=0.0, duration=15.0) -> str:
    """WAV extracted for Windows built-in async playback, not rendered into the audio master."""
    path = APP_HOME / 'Cache' / 'preview_playback.wav'
    run_ffmpeg(['-ss', f'{max(start,0):.3f}', '-t', f'{duration:.3f}', '-i', audio.source,
                '-vn', '-ac', '2', '-ar', '44100', '-acodec', 'pcm_s16le', str(path)])
    return str(path)


def capture_screen_start(path: str | Path, fps=15):
    if sys.platform != 'win32':
        raise RuntimeError('Desktop capture currently supported on Windows only')
    out = str(path)
    cmd = [ffmpeg_bin(), '-hide_banner', '-loglevel', 'warning', '-y',
           '-f', 'gdigrab', '-framerate', str(fps), '-draw_mouse', '1', '-i', 'desktop',
           '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', '-pix_fmt', 'yuv420p', out]
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=flags)


def capture_screen_stop(proc):
    if proc and proc.poll() is None:
        try:
            proc.stdin.write(b'q\n')
            proc.stdin.flush()
            proc.wait(timeout=6)
        except Exception:
            proc.terminate()
            try: proc.wait(timeout=2)
            except Exception: proc.kill()


def frame_from_video(path: str | Path, second=0.2):
    """Extract an actual frame from a user-recorded screen video for arrangement styling."""
    output = APP_HOME / 'Cache' / 'screen_frame.png'
    run_ffmpeg(['-ss', str(second), '-i', str(path), '-frames:v', '1', str(output)])
    return output

class ScreenSequence:
    """Cached video frames for moving background in Arrangement Scan visualiser.

    Frames are extracted at 12fps and limited to the first 60 seconds.
    The user should synchronise the screen recording with the Master capture manually.
    """
    def __init__(self, video_path):
        import hashlib
        self.video_path = str(video_path)
        s = Path(video_path)
        cache_hash = hashlib.sha1(f'{s.resolve()}|{s.stat().st_mtime_ns}'.encode()).hexdigest()[:16]
        self.folder = APP_HOME / 'Cache' / ('screen_'+cache_hash)
        self.folder.mkdir(parents=True, exist_ok=True)
        existing = sorted(self.folder.glob('frame_*.jpg'))
        if not existing:
            run_ffmpeg(['-i',self.video_path,'-t','60','-vf','fps=12,scale=960:-1',
                        '-q:v','4',str(self.folder/'frame_%05d.jpg')])
            existing=sorted(self.folder.glob('frame_*.jpg'))
        if not existing:
            raise ValueError('Could not read screen recording frames')
        self.frames=existing

    def frame_at(self,t):
        from PIL import Image
        from functools import lru_cache
        return self._frame(int(max(0,t)*12)).copy()

    @__import__('functools').lru_cache(maxsize=9)
    def _frame(self,idx):
        from PIL import Image
        return Image.open(self.frames[min(idx,len(self.frames)-1)]).convert('RGB')
