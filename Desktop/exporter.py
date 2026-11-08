"""Deterministic MP4 exporter. Renders same Pillow scene as the UI preview.
Audio from original file is muxed separately, with no clicks or UI sounds.
"""
from pathlib import Path
import subprocess
import threading
import time
from core import ffmpeg_bin
from visualisers import draw_scene


class CancelExport(Exception):
    pass


def export_reel(audio, preset, output, start=0.0, length=15.0, resolution='1080x1920', fps=30,
                midi=None, screen=None, title='LISTENTOAARXN', on_progress=None, cancel=None):
    if not audio:
        raise ValueError('Load a beat before exporting')
    if preset.needs_midi and (midi is None or not midi.notes):
        raise ValueError('This visualiser needs MIDI. Import a .mid file first.')
    w, h = (int(x) for x in resolution.lower().split('x'))
    if min(w, h) < 120 or max(w,h)>4096:
        raise ValueError('Invalid output resolution')
    start=max(0.0,float(start))
    length=min(float(length),max(0.0,audio.duration-start))
    if length<0.15:
        raise ValueError('Not enough audio left for a clip')
    count=max(1,round(length*fps))
    output = str(Path(output).resolve())
    cmd=[ffmpeg_bin(),'-hide_banner','-loglevel','error','-y',
         '-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}',
         '-framerate',str(fps),'-i','pipe:0',
         '-ss',f'{start:.6f}','-t',f'{length:.6f}','-i',audio.source,
         '-map','0:v:0','-map','1:a:0',
         '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
         '-c:a','aac','-b:a','192k','-ar','44100',
         '-t',f'{length:.6f}', '-movflags','+faststart',output]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for i in range(count):
            if cancel is not None and cancel.is_set():
                raise CancelExport('Cancelled')
            t=start+i/fps
            image=draw_scene(preset,audio,t,(w,h),midi=midi,screen=screen,title=title)
            proc.stdin.write(image.tobytes())
            if on_progress and (i%max(1,fps//2)==0 or i==count-1):
                on_progress((i+1)/count)
        proc.stdin.close()
        proc.stdin = None
        stderr=proc.communicate()[1].decode('utf-8','replace')
        if proc.returncode!=0:
            raise RuntimeError('FFmpeg export failed: '+stderr[-1300:])
        if not Path(output).is_file() or Path(output).stat().st_size<1000:
            raise RuntimeError('Output MP4 missing or empty')
        if on_progress: on_progress(1.0)
        return output
    except BaseException:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        try: Path(output).unlink(missing_ok=True)
        except Exception: pass
        raise
