from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.face_search_service import face_search_service

router = APIRouter(prefix="/search", tags=["Google Photos Vector Search"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit at trust boundary

@router.post("/by-image", response_model=List[Dict[str, Any]])
async def search_faces_by_image(
    file: UploadFile = File(...),
    threshold: float = Form(0.25)
):
    try:
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Ukuran file gambar melebihi batas maksimal 10 MB")
        results = face_search_service.search_person_by_image(contents, limit=12, threshold=threshold)
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal memproses pencarian wajah: {str(e)}")

@router.post("/register-identity")
async def register_identity(
    name: str = Form(...),
    is_watchlist: bool = Form(False),
    notes: str = Form(""),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Ukuran file gambar melebihi batas maksimal 10 MB")
        res = await face_search_service.register_new_identity_async(name.strip(), is_watchlist, contents, notes.strip())
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal mendaftarkan identitas: {str(e)}")

