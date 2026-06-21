import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# 活跃的 WebSocket 连接: job_id -> set[WebSocket]
_active_connections: dict[str, set[WebSocket]] = {}


async def broadcast_progress(job_id: str, event: str, data: dict):
    """向所有订阅该job的客户端广播进度"""
    connections = _active_connections.get(job_id, set())
    dead = set()
    payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)

    for ws in connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)

    connections.difference_update(dead)


def get_broadcast_func(job_id: str):
    """返回一个异步广播函数"""
    async def broadcast(event: str, data: dict):
        await broadcast_progress(job_id, event, data)
    return broadcast


@router.websocket("/ws/progress/{job_id}")
async def progress_websocket(ws: WebSocket, job_id: str):
    await ws.accept()

    if job_id not in _active_connections:
        _active_connections[job_id] = set()
    _active_connections[job_id].add(ws)

    try:
        # 发送连接确认
        await ws.send_json({"event": "connected", "data": {"job_id": job_id}})

        while True:
            # 等待客户端消息（如 cancel）
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "cancel":
                # 转发取消请求（由对应的service处理）
                await broadcast_progress(job_id, "cancel_requested", {"job_id": job_id})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        conns = _active_connections.get(job_id, set())
        conns.discard(ws)
        if not conns:
            _active_connections.pop(job_id, None)
