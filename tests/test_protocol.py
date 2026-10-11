import json, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

def run(state):
    p = subprocess.run([sys.executable, str(ROOT/'cpu6_oracle.py')], input=json.dumps({'op':'step','state':state})+'\n', text=True, capture_output=True, check=True)
    return json.loads(p.stdout)

class Smoke(unittest.TestCase):
    def test_nop(self):
        r = run({'pc':256, 'regs':['0000']*5+['FFFE','0000','0000'], 'memory':[{'address':256,'bytes':'01'}]})
        self.assertTrue(r['ok']); self.assertEqual(r['state']['pc'], 257); self.assertEqual(r['state']['flags'], 0)
    def test_halt(self):
        r = run({'pc':256, 'memory':[{'address':256,'bytes':'00'}]})
        self.assertTrue(r['state']['halted']); self.assertEqual(r['state']['pc'], 257)
    def test_flag_translation_layout(self):
        r = run({'pc':256, 'flags':0, 'memory':[{'address':256,'bytes':'02'}]})
        self.assertEqual(r['state']['flags'], 8)
    def test_branch(self):
        r = run({'pc':256, 'flags':4, 'memory':[{'address':256,'bytes':'14 FE'}]})
        self.assertEqual(r['state']['pc'], 256)

if __name__ == '__main__': unittest.main()
