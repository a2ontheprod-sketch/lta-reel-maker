"""300 selectable looks built from 25 distinct drawing/animation engines x 12 art directions.
Audio drives amplitude/energy/onsets. Note-based engines require real imported MIDI.
All images generated locally without external assets or online services.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ENGINES = [
    ('Piano Roll', 'Notes', True), ('Float Notes', 'Notes', True),
    ('Bass Glide', 'Notes', True), ('Step Matrix', 'Notes', True),
    ('Chord Flow', 'Notes', True), ('Falling Notes', 'Notes', True),
    ('Note Orbit', 'Notes', True), ('Split Lanes', 'Notes', True),
    ('Neon Staff', 'Notes', True), ('Note Barcode', 'Notes', True),
    ('Wave Ribbon', 'Audio', False), ('Orbit Spectrum', 'Audio', False),
    ('Spectrum Bars', 'Audio', False), ('Crystal Pulse', 'Audio', False),
    ('Harmonic Layers', 'Audio', False), ('Ripple Pool', 'Audio', False),
    ('Particle Bloom', 'Audio', False), ('Lissajous', 'Audio', False),
    ('Drum Matrix', 'Drums', False), ('Impact Frames', 'Drums', False),
    ('Depth Tunnel', '3D', False), ('Star Trails', '3D', False),
    ('Tape Machines', 'Retro', False), ('Editorial', 'Typography', False),
    ('Arrangement Scan', 'Arrangement', False),
]
ART_DIRECTIONS = [
    ('Candy', '#0e0b14', '#fa6da8', '#bcb0fa', '#fff3ff'),
    ('Midnight', '#080b12', '#f5f5f8', '#8a9bbd', '#fffaff'),
    ('Ice', '#0b1b25', '#79f1ff', '#4f9ff6', '#edfbff'),
    ('Peach', '#1c131c', '#ffa390', '#e8b4f7', '#fff3e7'),
    ('Forest', '#091c1b', '#7be4b8', '#8adddf', '#ebfff5'),
    ('Ember', '#1a0d0d', '#ff655c', '#ffb17f', '#fff0e7'),
    ('Lilac', '#171124', '#c69cff', '#fa9fdc', '#f8e9ff'),
    ('Chrome', '#101014', '#dce3ef', '#9ea1b7', '#ffffff'),
    ('Cobalt', '#071026', '#647aff', '#a4cbff', '#eef1ff'),
    ('Rose', '#220e18', '#ff94bd', '#f9d2db', '#fff3f8'),
    ('Dusk', '#150f26', '#d18cff', '#ffa97c', '#fff1ec'),
    ('Mono', '#0b0b0b', '#eeeeee', '#8e8e8e', '#ffffff'),
]


def rgb(col): return tuple(int(col[i:i+2],16) for i in (1,3,5))
def mix(a,b,q): return tuple(int(a[k]*(1-q)+b[k]*q) for k in range(3))
def clamp(v,low=0,high=1): return max(low,min(high,v))

@dataclass(frozen=True)
class Preset:
    index: int
    engine: int
    art: int
    name: str
    family: str
    needs_midi: bool

PRESETS = [Preset(i*12+j, i, j, f'{ART_DIRECTIONS[j][0]} {ENGINES[i][0]}', ENGINES[i][1], ENGINES[i][2])
           for i in range(len(ENGINES)) for j in range(len(ART_DIRECTIONS))]
assert len(PRESETS) == 300


@lru_cache(maxsize=36)
def font(size,bold=False):
    import os
    candidates = (['C:/Windows/Fonts/segoeuib.ttf','C:/Windows/Fonts/arialbd.ttf'] if bold else
                  ['C:/Windows/Fonts/segoeui.ttf','C:/Windows/Fonts/arial.ttf'])
    candidates += ['/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf']
    for fn in candidates:
        if os.path.isfile(fn):
            return ImageFont.truetype(fn,size)
    return ImageFont.load_default()


@lru_cache(maxsize=48)
def base_canvas(w,h,art):
    bg=rgb(ART_DIRECTIONS[art][1]); accent=rgb(ART_DIRECTIONS[art][2])
    im=Image.new('RGB',(w,h)); d=ImageDraw.Draw(im)
    for y in range(h):
        q=y/max(1,h-1)
        d.line((0,y,w,y),fill=mix(bg,mix(bg,accent,.20),q*.58))
    # restrained ambient grid
    grid=mix(bg,accent,.12)
    for x in range(0,w,max(25,w//9)):
        d.line((x,h*.12,x,h*.85),fill=grid,width=max(1,w//650))
    return im


def line(d, pts, col, width=2, joint='curve'):
    if len(pts)>1: d.line(pts,fill=col,width=max(1,int(width)),joint=joint)

def label(d,xy,text,col,sz,bold=False,anchor=None):
    d.text(xy,str(text),fill=col,font=font(max(8,int(sz)),bold),anchor=anchor)

def spectrum(audio,t):
    return audio.at(t) if audio else (0.22,0.18,0.12,0.13,0.0)

def _notes(midi,t,span=3.2):
    return midi.in_window(max(0,t-span),t+span,max_notes=170) if midi else []

def _note_y(p, h):
    return h*(.71 - clamp((p-36)/60)*.47)

def _circle(d,x,y,r,col,width=0):
    if r>0: d.ellipse((x-r,y-r,x+r,y+r),outline=col if width else None,fill=None if width else col,width=max(1,int(width)))

def _draw_notes(d,w,h,t,midi,kind,primary,secondary,muted,energy,style):
    notes=_notes(midi,t)
    speed = w/(2.8+style*.08)
    cx=w*.50
    for x in range(0,w,max(25,w//8)):
        d.line((x,h*.24,x,h*.76),fill=muted,width=1)
    d.line((cx,h*.19,cx,h*.78),fill=secondary,width=max(2,w//190))
    if kind in (0,1,7,8,9):
        if kind==8:
            for j in range(5): d.line((w*.08,h*(.36+j*.055),w*.92,h*(.36+j*.055)),fill=muted,width=1)
        for n in notes:
            x=cx+(n.start-t)*speed
            x2=cx+(n.end-t)*speed
            if x2<0 or x>w: continue
            y=_note_y(n.pitch,h)
            if kind==1:
                y+=math.sin(n.pitch*.3+t*1.5)*h*.014
            if kind==7:
                y=(h*.38 if n.pitch>=60 else h*.67)+(n.pitch%12-6)*h*.009
            if kind==8:
                y=h*(.36+(74-n.pitch)*.018)
            if kind==9:
                y=h*.28+(n.pitch%12)*h*.036
            color=primary if n.start <= t <= n.end else secondary
            if kind==9:
                d.line((x,h*.25,x,h*.76),fill=color,width=max(2,int(w*.009)))
            else:
                margin=w*.008
                d.rounded_rectangle((max(0,x),y-h*.009,max(x+3,x2),y+h*.009+max(1,w//140)),radius=max(2,w//100),fill=color)
                if n.start<=t<=n.end: _circle(d, cx,y,w*.013,secondary)
    elif kind==2:  # 808 pitch glides, approximate straight lines from imported MIDI notes
        bass=[n for n in notes if n.pitch<65]
        for a,b in zip(bass,bass[1:]):
            x=cx+(a.start-t)*speed; x2=cx+(b.start-t)*speed
            y=_note_y(a.pitch,h); y2=_note_y(b.pitch,h)
            line(d,[(x,y),(x2,y2)],primary,max(3,w//135))
        for n in bass:
            x=cx+(n.start-t)*speed; y=_note_y(n.pitch,h)
            _circle(d,x,y,w*.013,secondary)
            if n.start<=t<=n.end: _circle(d,cx,y,w*.024,primary,3)
    elif kind==3:  # step matrix
        rows=9; cols=12; x0=w*.08; y0=h*.28; dw=w*.84/cols; dh=h*.44/rows
        for r in range(rows):
            for c in range(cols):
                px=x0+c*dw; py=y0+r*dh
                note_time=t+(c-6)*.20
                active=any(abs(n.start-note_time)<.095 and (n.pitch%rows)==r for n in notes)
                d.rounded_rectangle((px+dw*.12,py+dh*.1,px+dw*.86,py+dh*.80),radius=2,
                                    fill=primary if active else muted)
        d.line((x0+6*dw,y0,x0+6*dw,y0+rows*dh),fill=secondary,width=2)
    elif kind==4:  # chord rails
        keynotes=sorted({n.pitch for n in notes})[:15]
        for p in keynotes:
            y=_note_y(p,h)
            for n in notes:
                if n.pitch==p:
                    x=cx+(n.start-t)*speed
                    x2=cx+(n.end-t)*speed
                    d.line((max(0,x),y,min(w,x2),y),fill=primary,width=max(2,w//150))
                    if abs(x-cx)<w*.04: _circle(d,cx,y,w*.014,secondary)
            label(d,(w*.055,y),midi_note_name(p),secondary,w*.035)
    elif kind==5:  # falling notes
        for n in notes:
            x=w*(.09+(n.pitch%24)/26)
            y=h*.66+(n.start-t)*h*.22
            height=max(h*.014,(n.end-n.start)*h*.15)
            if 0<y<h:
                d.rounded_rectangle((x,y-height,x+w*.022,y),radius=3,fill=primary if abs(n.start-t)<.2 else secondary)
        d.line((w*.08,h*.66,w*.92,h*.66),fill=primary,width=3)
    elif kind==6:  # orbit notes
        for n in notes:
            age=t-n.start
            if -1 < age < 2.5:
                angle=n.pitch*.56+age*1.7
                r=w*(.12+(n.pitch%16)*.013)
                x=w*.5+math.cos(angle)*r; y=h*.49+math.sin(angle)*r
                _circle(d,x,y,w*.014*(1+n.velocity/127),primary)
                d.line((w*.5,h*.49,x,y),fill=muted,width=1)
        _circle(d,w*.5,h*.49,w*.032,secondary)
    # Note mode never invents values when only audio present
    if not midi or not midi.notes:
        d.rectangle((w*.05,h*.36,w*.95,h*.64),fill=mix(rgb(ART_DIRECTIONS[style][1]),(0,0,0),.2))
        label(d,(w*.5,h*.47),'IMPORT MIDI',secondary,w*.057,True,'mm')
        label(d,(w*.5,h*.53),'for exact notes',secondary,w*.033,False,'mm')


def midi_note_name(p):
    return ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][p%12]+str(p//12-1)


def draw_scene(preset: Preset, audio, t: float, size=(360,640), midi=None, screen=None, title='LISTENTOAARXN'):
    """Deterministic per-frame image generator. Same logic used for preview + export."""
    w,h=size
    art=preset.art
    bg=rgb(ART_DIRECTIONS[art][1]); a=rgb(ART_DIRECTIONS[art][2]); b=rgb(ART_DIRECTIONS[art][3]); white=rgb(ART_DIRECTIONS[art][4])
    muted=mix(bg,b,.19)
    im=base_canvas(w,h,art).copy()
    d=ImageDraw.Draw(im)
    rms,bass,mids,treble,attack=spectrum(audio,t)
    e=preset.engine
    phase=t*(1+art*.018)
    if e<10:
        _draw_notes(d,w,h,t,midi,e,a,b,muted,rms,art)
    elif e==10:  # wave ribbon - smooth, parallel frequency lanes
        for k in range(4):
            pts=[]
            for x in range(0,w+4,4):
                tt=max(0,t+(x/w-.5)*2)
                rr,lo,mi,hi,at=spectrum(audio,tt)
                val=(lo,mi,hi,rr)[k]
                y=h*(.35+k*.095)+math.sin(x/w*16+phase*2+k*.8)*val*h*.09
                pts.append((x,y))
            line(d,pts,a if k%2==0 else b,max(2,w//150))
    elif e==11:  # orbit spectrum
        for j in range(5):
            val=(rms,bass,mids,treble,attack)[j]
            r=w*(.11+j*.065+val*.035)
            _circle(d,w*.5,h*.48,r,a if j%2==0 else b,max(1,w//210))
        for j in range(22):
            q=j/22*math.tau+phase*.32
            r=w*(.29+math.sin(j+phase)*.03)
            _circle(d,w*.5+math.cos(q)*r,h*.48+math.sin(q)*r,2+bass*3,b)
    elif e==12:  # spectrum columns
        for j in range(28):
            mixval=(bass,mids,treble)[min(2,j//10)]
            amp=clamp(mixval*(.55+.45*abs(math.sin(j*.8+t*9))))
            bar=h*.46*amp
            x=w*(.07+j*.86/28)
            d.rounded_rectangle((x,h*.69-bar,x+w*.020,h*.69),radius=max(2,w//230),fill=a if j%3 else b)
    elif e==13: # crystal pulse
        r=w*(.09+rms*.16)
        points=[]
        for j in range(8):
            q=j/8*math.tau+phase*.3
            rr=r*(.87+.17*math.sin(j*3+phase*2))
            points.append((w*.5+math.cos(q)*rr,h*.48+math.sin(q)*rr))
        d.polygon(points,fill=mix(bg,a,.23))
        line(d,points+[points[0]],a,max(2,w//130))
        for j in range(8): line(d,[points[j],(w*.5,h*.48)],b,1)
        _circle(d,w*.5,h*.48,w*.025+attack*w*.02,b)
    elif e==14:  # harmonic layers
        for k in range(11):
            pts=[]
            for x in range(0,w+7,7):
                q=x/w
                amp=(bass*.2+mids*.5+treble*.3)*h*.18
                y=h*(.23+k*.049)+math.sin(q*math.tau*(1.5+k*.18)+phase*(.7+k*.09))*amp*(.25+k*.05)
                pts.append((x,y))
            line(d,pts,a if k%2 else b,max(1,w//230))
    elif e==15: # ripple pool
        for k in range(12):
            r=(phase*50+k*w*.045) % (w*.48)
            alpha_factor=1-r/(w*.49)
            col=mix(bg,a,alpha_factor*.95)
            d.ellipse((w*.5-r,h*.55-r*.46,w*.5+r,h*.55+r*.46),outline=col,width=max(2,w//200))
        _circle(d,w*.5,h*.55,3+bass*w*.05,b)
    elif e==16: # particle bloom
        for k in range(125):
            ang=k*2.39996+phase*.19
            reach=math.sqrt(k/125)*(w*.34)*(1+attack*.4)
            x=w*.5+math.cos(ang)*reach; y=h*.47+math.sin(ang)*reach
            radius=max(1,int((1+(k%5)*.55)*w/360))
            _circle(d,x,y,radius,a if k%3 else b)
    elif e==17: # Lissajous
        pts=[]
        for j in range(400):
            u=j/399*math.tau
            pts.append((w*.5+math.sin(u*3+phase*.43)*w*(.15+treble*.12),
                        h*.49+math.sin(u*4+phase*.28)*h*(.12+bass*.06)))
        line(d,pts,a,max(2,w//180))
        _circle(d,w*.5,h*.49,w*.022,b)
    elif e==18: # drum matrix waveform onset-derived, not individual drum labels
        count=12; rows=7
        for row in range(rows):
            for col in range(count):
                sampletime=max(0,t+(col-count//2)*.16)
                r,lo,mi,hi,on=spectrum(audio,sampletime)
                v=(lo,mi,hi,lo*.5+on*.5,r,on,hi*.6+on*.4)[row]
                x=w*(.085+col*.835/count); y=h*(.28+row*.067)
                colr=a if v>.3 and v*(.7+math.sin(row+col)*.15)>.34 else muted
                d.rounded_rectangle((x,y,x+w*.055,y+h*.039),radius=max(2,w//135),fill=colr)
        d.line((w*.5,h*.25,w*.5,h*.78),fill=b,width=2)
    elif e==19: # impact rectangles
        for j in range(12):
            val=(bass,attack,mids,treble)[j%4]
            x=w*(.1+(j%4)*.21); y=h*(.25+(j//4)*.18)
            radius=w*(.027+val*.028)
            d.rounded_rectangle((x-radius*2,y-radius,x+radius*2,y+radius),
                                radius=max(3,w//70),fill=a if j%2 else b)
        if attack>.45:
            d.rectangle((0,h*.48-attack*h*.01,w,h*.48+attack*h*.01),fill=a)
    elif e==20: # depth tunnel
        for j in range(13):
            z=((j/13+phase*.07)%1)
            sizev=w*(.03+z*z*.7)*(1+bass*.2)
            col=mix(bg,a,z*.9)
            x=w*.5+math.sin(j*.9+phase*.16)*w*.018
            y=h*.48
            d.rectangle((x-sizev/2,y-sizev*.65,x+sizev/2,y+sizev*.65),outline=col,width=max(1,w//200))
    elif e==21: # star trails
        for j in range(85):
            ang=j*2.4
            depth=(j*.618+phase*.2)%1
            r=math.sqrt(depth)*w*.42*(1+rms*.2)
            x=w*.5+math.cos(ang)*r; y=h*.49+math.sin(ang)*r
            d.line((x,y,x+math.cos(ang)*r*.045,y+math.sin(ang)*r*.045),fill=a if j%3 else b,width=max(1,int(w/390)))
        _circle(d,w*.5,h*.49,w*.017,b)
    elif e==22: # tape machine / twin reels
        for c in (.30,.70):
            r=w*(.12+bass*.014)
            _circle(d,w*c,h*.45,r,a,3)
            _circle(d,w*c,h*.45,r*.3,b,3)
            for j in range(6):
                angle=j*math.tau/6+phase*.4*(1 if c==.30 else -1)
                line(d,[(w*c,h*.45),(w*c+math.cos(angle)*r*.88,h*.45+math.sin(angle)*r*.88)],muted,3)
        line(d,[(w*.3,h*.57),(w*.5,h*.64),(w*.7,h*.57)],b,2)
        d.rectangle((w*.1,h*.67,w*.9,h*.71),fill=muted)
        d.rectangle((w*.1,h*.67,w*(.1+.8*rms),h*.71),fill=a)
    elif e==23: # editorial typography responsive
        label(d,(w*.5,h*.29),'LISTEN',white,w*.17,True,'mm')
        label(d,(w*.5,h*.42),'TO',a,w*.25,True,'mm')
        label(d,(w*.5,h*.56),'AARXN',white,w*.16,True,'mm')
        d.rectangle((w*.1,h*.65,w*(.1+.8*max(.04,bass)),h*.668),fill=b)
        for j in range(5):
            yy=h*(.72+j*.025)
            d.line((w*.15,yy,w*(.2+.65*(treble+mids)/2),yy),fill=muted,width=1)
    elif e==24:  # arrangement screenshot slow Ken Burns; user-provided image only
        if screen is not None:
            src=(screen.frame_at(t) if hasattr(screen,'frame_at') else screen.copy()).convert('RGB')
            # simple moving horizontal pan on source; portrait target crop
            cropw=max(8,int(src.width*.55))
            offset=(math.sin(phase*.15)*.5+.5)
            left=int((src.width-cropw)*offset)
            src=src.crop((left,0,left+cropw,src.height))
            fitted=ImageOps.fit(src,(w,int(h*.65)),method=Image.Resampling.BICUBIC)
            im.paste(fitted,(0,int(h*.18)))
            d=ImageDraw.Draw(im)
            d.line((w*.5,h*.18,w*.5,h*.83),fill=a,width=3)
        else:
            for row in range(9):
                y=h*(.23+row*.057)
                d.rectangle((w*.08,y,w*.92,y+h*.044),fill=muted)
                for j in range(4):
                    x=w*(.11+(j*.21+row*.037)% .79)
                    x2=min(w*.90,x+w*(.07+(.11*(j%3))))
                    d.rounded_rectangle((x,y+2,x2,y+h*.042),radius=3,fill=a if row%3==0 else b)
            d.line((w*.5,h*.21,w*.5,h*.79),fill=white,width=3)
    # little UI footer, intentionally restrained and user-optional in future
    d.line((w*.09,h*.885,w*.91,h*.885),fill=muted,width=max(1,w//400))
    label(d,(w*.09,h*.915),title[:22].upper(),white,w*.038,True,'lm')
    label(d,(w*.91,h*.915),'LTA',a,w*.045,True,'rm')
    return im
