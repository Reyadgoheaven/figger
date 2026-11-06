# control_api.py — additions
import tempfile
from fastapi import UploadFile, File, Form

_uploads: dict[str, bytes] = {}   # id -> bytes; swap for disk in prod

@app.post("/bot/upload")
async def upload(file: UploadFile = File(...),
                 path: str = Form(...),
                 x_bot_token: str | None = Header(default=None)):
    _auth_bot(x_bot_token)
    blob = await file.read()
    if len(blob) > 50 * 1024 * 1024:
        raise HTTPException(413, "too large")
    uid = uuid.uuid4().hex[:12]
    with _lock:
        _uploads[uid] = blob
    # enqueue the agent side
    cid = uuid.uuid4().hex[:12]
    with _lock:
        _queue.append({"id": cid, "type": "upload", "upload_id": uid,
                       "path": path, "ts": time.time()})
    return {"job_id": cid, "upload_id": uid}

@app.get("/agent/upload/{uid}")
def agent_get_upload(uid: str, x_agent_token: str | None = Header(default=None)):
    _auth_agent(x_agent_token)
    with _lock:
        blob = _uploads.get(uid)
    if blob is None:
        raise HTTPException(404, "gone")
    from fastapi.responses import Response
    with _lock:
        _uploads.pop(uid, None)   # one-shot
    return Response(content=blob, media_type="application/octet-stream")
