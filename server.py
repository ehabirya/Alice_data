# ===== server.py =====
import os, glob, uuid, subprocess, zipfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from utils import (
    ensure_dirs, save_jpeg, run_cmd, strip_materials_to,
    convert_obj_to_glb
)

app = FastAPI(title="Meshroom Headless 3D Reconstruction (OBJ + GLB)")

BASE = "/data"
WORK, OUT = ensure_dirs(BASE)


def run_meshroom(images_dir, out_dir):
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
    Build a ZIP that includes:
      textured/ (if available):
        - texturedMesh.obj, texturedMesh.mtl, textures, and texturedMesh.glb
      mesh/ (always if possible):
        - mesh.obj (materials stripped) and mesh.glb
    Returns True if at least one mesh is added.
    """
    cache = os.path.join(out_dir, "MeshroomCache")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    textured_obj = None
    meshing_obj = None

    textured_candidates = glob.glob(os.path.join(cache, "Texturing", "*", "texturedMesh.obj"))
    if textured_candidates:
        textured_obj = textured_candidates[0]

    meshing_candidates = glob.glob(os.path.join(cache, "Meshing", "*", "mesh.obj"))
    if meshing_candidates:
        meshing_obj = meshing_candidates[0]

    wrote_any = False
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        # -------- Textured branch (OBJ/MTL/tex + GLB) --------
        if textured_obj and os.path.exists(textured_obj):
            base_dir = os.path.dirname(textured_obj)
            mtl_path = os.path.join(base_dir, "texturedMesh.mtl")
            textures = glob.glob(os.path.join(base_dir, "*.png")) + glob.glob(os.path.join(base_dir, "*.jpg"))

            # Add OBJ + MTL + textures
            z.write(textured_obj, "textured/texturedMesh.obj")
            if os.path.exists(mtl_path):
                z.write(mtl_path, "textured/texturedMesh.mtl")
            for t in textures:
                z.write(t, f"textured/{os.path.basename(t)}")

            # Make GLB from the textured OBJ (assimp reads MTL+textures if relative paths are valid)
            textured_glb_tmp = os.path.join(base_dir, "texturedMesh.glb")
            try:
                convert_obj_to_glb(textured_obj, textured_glb_tmp)
                if os.path.exists(textured_glb_tmp):
                    z.write(textured_glb_tmp, "textured/texturedMesh.glb")
                    os.remove(textured_glb_tmp)
            except Exception:
                pass

            wrote_any = True

        # -------- Mesh-only branch (OBJ stripped + GLB) --------
        # Prefer Meshing stage OBJ; if missing, strip textured OBJ
        mesh_src_obj = meshing_obj if (meshing_obj and os.path.exists(meshing_obj)) else textured_obj
        if mesh_src_obj and os.path.exists(mesh_src_obj):
            # OBJ without material refs
            stripped_tmp = strip_materials_to(mesh_src_obj)
            z.write(stripped_tmp, "mesh/mesh.obj")

            # GLB from stripped OBJ
            mesh_glb_tmp = os.path.join(os.path.dirname(mesh_src_obj), "mesh.glb")
            try:
                convert_obj_to_glb(stripped_tmp, mesh_glb_tmp)
                if os.path.exists(mesh_glb_tmp):
                    z.write(mesh_glb_tmp, "mesh/mesh.glb")
                    os.remove(mesh_glb_tmp)
            except Exception:
                pass

            os.remove(stripped_tmp)
            wrote_any = True

    return wrote_any


@app.post("/reconstruct")
async def reconstruct(
    front: UploadFile = File(...),
    back:  UploadFile = File(...),
    side:  UploadFile = File(...)
):
    job = str(uuid.uuid4())
    job_dir = os.path.join(WORK, job)
    images_dir = os.path.join(job_dir, "images")
    out_dir = os.path.join(job_dir, "out")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    try:
        save_jpeg(await front.read(), os.path.join(images_dir, "front.jpg"))
        save_jpeg(await back.read(),  os.path.join(images_dir, "back.jpg"))
        save_jpeg(await side.read(),  os.path.join(images_dir, "side.jpg"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    try:
        run_meshroom(images_dir, out_dir)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=422, detail=f"Meshroom failed:\n{e.stdout}")  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result_zip = os.path.join(OUT, f"{job}.zip")
    ok = pack_both_meshes(out_dir, result_zip)
    if not ok:
        raise HTTPException(status_code=422, detail="No mesh produced. Try more overlap / cleaner background / even lighting.")

    return FileResponse(result_zip, media_type="application/zip", filename="meshes.zip")
