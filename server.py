# ===== server.py =====
import os, glob, uuid, subprocess, zipfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from utils import ensure_dirs, save_jpeg, run_cmd, strip_materials_to

app = FastAPI(title="Meshroom Headless 3D Reconstruction (mesh + texture)")

BASE = "/data"
WORK, OUT = ensure_dirs(BASE)


def run_meshroom(images_dir, out_dir):
    """Run Meshroom headless full pipeline."""
    cmd = [
        "meshroom_photogrammetry",
        "--input", images_dir,
        "--output", out_dir,
        "--forceCompute",
        "--cache", os.path.join(out_dir, "MeshroomCache"),
    ]
    run_cmd(cmd)


def pack_both_meshes(out_dir, zip_path):
    """
    Create a ZIP that contains:
      - textured/* (texturedMesh.obj/.mtl + textures) if available
      - mesh/mesh.obj (materials stripped)
    Returns True if at least one mesh was added.
    """
    cache = os.path.join(out_dir, "MeshroomCache")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    textured_obj = None
    meshing_obj = None

    # Prefer Meshroom textured output if present
    textured_candidates = glob.glob(os.path.join(cache, "Texturing", "*", "texturedMesh.obj"))
    if textured_candidates:
        textured_obj = textured_candidates[0]

    # Mesh from Meshing stage (geometry only)
    meshing_candidates = glob.glob(os.path.join(cache, "Meshing", "*", "mesh.obj"))
    if meshing_candidates:
        meshing_obj = meshing_candidates[0]

    wrote_any = False
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        # 1) Add textured version if we have it
        if textured_obj and os.path.exists(textured_obj):
            base_dir = os.path.dirname(textured_obj)
            mtl_path = os.path.join(base_dir, "texturedMesh.mtl")
            tex_pngs = glob.glob(os.path.join(base_dir, "*.png"))
            tex_jpgs = glob.glob(os.path.join(base_dir, "*.jpg"))

            z.write(textured_obj, "textured/texturedMesh.obj")
            if os.path.exists(mtl_path):
                z.write(mtl_path, "textured/texturedMesh.mtl")
            for t in tex_pngs + tex_jpgs:
                z.write(t, f"textured/{os.path.basename(t)}")
            wrote_any = True

        # 2) Always include a mesh-only OBJ (materials stripped)
        #    Priority: use Meshing stage OBJ; if missing, derive from textured OBJ.
        mesh_only_added = False
        if meshing_obj and os.path.exists(meshing_obj):
            # Strip any mtllib/usemtl lines defensively into a temp path
            stripped_tmp = strip_materials_to(meshing_obj)
            z.write(stripped_tmp, "mesh/mesh.obj")
            os.remove(stripped_tmp)
            mesh_only_added = True
            wrote_any = True
        elif textured_obj and os.path.exists(textured_obj):
            stripped_tmp = strip_materials_to(textured_obj)
            z.write(stripped_tmp, "mesh/mesh.obj")
            os.remove(stripped_tmp)
            mesh_only_added = True
            wrote_any = True

    return wrote_any


@app.post("/reconstruct")
async def reconstruct(
    front: UploadFile = File(...),
    back:  UploadFile = File(...),
    side:  UploadFile = File(...)
):
    """
    Upload 3 photos (front/back/side) -> returns a ZIP containing:
      - textured/texturedMesh.obj (+ .mtl + textures) IF available
      - mesh/mesh.obj (materials stripped) ALWAYS if possible
    """
    job = str(uuid.uuid4())
    job_dir = os.path.join(WORK, job)
    images_dir = os.path.join(job_dir, "images")
    out_dir = os.path.join(job_dir, "out")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Normalize uploads to JPEG (helps consistency & EXIF)
    try:
        save_jpeg(await front.read(), os.path.join(images_dir, "front.jpg"))
        save_jpeg(await back.read(),  os.path.join(images_dir, "back.jpg"))
        save_jpeg(await side.read(),  os.path.join(images_dir, "side.jpg"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    # Run Meshroom
    try:
        run_meshroom(images_dir, out_dir)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=422, detail=f"Meshroom failed:\n{e.stdout}")  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Package results
    result_zip = os.path.join(OUT, f"{job}.zip")
    ok = pack_both_meshes(out_dir, result_zip)
    if not ok:
        raise HTTPException(status_code=422, detail="No mesh produced. Try more overlap / cleaner background / even lighting.")

    return FileResponse(result_zip, media_type="application/zip", filename="meshes.zip")
