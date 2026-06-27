import os, glob, shutil
src = "/data/workspace/02_AlphaTeam/alpha-blip/docs/Dog asset spec 요청/out"
dstd = "/data/workspace/02_AlphaTeam/alpha-blip/server/static/img/dogs"
dsta = dstd + "/acc"
os.makedirs(dsta, exist_ok=True)
n = 0
for p in glob.glob(src + "/dogs/*.png"):
    shutil.copy2(p, os.path.join(dstd, os.path.basename(p))); n += 1
for p in glob.glob(src + "/dogs/acc/*.png"):
    shutil.copy2(p, os.path.join(dsta, os.path.basename(p))); n += 1
print("copied", n)
print("dogs:", len(glob.glob(dstd + "/*.png")), "acc:", len(glob.glob(dsta + "/*.png")))
