import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Desktop'))
from visualisers import PRESETS,ENGINES,draw_scene
from core import parse_midi,load_audio
from demo import make_demo
from exporter import export_reel

class TestReelMaker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=tempfile.TemporaryDirectory()
        cls.wav,cls.mid=make_demo(Path(cls.work.name))
        cls.audio=load_audio(cls.wav,Path(cls.work.name)/'cache')
        cls.midi=parse_midi(cls.mid)

    @classmethod
    def tearDownClass(cls): cls.work.cleanup()

    def test_300_styles(self):
        self.assertEqual(len(PRESETS),300)
        self.assertEqual(len(ENGINES),25)
        self.assertEqual(len(set(p.name for p in PRESETS)),300)

    def test_audio_and_midi(self):
        self.assertGreater(self.audio.duration,10)
        self.assertGreater(len(self.midi.notes),20)
        self.assertTrue(any(n.pitch==60 for n in self.midi.notes))
        self.assertEqual(len(self.audio.at(1)),5)

    def test_all_25_engines_draw(self):
        for engine in range(25):
            scene=draw_scene(PRESETS[engine*12],self.audio,.75,(180,320),self.midi)
            self.assertEqual(scene.size,(180,320))

    def test_visualizer_midi_constraint(self):
        with self.assertRaisesRegex(ValueError,'needs MIDI'):
            export_reel(self.audio,PRESETS[0],str(Path(self.work.name)/'should_not.mp4'),
                        0,1,'160x288',12,None)

    def test_mp4_export_with_audio(self):
        output=Path(self.work.name)/'test.mp4'
        export_reel(self.audio,PRESETS[0],str(output),0,.65,'180x320',12,self.midi)
        self.assertGreater(output.stat().st_size,4000)

if __name__=='__main__':unittest.main()
