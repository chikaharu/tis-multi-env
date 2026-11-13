"""
統合原子層: Link の最小原子 = Store / Load

Store(2): (Addr, Val) -> ()     越境2本・同方向 (外, 外)。撃ちっぱなし。
Load(1) : (Addr) -> (Val)       越境2本・逆方向 (外, 内)。往復。
原子はこの2種だけ。媒体 (Medium) のインスタンス1つが1つのスコープ境界。
アドレスの同一性が範疇の同一性 (同アドレス = 同範疇)。
アドレス解決 (スコープ内での名前 -> アドレス) は resolver フックで差し替え可能
(既定は恒等写像。クロストーク内積による解決はここに差し込む)。

派生概念は全て原子の上に定義される:
  - Link: load の応答値を書いた「最後の store」とその load の対 (痕跡から抽出)
  - 辞書: キーをアドレスとする Medium。登録 = Store、照合 = Load
  - リング: アドレスを W で割った余りとする Medium
原子でないもの:
  - スコープ内部の計算 (境界から見えない)
  - 境界自体へのメタ操作 (媒体の設置/解体、キー列挙、フェンス、RMW合成)
"""
from dataclasses import dataclass, field

@dataclass
class Medium:
    resolver: object = None           # addr_raw -> addr (既定: 恒等)
    cells: dict = field(default_factory=dict)
    n_store: int = 0
    n_load: int = 0
    crossings: list = field(default_factory=list)   # (dir, kind, payload)
    trace: list = field(default_factory=list)       # ('S', addr, val) | ('L', addr, returned)

    def _resolve(self, a):
        return self.resolver(a) if self.resolver else a

    def store(self, addr, val):
        a = self._resolve(addr)
        self.crossings.append(("out", "addr", a)); self.crossings.append(("out", "value", val))
        self.cells[a] = val
        self.n_store += 1
        self.trace.append(("S", a, val))

    def load(self, addr):
        a = self._resolve(addr)
        self.crossings.append(("out", "addr", a))
        v = self.cells.get(a)
        self.crossings.append(("in", "value", v))
        self.n_load += 1
        self.trace.append(("L", a, v))
        return v

    # --- メタ操作 (原子ではない。境界自体への操作) ---
    def keys(self):
        return list(self.cells.keys())
    def drop(self, addr):
        self.cells.pop(self._resolve(addr), None)


def extract_links(trace):
    """Link 抽出: 各 load について、そのアドレスへの最後の先行 store と対にする。
    間に同アドレスの store があればそちらが最後の書き手になる (上書きで張り替え)。"""
    last = {}
    links = []
    for i, ev in enumerate(trace):
        if ev[0] == "S":
            last[ev[1]] = i
        else:
            if ev[1] in last:
                links.append((last[ev[1]], i))
    return links
