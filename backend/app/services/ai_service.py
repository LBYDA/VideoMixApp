import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional

import httpx

from ..models.schemas import AiMixInput, AiClipPlan, ClipSegment, AiMixExecuteRequest, JobStatus
from ..models.job import JobRecord, get_job_store
from ..core.ffmpeg_executor import FFmpegExecutor
from ..core.progress import create_tracker, remove_tracker, ProgressTracker
from ..core.tempfile_manager import TempFileManager
from ..config import get_config
from ..api.ws_progress import broadcast_progress
from .prompts import MIX_PROMPTS, MODE_LABELS


class AiMixService:
    """AI智能混剪服务 — 使用 ECutAuto 原始 Prompt"""

    def __init__(self):
        cfg = get_config()
        self.executor = FFmpegExecutor(
            ffmpeg_path=cfg.ffmpeg_path or "ffmpeg",
            ffprobe_path=cfg.ffprobe_path or "ffprobe",
        )
        self.temp = TempFileManager(cfg.workspace_dir)

    # ─── ASR ───

    async def run_asr(self, video_paths: list[str], job_id: str) -> list[dict]:
        """对视频列表执行ASR，返回带序号的字幕片段"""
        cfg = get_config()
        results = []

        for i, vp in enumerate(video_paths):
            await broadcast_progress(job_id, "log", {
                "level": "info",
                "message": f"ASR转写: {Path(vp).name} ({i+1}/{len(video_paths)})"
            })

            segments = await self._transcribe(vp, cfg)
            file_name = Path(vp).name
            results.append({
                "file": file_name,
                "file_path": vp,
                "segments": segments,
            })

        return results

    async def _transcribe(self, video_path: str, cfg) -> list[dict]:
        """使用 faster-whisper 转写单个视频"""
        audio_path = self.temp.get_temp_path(f"asr_{os.urandom(4).hex()}.wav")

        try:
            result = await self.executor.extract_audio(video_path, audio_path)
            if result.returncode != 0:
                return []

            try:
                from faster_whisper import WhisperModel

                model = WhisperModel(cfg.asr_model_size, device="cpu", compute_type="int8")
                segments_list = []
                segments_gen, info = model.transcribe(audio_path, language=cfg.asr_language, beam_size=5)

                for seg in segments_gen:
                    segments_list.append({
                        "index": len(segments_list),  # 片段序号（0-based）
                        "start": round(seg.start, 2),
                        "end": round(seg.end, 2),
                        "text": seg.text.strip(),
                        "duration": round(seg.end - seg.start, 2),
                    })

                return segments_list

            except ImportError:
                return []

        except Exception:
            return []
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass

    # ─── 构建文案表 ───

    def _build_copy_table(self, video_subtitles: list[dict]) -> str:
        """将字幕转换为 ECutAuto 风格的文案表（每行包含序号、文本、时长）"""
        lines = []
        global_idx = 0

        for vid in video_subtitles:
            file_name = vid.get("file", "unknown")
            lines.append(f"\n# 来源: {file_name}")
            for seg in vid.get("segments", []):
                text = seg.get("text", "")
                duration = seg.get("duration", round(seg.get("end", 0) - seg.get("start", 0), 2))
                lines.append(f"[{global_idx}] {text} ({duration}s)")
                global_idx += 1

        return "\n".join(lines)

    # ─── LLM 生成混剪方案 ───

    async def generate_plan(self, input_data: AiMixInput, video_subtitles: list[dict], job_id: str) -> Optional[AiClipPlan]:
        """调用 LLM 使用 ECutAuto 原始 Prompt 生成混剪方案"""
        cfg = get_config()

        # 构建文案表
        copy_table = self._build_copy_table(video_subtitles)

        # 选取对应的 Prompt
        system_prompt = MIX_PROMPTS.get(input_data.style, MIX_PROMPTS["general"])

        # 构建用户消息
        user_msg = (
            f"目标时长: 每组 {input_data.target_duration} 秒\n"
            f"输出组数: 1 组\n\n"
            f"{copy_table}"
        )

        await broadcast_progress(job_id, "log", {
            "level": "info",
            "message": f"使用 Prompt 模式: {MODE_LABELS.get(input_data.style, input_data.style)}"
        })

        if not cfg.llm_api_key:
            return self._generate_fallback_plan(input_data, video_subtitles)

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{cfg.llm_api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {cfg.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": cfg.llm_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                        ],
                        "max_tokens": cfg.llm_max_tokens,
                        "temperature": 0.7,
                    },
                )

                if resp.status_code != 200:
                    error_body = resp.text[:300]
                    await broadcast_progress(job_id, "log", {
                        "level": "warn",
                        "message": f"LLM调用失败 (HTTP {resp.status_code}): {error_body}"
                    })
                    return self._generate_fallback_plan(input_data, video_subtitles)

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # 解析 LLM 返回的 JSON（groups 格式）
                plan = self._parse_llm_response(content, video_subtitles, input_data.target_duration)

                if plan and plan.segments:
                    await broadcast_progress(job_id, "log", {
                        "level": "info",
                        "message": f"LLM 生成方案: {len(plan.segments)} 个片段, 总时长 {plan.total_duration:.1f}s"
                    })
                    return plan

        except Exception as e:
            await broadcast_progress(job_id, "log", {
                "level": "warn",
                "message": f"LLM调用失败，使用备用方案: {e}"
            })

        return self._generate_fallback_plan(input_data, video_subtitles)

    def _parse_llm_response(self, content: str, video_subtitles: list[dict], target_duration: float) -> Optional[AiClipPlan]:
        """解析 LLM 返回的 JSON（groups 格式或直接的 segments 格式）"""
        # 构建片段索引映射表
        index_map: list[tuple[str, float, float]] = []  # (file_path, start, end)
        for vid in video_subtitles:
            file_path = vid.get("file_path", "")
            for seg in vid.get("segments", []):
                index_map.append((file_path, seg.get("start", 0), seg.get("end", 0)))

        try:
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                return None

            plan_data = json.loads(json_match.group())

            # groups 格式 (ECutAuto 原生格式)
            if "groups" in plan_data:
                segments = []
                total_dur = 0.0
                for group in plan_data.get("groups", []):
                    indices = group.get("indices", [])
                    for idx in indices:
                        if 0 <= idx < len(index_map):
                            fp, start, end = index_map[idx]
                            dur = end - start
                            segments.append(ClipSegment(
                                source_file=fp,
                                start_time=start,
                                end_time=end,
                            ))
                            total_dur += dur

                if segments:
                    return AiClipPlan(segments=segments, total_duration=round(total_dur, 1))

            # 直接的 segments 格式（旧格式兼容）
            if "segments" in plan_data:
                segments = []
                total_dur = 0.0
                for seg in plan_data["segments"]:
                    dur = float(seg.get("end_time", 0)) - float(seg.get("start_time", 0))
                    if dur > 0:
                        segments.append(ClipSegment(
                            source_file=seg.get("source_file", ""),
                            start_time=float(seg.get("start_time", 0)),
                            end_time=float(seg.get("end_time", 0)),
                            text_overlay=seg.get("text_overlay"),
                            transition=seg.get("transition", "none"),
                        ))
                        total_dur += dur

                if segments:
                    return AiClipPlan(segments=segments, total_duration=round(total_dur, 1))

        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return None

    def _generate_fallback_plan(self, input_data: AiMixInput, video_subtitles: list[dict]) -> AiClipPlan:
        """无 LLM 时的备用方案：按时间顺序选取非噪声片段"""
        import random
        random.seed(42)

        # 噪声关键词过滤
        noise_patterns = [
            "嗯", "啊", "那个", "好吧", "哎呀", "妈呀", "然后然后",
            "扣1", "感谢灯牌", "小黄车", "321上链接", "1号链接",
            "家人们", "兄弟们", "老铁们", "大家好我是",
            "100%", "纯天然", "根治", "零风险",
        ]

        segments = []
        remaining = input_data.target_duration
        all_subs = []

        for vid in video_subtitles:
            file_path = vid.get("file_path", "")
            for seg in vid.get("segments", []):
                text = seg.get("text", "")
                dur = seg.get("duration", seg.get("end", 0) - seg.get("start", 0))

                # 过滤噪声
                is_noise = any(p in text for p in noise_patterns)
                if is_noise or dur < 1.0 or dur > 30.0:
                    continue

                all_subs.append((file_path, seg["start"], seg["end"], text, dur))

        if not all_subs:
            # 放宽过滤
            for vid in video_subtitles:
                file_path = vid.get("file_path", "")
                for seg in vid.get("segments", []):
                    dur = seg.get("duration", seg.get("end", 0) - seg.get("start", 0))
                    if dur > 0.5:
                        all_subs.append((file_path, seg["start"], seg["end"], seg.get("text", ""), dur))

        # 选择片段
        all_subs.sort(key=lambda x: x[4], reverse=True)  # 优先选长的
        for src, start, end, text, dur in all_subs:
            if remaining <= 0:
                break
            take = min(dur, remaining)
            segments.append(ClipSegment(
                source_file=src,
                start_time=start,
                end_time=start + take,
                text_overlay=text[:50] if text else None,
            ))
            remaining -= take

        return AiClipPlan(segments=segments, total_duration=input_data.target_duration - remaining)

    # ─── 执行 ───

    async def execute(self, req: AiMixExecuteRequest, job_id: str) -> str:
        """执行 AI 混剪渲染"""
        tracker = create_tracker(job_id, total_steps=2)
        tracker.set_status(JobStatus.RENDERING)

        store = get_job_store()
        store.put(JobRecord.create(
            job_id=job_id, job_type="ai_mix",
            input_summary=f"AI混剪: {len(req.clip_plan.segments)} 个片段",
        ))

        try:
            # Step 1: 裁剪片段
            job_dir = self.temp.create_temp_dir(f"ai_mix_{job_id}")
            clip_files = []
            total = len(req.clip_plan.segments)

            for i, seg in enumerate(req.clip_plan.segments):
                clip_path = os.path.join(job_dir, f"clip_{i:04d}.mp4")
                clip_files.append(clip_path)

                tracker.set_step(0, f"裁剪片段 {i+1}/{total}...")
                await broadcast_progress(job_id, "progress", tracker.to_dict())

                await self.executor.trim(
                    seg.source_file, clip_path, seg.start_time, seg.end_time, job_id
                )

            valid_clips = [f for f in clip_files if os.path.exists(f) and os.path.getsize(f) > 0]
            if not valid_clips:
                tracker.set_error("所有片段裁剪失败")
                await broadcast_progress(job_id, "error", tracker.to_dict())
                return job_id

            # Step 2: 拼接
            tracker.set_step(1, "正在拼接输出...")
            await broadcast_progress(job_id, "progress", tracker.to_dict())

            output = req.output_path
            os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)

            async def on_progress(ffprog):
                tracker.on_ffmpeg_progress(ffprog)
                await broadcast_progress(job_id, "progress", tracker.to_dict())

            result = await self.executor.concat(valid_clips, output, job_id, progress_callback=on_progress)

            if result.returncode == 0:
                tracker.set_output(output)
                self._update_job(store, job_id, JobStatus.COMPLETED, output_path=output)
                await broadcast_progress(job_id, "completed", tracker.to_dict())
            else:
                tracker.set_error("渲染失败")
                self._update_job(store, job_id, JobStatus.FAILED, error="渲染失败")
                await broadcast_progress(job_id, "error", tracker.to_dict())

        except Exception as e:
            tracker.set_error(str(e))
            self._update_job(store, job_id, JobStatus.FAILED, error=str(e))
            await broadcast_progress(job_id, "error", tracker.to_dict())

        finally:
            remove_tracker(job_id)
            self.temp.cleanup()

        return job_id

    def _update_job(self, store, job_id: str, status: JobStatus, output_path: str = "", error: str = ""):
        from datetime import datetime, timezone
        rec = store.get(job_id)
        if rec:
            rec.status = status
            if output_path:
                rec.output_path = output_path
            if error:
                rec.error = error
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                rec.completed_at = datetime.now(timezone.utc).isoformat()
            store.put(rec)


_ai_service: Optional[AiMixService] = None


def get_ai_service() -> AiMixService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AiMixService()
    return _ai_service
