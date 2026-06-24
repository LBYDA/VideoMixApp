import asyncio
import json
import os
import re
import subprocess
import tempfile
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
    """AI智能混剪服务"""

    def __init__(self):
        cfg = get_config()
        self.executor = FFmpegExecutor(
            ffmpeg_path=cfg.ffmpeg_path or "ffmpeg",
            ffprobe_path=cfg.ffprobe_path or "ffprobe",
        )
        self.temp = TempFileManager(cfg.workspace_dir)

    # ═══════ ASR ═══════

    async def run_asr(self, video_paths: list[str], job_id: str) -> list[dict]:
        cfg = get_config()
        results = []

        for i, vp in enumerate(video_paths):
            await self._log(job_id, "info", f"ASR 转写: {Path(vp).name} ({i+1}/{len(video_paths)})")
            segments = await self._transcribe(vp, cfg)
            results.append({
                "file": Path(vp).name,
                "file_path": vp,
                "segments": segments,
            })
        return results

    async def _transcribe(self, video_path: str, cfg) -> list[dict]:
        audio_path = self.temp.get_temp_path(f"asr_{os.urandom(4).hex()}.wav")
        try:
            result = await self.executor.extract_audio(video_path, audio_path)
            if result.returncode != 0:
                return []

            try:
                from faster_whisper import WhisperModel
                model = WhisperModel(cfg.asr_model_size, device="cpu", compute_type="int8")
                segs = []
                gen, _ = model.transcribe(audio_path, language=cfg.asr_language, beam_size=5)
                for s in gen:
                    segs.append({
                        "index": len(segs),
                        "start": round(s.start, 2),
                        "end": round(s.end, 2),
                        "text": s.text.strip(),
                        "duration": round(s.end - s.start, 2),
                    })
                return segs
            except ImportError:
                return []
        except Exception:
            return []
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass

    # ═══════ 文案表 ═══════

    def _build_copy_table(self, video_subtitles: list[dict]) -> str:
        lines = []
        idx = 0
        for vid in video_subtitles:
            lines.append(f"\n# 来源: {vid.get('file', 'unknown')}")
            for seg in vid.get("segments", []):
                text = seg.get("text", "")
                dur = seg.get("duration", round(seg.get("end", 0) - seg.get("start", 0), 2))
                lines.append(f"[{idx}] {text} ({dur}s)")
                idx += 1
        return "\n".join(lines)

    # ═══════ LLM 方案生成 (带重试) ═══════

    async def generate_plan(self, input_data: AiMixInput, video_subtitles: list[dict], job_id: str) -> Optional[AiClipPlan]:
        cfg = get_config()
        copy_table = self._build_copy_table(video_subtitles)

        custom_key = f"custom_prompt_{input_data.style}"
        custom = getattr(cfg, custom_key, "").strip()
        system_prompt = custom if custom else MIX_PROMPTS.get(input_data.style, MIX_PROMPTS["general"])

        user_msg = (
            f"目标时长: 每组 {input_data.target_duration} 秒\n"
            f"输出组数: 1 组\n\n"
            f"{copy_table}"
        )

        await self._log(job_id, "info", f"模式: {MODE_LABELS.get(input_data.style, input_data.style)}")

        # 没有 ASR 字幕数据时，LLM 无法分析，直接走回退方案
        total_segments = sum(len(v.get("segments", [])) for v in video_subtitles)
        if total_segments == 0:
            await self._log(job_id, "info", "无 ASR 字幕数据（未安装 faster-whisper），使用本地回退方案")
            return self._fallback_plan(input_data, video_subtitles)

        if not cfg.llm_api_key:
            await self._log(job_id, "info", "未配置 LLM API Key，使用本地备用方案")
            return self._fallback_plan(input_data, video_subtitles)

        # 最多重试 3 次
        for attempt in range(3):
            try:
                content = await self._call_llm(cfg, system_prompt, user_msg, job_id, attempt)
                if not content:
                    continue

                plan = self._parse_llm_response(content, video_subtitles)
                if plan and plan.segments:
                    await self._log(job_id, "info", f"方案生成成功: {len(plan.segments)} 片段, {plan.total_duration:.1f}s")
                    return plan

                await self._log(job_id, "warn", f"LLM 返回格式错误 (尝试 {attempt+1}/3)，正在重试...")
            except Exception as e:
                await self._log(job_id, "warn", f"LLM 调用失败 (尝试 {attempt+1}/3): {e}")

        await self._log(job_id, "info", "LLM 多次失败，使用本地备用方案")
        return self._fallback_plan(input_data, video_subtitles)

    async def _call_llm(self, cfg, system_prompt: str, user_msg: str, job_id: str, attempt: int) -> Optional[str]:
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
                    "temperature": cfg.llm_temperature,
                },
            )

            if resp.status_code != 200:
                await self._log(job_id, "warn", f"HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _parse_llm_response(self, content: str, video_subtitles: list[dict]) -> Optional[AiClipPlan]:
        # 记录原始返回用于调试
        print(f"[LLM Response] {content[:500]}")

        index_map: list[tuple[str, float, float]] = []
        for vid in video_subtitles:
            for seg in vid.get("segments", []):
                index_map.append((vid.get("file_path", ""), seg.get("start", 0), seg.get("end", 0)))

        try:
            plan_data = self._extract_json(content)
            if not plan_data:
                return None

            if "groups" in plan_data:
                segs = []
                dur = 0.0
                for g in plan_data["groups"]:
                    for idx in g.get("indices", []):
                        if 0 <= idx < len(index_map):
                            fp, s, e = index_map[idx]
                            segs.append(ClipSegment(source_file=fp, start_time=s, end_time=e))
                            dur += e - s
                if segs:
                    return AiClipPlan(segments=segs, total_duration=round(dur, 1))

            if "segments" in plan_data:
                segs = []
                dur = 0.0
                for seg in plan_data["segments"]:
                    d = float(seg.get("end_time", 0)) - float(seg.get("start_time", 0))
                    if d > 0:
                        segs.append(ClipSegment(
                            source_file=str(seg.get("source_file", "")),
                            start_time=float(seg.get("start_time", 0)),
                            end_time=float(seg.get("end_time", 0)),
                            text_overlay=str(seg.get("text_overlay", "")) if seg.get("text_overlay") else None,
                            transition=str(seg.get("transition", "none")),
                        ))
                        dur += d
                if segs:
                    return AiClipPlan(segments=segs, total_duration=round(dur, 1))
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_json(content: str) -> Optional[dict]:
        # 1. 直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 2. 正则提取 { ... }
        m = re.search(r'\{[\s\S]*\}', content)
        if m:
            raw = m.group(0)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
            # 3. 修复常见 JSON 错误（尾部逗号、单引号等）
            raw = re.sub(r',\s*}', '}', raw)
            raw = re.sub(r',\s*]', ']', raw)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_plan(self, input_data: AiMixInput, video_subtitles: list[dict]) -> AiClipPlan:
        import random
        random.seed(42)

        noise = {"嗯", "啊", "那个", "好吧", "哎呀", "妈呀", "然后然后",
                  "扣1", "感谢灯牌", "小黄车", "321上链接", "1号链接",
                  "家人们", "兄弟们", "老铁们", "100%", "纯天然", "根治"}
        segs = []
        remain = input_data.target_duration
        all_subs = []

        # 先从 ASR 字幕提取
        for vid in video_subtitles:
            for seg in vid.get("segments", []):
                text = seg.get("text", "")
                dur = seg.get("duration", seg.get("end", 0) - seg.get("start", 0))
                if any(p in text for p in noise) or dur < 1.0 or dur > 30.0:
                    continue
                all_subs.append((vid.get("file_path", ""), seg["start"], seg["end"], text, dur))

        # 没有 ASR 字幕：直接从视频文件均匀切片
        if not all_subs:
            all_files = [v.get("file_path", "") for v in video_subtitles if v.get("file_path")]
            if all_files:
                clip_dur = 4.0
                num_per_file = max(1, int(remain / len(all_files) / clip_dur))
                for fp in all_files:
                    for i in range(num_per_file):
                        start = i * (clip_dur + 0.5)
                        dur = clip_dur
                        if start + dur > 99999:
                            break
                        all_subs.append((fp, start, start + dur, "", dur))

        all_subs.sort(key=lambda x: x[4], reverse=True)
        for src, start, end, text, dur in all_subs:
            if remain <= 0:
                break
            take = min(dur, remain)
            segs.append(ClipSegment(source_file=src, start_time=start, end_time=start + take,
                                    text_overlay=text[:80] if text else None))
            remain -= take

        return AiClipPlan(segments=segs, total_duration=input_data.target_duration - remain)

    # ═══════ TTS 配音 ═══════

    async def generate_tts(self, text: str, job_id: str) -> Optional[str]:
        """生成 TTS 音频，返回 mp3 文件路径"""
        cfg = get_config()
        if not cfg.tts_enabled or not text.strip():
            return None

        out_path = self.temp.get_temp_path(f"tts_{os.urandom(4).hex()}.mp3")

        # 尝试 edge-tts（免费，无需 API Key）
        try:
            voice = cfg.tts_voice
            proc = await asyncio.create_subprocess_exec(
                "edge-tts", "--text", text, "--voice", voice,
                "--write-media", out_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
            if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                await self._log(job_id, "info", f"TTS 配音生成成功 (edge-tts, {voice})")
                return out_path
        except Exception:
            pass

        # 尝试火山引擎 TTS API
        if cfg.tts_api_key and cfg.tts_api_base:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        cfg.tts_api_base,
                        headers={
                            "Authorization": f"Bearer {cfg.tts_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={"text": text, "voice": cfg.tts_voice},
                    )
                    if resp.status_code == 200:
                        audio_data = resp.content
                        if len(audio_data) > 100:
                            with open(out_path, "wb") as f:
                                f.write(audio_data)
                            await self._log(job_id, "info", "TTS 配音生成成功 (API)")
                            return out_path
            except Exception:
                pass

        await self._log(job_id, "warn", "TTS 配音生成失败，将不放配音")
        return None

    # ═══════ 执行渲染 (含 TTS + 字幕) ═══════

    async def execute(self, req: AiMixExecuteRequest, job_id: str) -> str:
        tracker = create_tracker(job_id, total_steps=3)
        tracker.set_status(JobStatus.RENDERING)

        store = get_job_store()
        store.put(JobRecord.create(job_id=job_id, job_type="ai_mix",
                                    input_summary=f"AI混剪: {len(req.clip_plan.segments)} 片段"))

        try:
            job_dir = self.temp.create_temp_dir(f"ai_mix_{job_id}")
            output = req.output_path
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

            # Step 1: TTS 配音
            tts_path = None
            if req.tts_enabled:
                tracker.set_step(0, "正在生成 TTS 配音...")
                await broadcast_progress(job_id, "progress", tracker.to_dict())
                # 组合所有片段的 text_overlay 作为 TTS 文本
                full_text = " ".join(s.text_overlay or "" for s in req.clip_plan.segments).strip()
                if not full_text:
                    full_text = "这是一个自动生成的混剪视频。"
                tts_path = await self.generate_tts(full_text, job_id)

            # Step 2: 裁剪片段
            total_clips = len(req.clip_plan.segments)
            clip_files = []
            for i, seg in enumerate(req.clip_plan.segments):
                tracker.set_step(1, f"正在裁剪片段 {i+1}/{total_clips}...")
                tracker.ffmpeg_percent = ((i + 1) / total_clips) * 100
                await broadcast_progress(job_id, "progress", tracker.to_dict())

                clip = os.path.join(job_dir, f"clip_{i:04d}.mp4")
                clip_files.append(clip)
                await self.executor.trim(seg.source_file, clip, seg.start_time, seg.end_time, job_id)

            valid_clips = [f for f in clip_files if os.path.exists(f) and os.path.getsize(f) > 0]
            if not valid_clips:
                tracker.set_error("所有片段裁剪失败")
                await broadcast_progress(job_id, "error", tracker.to_dict())
                return job_id

            # Step 3: 拼接 + 字幕烧录 + TTS 混音
            tracker.set_step(2, "正在拼接输出...")
            tracker.ffmpeg_percent = 0.0
            await broadcast_progress(job_id, "progress", tracker.to_dict())

            cfg = get_config()
            codec = cfg.hw_encoder or "libx264"

            # 构建 FFmpeg 参数
            args = []
            for cf in valid_clips:
                args.extend(["-i", cf])
            if tts_path and os.path.exists(tts_path):
                args.extend(["-i", tts_path])

            # 视频 concat
            filters = []
            v_in = [f"[{i}:v]trim=0:99999,setpts=PTS-STARTPTS[v{i}]" for i in range(len(valid_clips))]
            filters.extend(v_in)
            v_labels = "".join(f"[v{i}]" for i in range(len(valid_clips)))
            filters.append(f"{v_labels}concat=n={len(valid_clips)}:v=1:a=0[vout]")

            # 字幕烧录（如果有 text_overlay）
            if any(s.text_overlay for s in req.clip_plan.segments if s.text_overlay):
                subtitle_texts = [s.text_overlay or "" for s in req.clip_plan.segments if s.text_overlay]
                # 把每个片段对应的文字用 drawtext 压上去
                filters.append(
                    f"[vout]drawtext=text='{subtitle_texts[0][:60]}':"
                    f"fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:"
                    f"x=(w-text_w)/2:y=h-th-60:enable='between(0,3)'[vout_s]"
                )
                vout_label = "[vout_s]"
            else:
                vout_label = "[vout]"

            # TTS 音频混入
            if tts_path and os.path.exists(tts_path):
                tts_idx = len(valid_clips)
                filters.append(f"[{tts_idx}:a]volume=1.0,adelay=0:all=1[a1]")
                a_out = "-map \"[a1]\""
            else:
                a_out = ""

            filter_str = ";".join(filters)
            args.extend(["-filter_complex", filter_str, "-map", vout_label])
            if a_out:
                parts = a_out.split()
                for p in parts:
                    args.append(p)

            args.extend([
                "-c:v", codec, "-preset", "medium", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ])
            if not tts_path:
                args.append("-an")
            args.append(output)

            async def on_progress(ffprog):
                tracker.on_ffmpeg_progress(ffprog)
                await broadcast_progress(job_id, "progress", tracker.to_dict())

            result = await self.executor.run(args, job_id, progress_callback=on_progress)

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

    # ═══════ helpers ═══════

    async def _log(self, job_id: str, level: str, message: str):
        await broadcast_progress(job_id, "log", {"level": level, "message": message})

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
