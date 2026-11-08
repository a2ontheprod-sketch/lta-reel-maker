"""Self-contained original demo song + MIDI for testing without any personal files."""
from pathlib import Path
import numpy as np
import soundfile as sf
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage


def make_demo(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    wav = target / 'LTA Demo Beat.wav'
    mid = target / 'LTA Demo Notes.mid'
    if wav.is_file() and mid.is_file():
        return wav, mid
    sr = 22050
    bpm = 140
    total_bars = 8
    beat = 60/bpm
    duration = total_bars*4*beat
    n = int(duration*sr)
    rng = np.random.default_rng(173)
    y = np.zeros(n, dtype=np.float64)
    notes = [(0,60,1),(1,63,0.5),(1.5,67,0.5),(2,70,1),
             (3,67,1),(4,65,1),(5,63,1),(6,60,1),(7,58,1)]
    freqs = {p: 440*2**((p-69)/12) for p in range(20, 100)}
    midi = MidiFile(ticks_per_beat=480)
    tr = MidiTrack(); midi.tracks.append(tr)
    tr.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
    tr.append(MetaMessage('track_name', name='LTA Demo Melody', time=0))
    events=[]
    for bar in range(total_bars//2):
        for index,p,dur in notes:
            start = bar*16+index*2
            end = start+dur*2
            events.extend([(int(start*480), True, p),(int(end*480), False, p)])
            a = int(start*beat*sr); length = min(int(dur*beat*sr),n-a)
            if length <= 0: continue
            t = np.arange(length)/sr
            env = np.minimum(1,t*35)*np.exp(-t*3.5)
            x = 0.10*env*(np.sin(2*np.pi*freqs[p]*t)+.3*np.sin(2*np.pi*2*freqs[p]*t))
            y[a:a+length] += x
    for step in range(total_bars*4):
        a=int(step*beat*sr)
        length=min(int(sr*.27),n-a)
        if length <= 0: continue
        t = np.arange(length)/sr
        if step % 4 in (0, 2):
            kick = .44*np.exp(-20*t)*np.sin(2*np.pi*(55*t+45*.035*(1-np.exp(-t*45))))
            y[a:a+length] += kick
        if step % 4 == 2:
            y[a:a+length] += .17*rng.normal(size=length)*np.exp(-t*28)
        if step % 2 == 1:
            y[a:a+length] += .06*rng.normal(size=length)*np.exp(-t*70)
    events.sort(key=lambda item:(item[0],not item[1]))
    prev=0
    for tick,on,p in events:
        tr.append(Message('note_on' if on else 'note_off',note=p,velocity=100 if on else 0,
                          channel=0,time=max(0,tick-prev)))
        prev=tick
    midi.save(str(mid))
    y=np.tanh(y*1.2)*0.85
    sf.write(str(wav),y.astype(np.float32),sr,subtype='PCM_16')
    return wav,mid
