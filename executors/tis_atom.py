"""
tis_atom.py -- TIS v1 (テクセクタム命令セット) の原子化

B試験: テクセクタムの命令セットを Store/Load の痕跡で表しきる。

設計: 実行状態は全て媒体 (Medium) のセルに置く。境界を越える出来事は
5つの媒体への Store/Load 原子だけであり、それ以外に状態は存在しない。
スコープ内部に残るのは pc・入力カーソル・一時変数だけ (原子層の定義で
「境界から見えない内部計算」)。実行経路は CODE 媒体への Load 列
(= fetch 痕跡) として痕跡に残るので、制御フローも痕跡から再構成できる。

  CODE : 命令列。ローダ (コンパイラ側=世界) が Store、fetch = Load(pc)
  REG  : レジスタ %tN。オペランド読み = Load、結果書き = Store
  ENV  : 変数。var 読み = Load、store 命令 = Store
  IN   : 入力。世界がトークン/バイトを Store 済み。read_* = Load
         (未書込セルの Load = None -> read_int は 0、read_byte は -1、
          read_eof は 1。tisrun の尽きた入力の意味論と一致)
  OUT  : 出力。print_*/write_byte = Store(連番アドレス, 断片)
         標準出力は OUT セルをアドレス順に連結したもの

意味論は tisrun.pl の逐語移植 (数値整形 fmt_val、文字列リテラルの
unescape 順序を含む)。原子層は link_atom.Medium をそのまま使うので、
越境記録・痕跡・Link 抽出は既存の統合原子層が担う。
"""
import math
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from link_atom import Medium, extract_links

NUM = r"-?[\d.eE+-]+"


def parse_num(s):
    return int(s) if re.fullmatch(r"-?\d+", s) else float(s)


def parse_strlit(s):
    assert s.startswith('"') and s.endswith('"')
    body = s[1:-1]
    body = re.sub(r"\\x([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), body)
    body = body.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    body = body.replace('\\"', '"').replace("\\\\", "\\")
    return body


def fmt_val(v):
    if v == int(v) and abs(v) < 9.0e15:
        return str(int(v))
    return "%.15g" % v


FN = {
    "sqrt": math.sqrt, "exp": math.exp, "log": math.log,
    "log2": math.log2, "abs": abs, "sin": math.sin, "cos": math.cos,
    "tan": math.tan,
    "asin": lambda x: math.atan2(x, math.sqrt(1 - x * x)),
    "acos": lambda x: math.atan2(math.sqrt(1 - x * x), x),
    "atan": lambda x: math.atan2(x, 1),
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "floor": lambda v: float(math.floor(v)),
    "ceil": lambda v: float(math.ceil(v)),
    "int": lambda v: float(int(v)),
}


def perl_mod(x, s):
    # tisrun の % : 整数同士では Perl の % (被除数でなく除数側に符号が合う床剰余)
    if float(x) == int(x) and float(s) == int(s):
        return int(x) % int(s)
    return int(x) % int(s)


class TisAtom:
    def __init__(self, tis_text, stdin_text):
        prog, label = [], {}
        for line in tis_text.splitlines():
            line = line.rstrip()
            if re.match(r"\s*(;|$)", line):
                continue
            m = re.fullmatch(r"(L\d+):", line)
            if m:
                label[m.group(1)] = len(prog)
                continue
            prog.append(line)
        self._init_media(prog, label, stdin_text)

    @classmethod
    def from_prog(cls, prog, label, stdin_text):
        vm = cls.__new__(cls)
        vm._init_media(list(prog), dict(label), stdin_text)
        return vm

    def _init_media(self, prog, label, stdin_text):
        self.code = Medium()   # CODE
        self.reg = Medium()    # REG
        self.env = Medium()    # ENV
        self.inp = Medium()    # IN
        self.out = Medium()    # OUT
        self.prog = prog
        self.label = label
        # ローダ: 命令列を CODE 媒体へ Store (世界側の書き込み)
        for i, line in enumerate(prog):
            self.code.store(i, line)
        # 世界: 入力を IN 媒体へ Store (トークン列とバイト列)
        self.tokens = re.findall(r"-?\d+", stdin_text)
        for i, t in enumerate(self.tokens):
            self.inp.store(("tok", i), int(t))
        for i, ch in enumerate(stdin_text):
            self.inp.store(("byt", i), ord(ch))
        self.n_out = 0

    def _emit(self, chunk):
        self.out.store(self.n_out, chunk)
        self.n_out += 1

    def stdout(self):
        return "".join(self.out.cells[i] for i in range(self.n_out))

    def run(self, step_limit=100_000_000):
        pc = 0
        tokpos = 0
        bytepos = 0
        steps = 0
        n = len(self.prog)
        while 0 <= pc < n:
            steps += 1
            if steps > step_limit:
                raise RuntimeError("tis_atom: step limit exceeded")
            ins = self.code.load(pc)          # fetch = Load
            pc += 1
            m = re.fullmatch(r"(%t\d+) = const (" + NUM + r")", ins)
            if m:
                self.reg.store(m.group(1), parse_num(m.group(2)))
                continue
            m = re.fullmatch(r"(%t\d+) = var (\w+)", ins)
            if m:
                v = self.env.load(m.group(2))
                self.reg.store(m.group(1), 0 if v is None else v)
                continue
            m = re.fullmatch(r"(%t\d+) = aff (%t\d+), (" + NUM + r"), (" + NUM + r")", ins)
            if m:
                x = self.reg.load(m.group(2))
                self.reg.store(m.group(1), parse_num(m.group(3)) * x + parse_num(m.group(4)))
                continue
            m = re.fullmatch(r"(%t\d+) = (add|sub|mul|div|mod|pow|and|or) (%t\d+) ; (%t\d+)", ins)
            if m:
                t, op = m.group(1), m.group(2)
                x = self.reg.load(m.group(3))
                s = self.reg.load(m.group(4))
                v = (x + s if op == "add" else x - s if op == "sub" else
                     x * s if op == "mul" else x / s if op == "div" else
                     perl_mod(x, s) if op == "mod" else x ** s if op == "pow" else
                     (1 if (x != 0 and s != 0) else 0) if op == "and" else
                     (1 if (x != 0 or s != 0) else 0))
                self.reg.store(t, v)
                continue
            m = re.fullmatch(r"(%t\d+) = cmp (==|!=|<=|>=|<|>), (%t\d+) ; (%t\d+)", ins)
            if m:
                t, op = m.group(1), m.group(2)
                x = self.reg.load(m.group(3))
                s = self.reg.load(m.group(4))
                v = 1 if ((x == s) if op == "==" else (x != s) if op == "!=" else
                          (x < s) if op == "<" else (x <= s) if op == "<=" else
                          (x > s) if op == ">" else (x >= s)) else 0
                self.reg.store(t, v)
                continue
            m = re.fullmatch(r"(%t\d+) = fn (\w+), (%t\d+)", ins)
            if m:
                x = self.reg.load(m.group(3))
                self.reg.store(m.group(1), FN[m.group(2)](x))
                continue
            m = re.fullmatch(r"(%t\d+) = not (%t\d+)", ins)
            if m:
                x = self.reg.load(m.group(2))
                self.reg.store(m.group(1), 1 if x == 0 else 0)
                continue
            m = re.fullmatch(r"(%t\d+) = read_int", ins)
            if m:
                v = self.inp.load(("tok", tokpos))
                tokpos += 1
                self.reg.store(m.group(1), 0 if v is None else v)
                continue
            m = re.fullmatch(r"(%t\d+) = read_byte", ins)
            if m:
                v = self.inp.load(("byt", bytepos))
                bytepos += 1
                self.reg.store(m.group(1), -1 if v is None else v)
                continue
            m = re.fullmatch(r"(%t\d+) = read_eof", ins)
            if m:
                v = self.inp.load(("tok", tokpos))
                self.reg.store(m.group(1), 1 if v is None else 0)
                continue
            m = re.fullmatch(r"store (\w+), (%t\d+)", ins)
            if m:
                v = self.reg.load(m.group(2))
                self.env.store(m.group(1), v)
                continue
            m = re.fullmatch(r'print_str (".*")', ins)
            if m:
                self._emit(parse_strlit(m.group(1)))
                continue
            m = re.fullmatch(r"print_val (%t\d+)", ins)
            if m:
                self._emit(fmt_val(self.reg.load(m.group(1))))
                continue
            m = re.fullmatch(r"write_byte (%t\d+)", ins)
            if m:
                self._emit(chr(self.reg.load(m.group(1)) & 0xFF))
                continue
            m = re.fullmatch(r"jmp (L\d+)", ins)
            if m:
                pc = self.label[m.group(1)]
                continue
            m = re.fullmatch(r"jz (%t\d+), (L\d+)", ins)
            if m:
                if self.reg.load(m.group(1)) == 0:
                    pc = self.label[m.group(2)]
                continue
            m = re.fullmatch(r"jnz (%t\d+), (L\d+)", ins)
            if m:
                if self.reg.load(m.group(1)) != 0:
                    pc = self.label[m.group(2)]
                continue
            if ins == "halt":
                break
            raise RuntimeError(f"tis_atom: cannot decode instruction: {ins}")
        return self.stdout()
