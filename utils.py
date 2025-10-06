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
    max_side = 4096  # keep CPU-friendly; adjust as needed
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
    Create a temp OBJ with 'mtllib'/'usemtl' lines removed.
    Returns path of the stripped temp OBJ.
    """
    fd, tmp_path = tempfile.mkstemp(suffix=".obj")
    os.close(fd)
    with open(src_obj_path, "r", errors="ignore") as s, open(tmp_path, "w") as d:
        for line in s:
            ls = line.lstrip()
            if ls.startswith("mtllib") or ls.startswith("usemtl"):
                continue
            d.write(line)
    return tmp_path

def convert_obj_to_glb(obj_path: str, glb_path: str):
    """
    Convert OBJ(+MTL/tex) to GLB using Assimp CLI.
    Assimp resolves relative texture paths if run in OBJ directory.
    """
    obj_dir = os.path.dirname(obj_path) or "."
    obj_name = os.path.basename(obj_path)
    # assimp export <in> <out> -f glb2
    cmd = ["assimp", "export", obj_name, glb_path, "-f", "glb2"]
    run_cmd(cmd, cwd=obj_dir)
