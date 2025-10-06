# ===== utils.py =====
import os, io, subprocess, tempfile
from PIL import Image

def ensure_dirs(base="/data"):
    work = os.path.join(base, "work")
    out  = os.path.join(base, "out")
    os.makedirs(work, exist_ok=True)
    os.makedirs(out,  exist_ok=True)
    return work, out

def save_jpeg(raw_bytes: bytes, path: str):
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    # keep CPU-friendly sizes; adjust if you have more compute
    max_side = 4096
    if max(img.size) > max_side:
        r = max_side / max(img.size)
        img = img.resize((int(img.size[0]*r), int(img.size[1]*r)))
    img.save(path, "JPEG", quality=95)

def run_cmd(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        e = subprocess.CalledProcessError(p.returncode, cmd, output=p.stdout)
        e.stdout = p.stdout
        raise e
    return p.stdout

def strip_materials_to(src_obj_path: str) -> str:
    """
    Create a temp OBJ file with all 'mtllib' and 'usemtl' lines removed,
    so consumers get a pure geometry OBJ that doesn't reference textures.
    Returns the path to the stripped temp file.
    """
    fd, tmp_path = tempfile.mkstemp(suffix=".obj")
    os.close(fd)
    with open(src_obj_path, "r", errors="ignore") as s, open(tmp_path, "w") as d:
        for line in s:
            if line.lstrip().startswith("mtllib") or line.lstrip().startswith("usemtl"):
                continue
            d.write(line)
    return tmp_path
