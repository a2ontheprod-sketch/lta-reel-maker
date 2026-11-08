"""LTA REEL MAKER Windows desktop UI: simple dark three-panel design.
Preview + export use same render engine. Companion to the LTA Master Capture VST3.
"""
from __future__ import annotations
import os
import sys
import math
import time
import queue
import threading
import datetime
import json
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from core import (APP_HOME, CAPTURE_DIR, EXPORT_DIR, load_audio, parse_midi,
                  capture_screen_start,capture_screen_stop,frame_from_video,make_preview_wav,ScreenSequence)
from demo import make_demo
from visualisers import PRESETS, draw_scene
from exporter import export_reel, CancelExport

# UI accent: charcoal + pop pink, close to the approved minimal mockup.
BG='#08080c'; PANEL='#101015'; PANEL2='#15151d'; LINE='#30303b'; PINK='#fa69a9'; WHITE='#f6f4f8'; MUTED='#a3a0b1'; DIM='#726f81'


def button(parent, text, action, accent=False, width=None, size=10):
    bg=PINK if accent else PANEL2
    fg='#120813' if accent else WHITE
    return tk.Button(parent,text=text,command=action,fg=fg,bg=bg,
                     activebackground='#ff9ac5' if accent else '#26212d',activeforeground=fg,
                     relief='flat',bd=0,font=('Segoe UI',size,'bold'),
                     cursor='hand2',padx=12,pady=10,width=width,highlightthickness=0)


def lbl(parent,text,size=10,color=WHITE,bold=False):
    return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,font=('Segoe UI',size,'bold' if bold else 'normal'))


class ReelMakerApp:
    def __init__(self, root, smoke=False):
        self.root=root
        self.root.title('LTA REEL MAKER')
        self.root.geometry('1390x825')
        self.root.minsize(1160,730)
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.audio=None; self.midi=None; self.screen=None; self.audio_path=None
        self.preset=PRESETS[0]; self.page=0; self.filtered=list(PRESETS)
        self.fav_file=APP_HOME/'favourites.json'
        try:self.favourites=set(int(i) for i in json.loads(self.fav_file.read_text(encoding='utf-8')))
        except Exception:self.favourites=set()
        self.only_favs=False
        self.export_busy=False; self.export_cancel=threading.Event()
        self.screen_proc=None; self.screen_path=None
        self.playing=False; self.play_started=0.; self.current_time=0.
        self.clip_start=0.; self.clip_length=15
        self.preview_photo=None; self.preview_size=(328,580)
        self.thumb_images=[]
        self.events=queue.Queue()
        self.last_frame=-1
        self.title_var=tk.StringVar(value='LISTENTOAARXN')
        self.search_var=tk.StringVar(value='')
        self.search_var.trace_add('write',lambda *_:self.apply_filter())
        self.kind_var=tk.StringVar(value='All')
        self.duration_var=tk.StringVar(value='15s')
        self.res_var=tk.StringVar(value='1080p')
        self.build_ui()
        self.root.after(100,self.load_initial_demo)
        self.root.after(65,self.tick)
        if smoke:
            self.root.after(1800,self.root.destroy)

    def build_ui(self):
        header=tk.Frame(self.root,bg=BG,height=78)
        header.pack(fill='x',padx=27,pady=(15,11))
        tk.Label(header,text='LTA',font=('Segoe UI',27,'bold'),fg=WHITE,bg=BG).pack(side='left')
        tk.Label(header,text='REEL MAKER',font=('Segoe UI',15),fg=MUTED,bg=BG).pack(side='left',padx=(12,0),pady=(9,0))
        tk.Label(header,text='●  CAPTURE     —     ◈  VISUALISE     —     ↥  EXPORT',font=('Segoe UI',11),fg=PINK,bg=BG).pack(side='left',expand=True,padx=30)
        button(header,'?',self.show_help,size=12).pack(side='right')
        main=tk.Frame(self.root,bg=BG)
        # Main grid is packed after the fixed footer, so Export stays visible at all sizes.
        main.pack(fill='both',expand=True,padx=21)
        main.grid_columnconfigure(0,weight=1,uniform='a')
        main.grid_columnconfigure(1,weight=2,uniform='a')
        main.grid_columnconfigure(2,weight=1,uniform='a')
        main.grid_rowconfigure(0,weight=1)
        self.left=tk.Frame(main,bg=PANEL,highlightbackground=LINE,highlightthickness=1)
        self.left.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        self.center=tk.Frame(main,bg=PANEL,highlightbackground=LINE,highlightthickness=1)
        self.center.grid(row=0,column=1,sticky='nsew',padx=(0,10))
        self.right=tk.Frame(main,bg=PANEL,highlightbackground=LINE,highlightthickness=1)
        self.right.grid(row=0,column=2,sticky='nsew')
        self.make_left()
        self.make_center()
        self.make_right()
        footer=tk.Frame(self.root,bg=PANEL,height=86,highlightbackground=LINE,highlightthickness=1)
        footer.pack(fill='x',padx=21,pady=(12,15))
        tk.Label(footer,text='REEL',bg=PANEL,fg=WHITE,font=('Segoe UI',13,'bold')).pack(side='left',padx=(23,10))
        self.duration_menu=tk.OptionMenu(footer,self.duration_var,'15s','30s','60s',command=lambda v:self.change_duration(v))
        self.style_menu(self.duration_menu); self.duration_menu.pack(side='left',padx=(0,12))
        lbl(footer,'FORMAT',9,MUTED).pack(side='left',padx=(17,10))
        for key in ('9:16','1:1','16:9'):
            b=button(footer,key,lambda k=key:self.change_format(k),size=10)
            b.pack(side='left',padx=3,pady=13)
            if not hasattr(self,'format_buttons'): self.format_buttons={}
            self.format_buttons[key]=b
        self.format='9:16'
        self.update_format_buttons()
        self.export_button=button(footer,'↥  EXPORT REEL',self.start_export,accent=True,size=13)
        self.export_button.pack(side='right',padx=18,pady=13)
        self.status=lbl(footer,'Ready',9,MUTED)
        self.status.pack(side='right',padx=10)
        # Pack order controls shrinking: reserve the bottom bar before the flexible grid.
        main.pack_forget()
        footer.pack_forget()
        footer.pack(side='bottom',fill='x',padx=21,pady=(12,15))
        main.pack(fill='both',expand=True,padx=21)

    def make_left(self):
        lbl(self.left,'CAPTURE',15,WHITE,True).pack(anchor='w',padx=22,pady=(23,13))
        self.capture_canvas=tk.Canvas(self.left,width=230,height=116,bg=PANEL,highlightthickness=0,cursor='hand2')
        self.capture_canvas.pack(pady=(5,13))
        self.capture_canvas.create_oval(72,2,160,90,outline=PINK,width=4)
        self.capture_canvas.create_oval(104,33,128,57,fill=PINK,outline='')
        self.capture_canvas.create_text(116,108,text='LTA MASTER CAPTURE',fill=WHITE,font=('Segoe UI',11,'bold'))
        self.capture_canvas.bind('<Button-1>',lambda e:self.load_latest_capture())
        self.left_msg=lbl(self.left,'Click to load latest VST recording',9,DIM)
        self.left_msg.pack(pady=(0,16))
        cols=tk.Frame(self.left,bg=PANEL)
        cols.pack(fill='x',padx=17)
        button(cols,'+ AUDIO',self.choose_audio,size=10).grid(row=0,column=0,sticky='ew',padx=4,pady=5)
        button(cols,'+ MIDI',self.choose_midi,size=10).grid(row=0,column=1,sticky='ew',padx=4,pady=5)
        button(cols,'+ SCREEN',self.choose_screen,size=10).grid(row=1,column=0,sticky='ew',padx=4,pady=5)
        self.screen_button=button(cols,'● REC SCREEN',self.toggle_screen_record,size=9)
        self.screen_button.grid(row=1,column=1,sticky='ew',padx=4,pady=5)
        cols.grid_columnconfigure(0,weight=1); cols.grid_columnconfigure(1,weight=1)
        tk.Frame(self.left,bg=LINE,height=1).pack(fill='x',padx=22,pady=13)
        lbl(self.left,'AUDIO',10,MUTED,True).pack(anchor='w',padx=23)
        self.file_label=lbl(self.left,'LTA demo loading…',10,WHITE)
        self.file_label.pack(anchor='w',padx=23,pady=(6,5))
        self.details_label=lbl(self.left,'',9,DIM)
        self.details_label.pack(anchor='w',padx=23)
        lbl(self.left,'REEL TITLE',9,MUTED,True).pack(anchor='w',padx=23,pady=(16,6))
        ent=tk.Entry(self.left,textvariable=self.title_var,bg=PANEL2,fg=WHITE,insertbackground=WHITE,
                     relief='flat',font=('Segoe UI',10),highlightthickness=1,highlightbackground=LINE,highlightcolor=PINK)
        ent.pack(fill='x',padx=21,ipady=9)
        lbl(self.left,'CLIP START  (seconds)',9,MUTED,True).pack(anchor='w',padx=23,pady=(12,5))
        self.start_var=tk.DoubleVar(value=0.0)
        self.start_scale=tk.Scale(self.left,from_=0,to=1,orient='horizontal',variable=self.start_var,
                                  command=self.on_seek,bg=PANEL,fg=WHITE,highlightthickness=0,
                                  troughcolor=PANEL2,activebackground=PINK,showvalue=True,
                                  resolution=.25,sliderlength=18,bd=0)
        self.start_scale.pack(fill='x',padx=18)


    def make_center(self):
        top=tk.Frame(self.center,bg=PANEL)
        top.pack(fill='x',padx=17,pady=(13,8))
        self.preset_label=lbl(top,'CANDY PIANO ROLL',10,WHITE,True)
        self.preset_label.pack(side='left')
        self.midistatus=lbl(top,'MIDI',9,PINK,True)
        self.midistatus.pack(side='right')
        self.preview_holder=tk.Frame(self.center,bg=BG)
        self.preview_holder.pack(fill='both',expand=True,padx=15)
        self.preview_canvas=tk.Canvas(self.preview_holder,bg=BG,highlightthickness=0)
        self.preview_canvas.pack(fill='both',expand=True)
        self.preview_canvas.bind('<Configure>',lambda e:self.force_preview())
        self.preview_handle=None
        ctrl=tk.Frame(self.center,bg=PANEL,height=58)
        ctrl.pack(fill='x',padx=16,pady=(8,14))
        self.play_button=button(ctrl,'▶',self.play_pause,size=13)
        self.play_button.pack(side='left',padx=(0,10))
        self.timeline=tk.Canvas(ctrl,height=25,bg=PANEL,highlightthickness=0,cursor='hand2')
        self.timeline.pack(side='left',fill='x',expand=True,padx=(0,8),pady=13)
        self.timeline.bind('<Button-1>',self.on_timeline_click)
        self.time_label=lbl(ctrl,'0:00 / 0:15',9,MUTED)
        self.time_label.pack(side='right')

    def make_right(self):
        top=tk.Frame(self.right,bg=PANEL)
        top.pack(fill='x',padx=18,pady=(21,13))
        lbl(top,'VISUALISERS',15,WHITE,True).pack(side='left')
        lbl(top,'300',11,PINK,True).pack(side='right')
        self.search=tk.Entry(self.right,textvariable=self.search_var,bg=PANEL2,fg=WHITE,
                             insertbackground=WHITE,relief='flat',highlightthickness=1,
                             highlightbackground=LINE,highlightcolor=PINK,
                             font=('Segoe UI',10))
        self.search.pack(fill='x',padx=17,ipady=8)
        self.search.insert(0,'Search styles…')
        self.search.configure(fg=DIM)
        def on_focus_in(_):
            if self.search_var.get()=='Search styles…':
                self.search.delete(0,'end');self.search.configure(fg=WHITE)
        def on_focus_out(_):
            if not self.search_var.get():
                self.search.insert(0,'Search styles…');self.search.configure(fg=DIM)
        self.search.bind('<FocusIn>',on_focus_in)
        self.search.bind('<FocusOut>',on_focus_out)
        controls=tk.Frame(self.right,bg=PANEL)
        controls.pack(fill='x',padx=15,pady=(10,10))
        self.filter_menu=tk.OptionMenu(controls,self.kind_var,'All','Notes','Audio','Drums','3D','Retro','Typography','Arrangement',command=lambda _:self.apply_filter())
        self.style_menu(self.filter_menu)
        self.filter_menu.pack(side='left')
        self.fav_button=button(controls,'♡',self.toggle_favourites,size=13)
        self.fav_button.pack(side='right')
        self.thumb_frame=tk.Frame(self.right,bg=PANEL)
        self.thumb_frame.pack(fill='both',expand=True,padx=12)
        self.thumb_buttons=[]
        for row in range(3):
            self.thumb_frame.grid_rowconfigure(row,weight=1)
            for col in range(3):
                self.thumb_frame.grid_columnconfigure(col,weight=1)
                c=tk.Canvas(self.thumb_frame,width=100,height=96,bg=PANEL2,highlightthickness=1,highlightbackground=LINE,cursor='hand2')
                c.grid(row=row,column=col,sticky='nsew',padx=4,pady=4)
                c.bind('<Button-1>',lambda e,idx=row*3+col:self.on_tile_click(e,idx))
                self.thumb_buttons.append(c)
        pag=tk.Frame(self.right,bg=PANEL)
        pag.pack(fill='x',padx=16,pady=(9,8))
        button(pag,'‹',self.prev_page,size=14).pack(side='left')
        self.page_label=lbl(pag,'1 / 34',9,MUTED)
        self.page_label.pack(side='left',expand=True)
        button(pag,'›',self.next_page,size=14).pack(side='right')
        self.surprise_button=button(self.right,'✧  SURPRISE ME',self.random_preset,accent=True,size=11)
        self.surprise_button.pack(fill='x',padx=17,pady=(8,16))
        self.populate_tiles()

    @staticmethod
    def style_menu(option):
        option.configure(bg=PANEL2,fg=WHITE,activebackground=PANEL2,activeforeground=WHITE,
                         relief='flat',bd=0,highlightthickness=0,font=('Segoe UI',10,'bold'),cursor='hand2')
        option['menu'].configure(bg=PANEL2,fg=WHITE,activebackground=PINK,activeforeground='#000')

    def set_status(self, text):
        self.status.configure(text=text[:70])

    def load_initial_demo(self):
        try:
            wav,mid=make_demo(APP_HOME/'Demo')
            self.midi=parse_midi(mid)
            self.open_audio(wav)
            self.set_status('Demo loaded — select your beat to begin')
        except Exception as exc:
            self.set_status('Demo error: '+str(exc)[:55])

    def open_audio(self,path):
        self.playing=False
        self.set_status('Analysing audio…')
        self.root.update_idletasks()
        def worker():
            try: self.events.put(('audio',load_audio(path)))
            except Exception as exc: self.events.put(('error','Audio import failed: '+str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def choose_audio(self):
        path=filedialog.askopenfilename(title='Select your beat',filetypes=[('Audio','*.wav *.mp3 *.flac *.m4a *.aiff *.ogg'),('All files','*.*')])
        if path:
            # Do not accidentally display MIDI from the previous beat.
            self.midi=None
            self.open_audio(path)

    def choose_midi(self):
        path=filedialog.askopenfilename(title='Choose exported FL Studio MIDI',filetypes=[('MIDI','*.mid *.midi')])
        if path:
            try:
                self.midi=parse_midi(path)
                self.set_status(f'MIDI imported: {len(self.midi.notes)} notes')
                self.midistatus.configure(text='MIDI ✓',fg=PINK)
                self.populate_tiles()
                self.force_preview()
            except Exception as exc: messagebox.showerror('MIDI import',str(exc))

    def choose_screen(self):
        path=filedialog.askopenfilename(title='Select arrangement screenshot or screen recording',
             filetypes=[('Image or video','*.png *.jpg *.jpeg *.bmp *.mp4 *.mov *.mkv'),('All files','*.*')])
        if path:
            try:
                if Path(path).suffix.lower() in ('.mp4','.mov','.mkv'):
                    self.screen=ScreenSequence(path)
                else:
                    self.screen=Image.open(path).convert('RGB')
                self.set_status('Screen background loaded')
                self.populate_tiles()
                self.force_preview()
            except Exception as exc:messagebox.showerror('Screen import',str(exc))

    def load_latest_capture(self):
        captures=sorted(CAPTURE_DIR.glob('*.wav'),key=lambda p:p.stat().st_mtime,reverse=True)
        if not captures:
            messagebox.showinfo('No capture yet','Open the LTA Reel Capture VST on your FL Studio Master, press REC, play your beat, then press STOP. Come back here and click the capture circle.')
            return
        self.midi=None
        self.open_audio(captures[0])
        self.set_status('Importing '+captures[0].name)

    def toggle_screen_record(self):
        if self.screen_proc:
            proc=self.screen_proc; self.screen_proc=None
            capture_screen_stop(proc)
            self.screen_button.config(text='● REC SCREEN')
            self.set_status('Screen clip saved: '+Path(self.screen_path).name)
            try:self.screen=ScreenSequence(self.screen_path)
            except Exception:pass
        else:
            dest=CAPTURE_DIR/('Screen_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.mp4')
            try:
                self.screen_proc=capture_screen_start(dest)
                self.screen_path=str(dest)
                self.screen_button.config(text='■ STOP SCREEN')
                self.set_status('Recording desktop — click again to stop')
            except Exception as exc:messagebox.showerror('Screen recording',str(exc))

    def apply_filter(self):
        if not hasattr(self,'filtered'):return
        q=self.search_var.get().strip().lower()
        if q=='search styles…':q='' 
        group=self.kind_var.get()
        self.filtered=[p for p in PRESETS if (group=='All' or group==p.family)
                       and (not q or q in p.name.lower() or q in p.family.lower())
                       and (not self.only_favs or p.index in self.favourites)]
        self.page=0
        self.populate_tiles()

    def toggle_favourites(self):
        self.only_favs=not self.only_favs
        self.fav_button.configure(text='♥' if self.only_favs else '♡',fg=PINK if self.only_favs else WHITE)
        self.apply_filter()

    def populate_tiles(self):
        if not hasattr(self,'thumb_buttons'): return
        self.thumb_images=[]
        self.page_label.configure(text=f'{self.page+1} / {max(1,math.ceil(len(self.filtered)/9))}')
        for i,c in enumerate(self.thumb_buttons):
            c.delete('all')
            pos=self.page*9+i
            if pos>=len(self.filtered):
                c.configure(highlightbackground=LINE)
                continue
            p=self.filtered[pos]
            try:
                pic=draw_scene(p,self.audio,0.8,(100,96),self.midi,self.screen,self.title_var.get())
                photo=ImageTk.PhotoImage(pic)
                self.thumb_images.append(photo)
                c.create_image(0,0,image=photo,anchor='nw')
            except Exception: pass
            c.create_rectangle(0,79,100,96,fill=PANEL2,outline='')
            c.create_text(89,12,text='♥' if p.index in self.favourites else '♡',fill=PINK if p.index in self.favourites else WHITE,font=('Segoe UI',12,'bold'))
            name=p.name[:16]
            c.create_text(50,87,text=name,fill=WHITE,font=('Segoe UI',8),anchor='center')
            c.configure(highlightbackground=PINK if p.index==self.preset.index else LINE)

    def on_tile_click(self,event,i):
        idx=self.page*9+i
        if idx>=len(self.filtered): return
        if event.x>74 and event.y<32:
            pid=self.filtered[idx].index
            if pid in self.favourites:self.favourites.remove(pid)
            else:self.favourites.add(pid)
            try:self.fav_file.write_text(json.dumps(sorted(self.favourites)),encoding='utf-8')
            except Exception:pass
            if self.only_favs:self.apply_filter()
            else:self.populate_tiles()
        else:self.select_tile(i)

    def select_tile(self,i):
        idx=self.page*9+i
        if idx<len(self.filtered):self.select_preset(self.filtered[idx])

    def select_preset(self,p):
        self.preset=p
        self.preset_label.configure(text=p.name.upper())
        self.midistatus.configure(text='MIDI' if p.needs_midi else 'AUDIO',fg=PINK if p.needs_midi else MUTED)
        self.populate_tiles()
        self.force_preview()

    def random_preset(self):
        import random
        if self.filtered:self.select_preset(random.choice(self.filtered))

    def prev_page(self):
        self.page=max(0,self.page-1); self.populate_tiles()
    def next_page(self):
        self.page=min(max(0,math.ceil(len(self.filtered)/9)-1),self.page+1);self.populate_tiles()

    def change_duration(self,value):
        self.clip_length=int(value.rstrip('s'))
        if self.audio:
            self.start_scale.configure(to=max(0.,self.audio.duration-self.clip_length))
        self.force_preview()

    def change_format(self,value):
        self.format=value
        self.update_format_buttons()
        self.force_preview()
    def update_format_buttons(self):
        for k,b in self.format_buttons.items():
            b.configure(bg=PINK if k==self.format else PANEL2,fg='#120813' if k==self.format else WHITE)

    def on_seek(self,val):
        self.clip_start=float(val)
        self.current_time=self.clip_start
        self.last_frame=-1
        self.force_preview()

    def force_preview(self):self.last_frame=-1

    def draw_preview(self):
        c=self.preview_canvas
        pw=max(130,c.winfo_width());ph=max(180,c.winfo_height())
        if self.format=='9:16': ratio=9/16
        elif self.format=='1:1':ratio=1
        else:ratio=16/9
        h=min(ph-10,int((pw-10)/ratio))
        w=int(h*ratio)
        if w>pw-10:
            w=pw-10;h=int(w/ratio)
        w=max(64,w);h=max(64,h)
        self.preview_size=(w,h)
        scene=draw_scene(self.preset,self.audio,self.current_time,(w,h),self.midi,self.screen,self.title_var.get())
        photo=ImageTk.PhotoImage(scene)
        self.preview_photo=photo
        c.delete('all')
        c.create_image(pw//2,ph//2,image=photo,anchor='center')
        if self.audio:
            self.time_label.configure(text=f'{int(max(0,self.current_time-self.clip_start))//60}:{int(max(0,self.current_time-self.clip_start))%60:02d} / 0:{self.clip_length:02d}')

    def draw_timeline(self):
        c=self.timeline;w=max(20,c.winfo_width());h=25
        c.delete('all');c.create_line(4,h//2,w-4,h//2,fill=LINE,width=5)
        ratio=clamp((self.current_time-self.clip_start)/max(1,self.clip_length))
        c.create_line(4,h//2,max(4,(w-8)*ratio),h//2,fill=PINK,width=5)
        c.create_oval(max(3,(w-8)*ratio)-4,7,max(3,(w-8)*ratio)+4,19,fill=PINK,outline='')

    def on_timeline_click(self,event):
        ratio=max(0,min(1,event.x/max(1,self.timeline.winfo_width())))
        self.current_time=self.clip_start+ratio*self.clip_length
        if self.playing:
            self.play_pause() # pause; next play starts at clip start for precise WAV sync
        self.force_preview()

    def play_pause(self):
        if not self.audio:return
        if self.playing:
            self.playing=False
            self.play_button.configure(text='▶')
            if sys.platform=='win32':
                import winsound
                winsound.PlaySound(None,winsound.SND_PURGE)
        else:
            self.current_time=self.clip_start
            if sys.platform=='win32':
                try:
                    import winsound
                    p=make_preview_wav(self.audio,self.clip_start,self.clip_length)
                    winsound.PlaySound(p,winsound.SND_FILENAME|winsound.SND_ASYNC)
                except Exception as exc:
                    self.set_status('Audio playback unavailable: '+str(exc)[:45])
            self.play_started=time.monotonic()
            self.playing=True
            self.play_button.configure(text='Ⅱ')
        self.force_preview()

    def tick(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=='audio':
                    self.audio=event[1]
                    self.current_time=self.clip_start=0.
                    self.start_var.set(0.)
                    self.start_scale.configure(to=max(0.,self.audio.duration-self.clip_length))
                    self.file_label.configure(text=Path(self.audio.source).name[:34])
                    self.details_label.configure(text=f'{self.audio.duration:.1f}s • audio ready')
                    self.set_status('Beat analysed — choose a visualiser')
                    self.populate_tiles()
                    self.force_preview()
                elif event[0]=='progress':
                    self.set_status(f'Exporting… {int(event[1]*100)}%')
                elif event[0]=='complete':
                    self.export_busy=False; self.export_button.configure(text='↥  EXPORT REEL',state='normal')
                    self.set_status('MP4 ready!')
                    messagebox.showinfo('Export finished',f'Saved MP4:\n{event[1]}')
                elif event[0]=='error':
                    self.export_busy=False;self.export_button.configure(text='↥  EXPORT REEL',state='normal')
                    self.set_status(event[1][:75])
                    messagebox.showerror('LTA Reel Maker',event[1])
        except queue.Empty:pass
        if self.playing:
            self.current_time=self.clip_start+time.monotonic()-self.play_started
            if self.current_time>=min(self.audio.duration,self.clip_start+self.clip_length):
                self.play_pause()
                self.current_time=self.clip_start
        frame=int(self.current_time*22)
        if frame!=self.last_frame:
            self.last_frame=frame
            try:self.draw_preview();self.draw_timeline()
            except Exception as exc:self.set_status('Preview: '+str(exc)[:55])
        self.root.after(45,self.tick)

    def start_export(self):
        if self.export_busy:
            self.export_cancel.set();self.set_status('Cancelling…');return
        if not self.audio:
            messagebox.showinfo('Import a beat','Choose a WAV/MP3 or load a Master capture first.')
            return
        if self.preset.needs_midi and (self.midi is None or not self.midi.notes):
            messagebox.showinfo('MIDI needed','This note visualiser requires a real .mid export from FL Studio. Choose + MIDI, or select an Audio visualiser.')
            return
        name='LTA_Reel_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.mp4'
        destination=filedialog.asksaveasfilename(title='Export Reel',initialdir=str(EXPORT_DIR),
                     initialfile=name,defaultextension='.mp4',filetypes=[('MP4 video','*.mp4')])
        if not destination:return
        sizes={'9:16':'1080x1920','1:1':'1080x1080','16:9':'1920x1080'}
        self.export_cancel.clear();self.export_busy=True
        self.export_button.configure(text='✕  CANCEL EXPORT')
        # capture settings to avoid threading access to tkinter UI
        audio=self.audio;preset=self.preset;start=self.clip_start;duration=self.clip_length
        midi=self.midi;screen=self.screen;title=self.title_var.get();size=sizes[self.format]
        def worker():
            try:
                output=export_reel(audio,preset,destination,start,duration,size,30,midi,screen,title,
                                   lambda p:self.events.put(('progress',p)),self.export_cancel)
                self.events.put(('complete',output))
            except CancelExport:
                self.events.put(('error','Export cancelled'))
            except Exception as exc:
                self.events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()
        self.set_status('Export starting…')

    def show_help(self):
        messagebox.showinfo('LTA Reel Maker',
            '1. Add a beat (+ AUDIO), or record it with the LTA Reel Capture VST3 on Master and click the large circle.\n\n'
            '2. For accurate piano-roll/chord scenes, export a MIDI file from FL Studio and click + MIDI.\n\n'
            '3. Pick any of 300 looks, select your clip start, and hit EXPORT REEL.\n\n'
            'Arrangement scenes can use your own FL screenshot (+ SCREEN). Screen recording saves an MP4 of your desktop.\n\n'
            'Note: FL Studio does not expose other channels\' exact notes to a standard Master VST3.')

    def close(self):
        if self.screen_proc:capture_screen_stop(self.screen_proc)
        if self.playing and sys.platform=='win32':
            import winsound
            winsound.PlaySound(None,winsound.SND_PURGE)
        self.export_cancel.set()
        self.root.destroy()


def clamp(x):return max(0.,min(1.,x))

if __name__=='__main__':
    root=tk.Tk()
    ReelMakerApp(root,smoke='--smoke' in sys.argv)
    root.mainloop()
