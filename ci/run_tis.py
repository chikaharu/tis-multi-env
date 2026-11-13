import os, platform, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "executors"))
from tis_atom import TisAtom

CASES = [
    ("demo2", "demo2.tis", "empty.txt", "demo2.out"),
    ("demo", "demo.tis", "empty.txt", "demo.out"),
    ("streamsum", "streamsum.tis", "streamsum.txt", "streamsum.out"),
]

def crlf_only_diff(a, b):
    return a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n") and a != b

def main():
    print("platform:", platform.system(), platform.release(), platform.machine())
    print("python:", sys.version.split()[0])
    perl = shutil.which("perl")
    print("perl:", perl or "NOT FOUND")
    if perl:
        v = subprocess.run([perl, "-e", "print $^V"], capture_output=True).stdout.decode().strip()
        print("perl version:", v)
    fails = 0
    for name, tis_file, in_file, out_file in CASES:
        tis_text = (ROOT / "programs" / tis_file).read_text(encoding="utf-8")
        stdin_bytes = (ROOT / "inputs" / in_file).read_bytes()
        stdin_text = stdin_bytes.decode("utf-8")
        golden = (ROOT / "expected" / out_file).read_bytes()
        # Python executor (in-process)
        atom_out = TisAtom(tis_text, stdin_text).run().encode("utf-8")
        ok_atom = atom_out == golden
        print(f"[{name}] TisAtom(python) == golden: {'PASS' if ok_atom else 'FAIL'} ({len(atom_out)}B vs {len(golden)}B)")
        if not ok_atom:
            fails += 1
        # Perl reference VM (subprocess)
        if perl:
            r = subprocess.run([perl, str(ROOT / "executors" / "tisrun.pl"), str(ROOT / "programs" / tis_file)],
                               input=stdin_bytes, capture_output=True)
            perl_out = r.stdout
            if perl_out == golden:
                print(f"[{name}] tisrun(perl) == golden: PASS ({len(perl_out)}B)")
            elif crlf_only_diff(perl_out, golden):
                print(f"[{name}] tisrun(perl) == golden: PASS-CRLF (differs only by CRLF translation, {len(perl_out)}B vs {len(golden)}B)")
            else:
                print(f"[{name}] tisrun(perl) == golden: FAIL ({len(perl_out)}B vs {len(golden)}B) rc={r.returncode}")
                fails += 1
            cross = "PASS" if (perl_out == atom_out or crlf_only_diff(perl_out, atom_out)) else "FAIL"
            print(f"[{name}] tisrun vs TisAtom cross-check: {cross}")
            if cross == "FAIL":
                fails += 1
        else:
            print(f"[{name}] tisrun(perl): SKIPPED (no perl in PATH)")
    print("RESULT:", "ALL PASS" if fails == 0 else f"{fails} FAILURES")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
