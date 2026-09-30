from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)

from . import auth, cache, catalog, config, ingest

router = APIRouter(prefix="/api")


@router.post("/auth/login")
def login(password: str = Form(...), response: Response = None):
    if password != config.ADMIN_PASSWORD:
        raise HTTPException(401, "Incorrect password")

    auth.create_session_cookie(response)
    return {"ok": True}


@router.post("/auth/logout")
def logout(response: Response):
    auth.clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(_: None = Depends(auth.require_admin)):
    return {"authenticated": True}


@router.get("/tree")
def get_tree(_: None = Depends(auth.require_admin)):
    entries = catalog.list_catalog()

    directories: dict[str, list[dict]] = {}

    for entry in entries:
        directories.setdefault(entry["directory_path"], []).append(entry)

    return {"directories": directories}


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    directory: str = Form(""),
    _: None = Depends(auth.require_admin),
):
    content = await file.read()

    try:
        result = ingest.ingest_file(
            directory_path=directory, file_name=file.filename, content=content
        )
    except ValueError as error:
        raise HTTPException(400, str(error))

    return result


@router.delete("/tables/{table_name}")
def delete_table(table_name: str, _: None = Depends(auth.require_admin)):
    try:
        ingest.delete_table(table_name)
    except ValueError as error:
        raise HTTPException(404, str(error))

    return {"ok": True}


@router.delete("/files")
def delete_file(
    directory: str = Query(""),
    file_name: str = Query(...),
    _: None = Depends(auth.require_admin),
):
    count = ingest.delete_file(directory, file_name)
    return {"ok": True, "deleted": count}


@router.delete("/directories/{directory_path:path}")
def delete_directory(directory_path: str, _: None = Depends(auth.require_admin)):
    count = ingest.delete_directory(directory_path)
    return {"ok": True, "deleted": count}


@router.post("/reload")
def reload(_: None = Depends(auth.require_admin)):
    return cache.reload_cache()
