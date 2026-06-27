import os, struct, glob
base = "/data/workspace/02_AlphaTeam/alpha-blip/docs/Dog asset spec 요청/out"

def info(p):
    with open(p, 'rb') as f:
        h = f.read(33)
    if h[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    w, hh = struct.unpack('>II', h[16:24])
    col = h[25]
    ct = {0: 'Gray', 2: 'RGB', 3: 'Pal', 4: 'GrayA', 6: 'RGBA'}.get(col, col)
    return w, hh, ct

files = sorted(glob.glob(base + "/dogs/*.png")) + sorted(glob.glob(base + "/dogs/acc/*.png")) + [base + "/contact.png"]
dims = {}
bad = []
for p in files:
    r = info(p)
    name = os.path.relpath(p, base)
    if r is None:
        print("NOTPNG", name); continue
    w, hh, ct = r
    dims[(w, hh, ct)] = dims.get((w, hh, ct), 0) + 1
    if ct != 'RGBA' or w != hh:
        bad.append((name, w, hh, ct))
print("size/type histogram:")
for k, v in sorted(dims.items(), key=lambda x: -x[1]):
    print(f"  {k[0]}x{k[1]} {k[2]}: {v} files")
print("TOTAL", len(files))
if bad:
    print("OFF-SPEC (non-RGBA or non-square):")
    for b in bad:
        print("  ", b)
else:
    print("all RGBA + square OK")
