import json
from pathlib import Path
from fastapi import UploadFile

def simple_slugify(value: str) -> str:
    return value.strip().lower().replace(" ","_")

async def read_json_upload(file:UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith('.json'):
        raise ValueError("只能上传JSON格式的文件")

    content = await file.read()


    if not content.strip():
        raise ValueError(f"JSON文件为空: {file.filename}")

    try:
        json.loads(content.decode('utf-8-sig'))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON文件有问题: {file.filename}") from exc

    return content

def save_bytes(path:Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)