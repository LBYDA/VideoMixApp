from ..models.schemas import VideoMixRequest, VideoTrack, FilterChainNode, OutputSettings


class FilterGraphBuilder:
    """FFmpeg filter_complex 构建器"""

    def __init__(self):
        self.filters: list[str] = []
        self.input_labels: list[str] = []
        self.output_video_label = ""
        self.output_audio_label = ""
        self._counter = 0

    def _next_label(self, prefix: str = "v") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def build(self, req: VideoMixRequest) -> str:
        """构建完整的 filter_complex 字符串"""
        parts = []

        # 处理每个轨道
        prev_video_labels = []
        prev_audio_labels = []

        for i, track in enumerate(req.tracks):
            input_idx = i
            v_label = f"[{input_idx}:v]"
            a_label = f"[{input_idx}:a]" if track.volume > 0 else ""

            # Trim
            if track.start > 0 or track.end > 0:
                trim_label = self._next_label("tv")
                dur = track.end - track.start
                parts.append(f"{v_label}trim=start={track.start}:duration={dur},setpts=PTS-STARTPTS{trim_label}")
                v_label = trim_label

            # Speed
            if track.speed != 1.0:
                speed_label = self._next_label("sp")
                pts_factor = 1.0 / track.speed
                parts.append(f"{v_label}setpts={pts_factor}*PTS{speed_label}")
                v_label = speed_label

                if a_label:
                    audio_speed_label = self._next_label("as")
                    parts.append(f"{a_label}atempo={track.speed}{audio_speed_label}")
                    a_label = audio_speed_label

            # Scale
            if track.scale != 1.0:
                scale_label = self._next_label("sc")
                parts.append(f"{v_label}scale=iw*{track.scale}:ih*{track.scale}{scale_label}")
                v_label = scale_label

            prev_video_labels.append(v_label)
            if a_label:
                prev_audio_labels.append(a_label)

        # 视频混合（叠加）
        if len(prev_video_labels) == 1:
            final_video = prev_video_labels[0]
        else:
            # 多轨道叠加
            base = prev_video_labels[0]
            for j in range(1, len(prev_video_labels)):
                overlay_label = self._next_label("ov")
                track = req.tracks[j] if j < len(req.tracks) else None
                x = "0"
                y = "0"
                if track and track.position_x is not None and track.position_y is not None:
                    x = str(track.position_x)
                    y = str(track.position_y)
                else:
                    x = "(W-w)/2"
                    y = "(H-h)/2"

                parts.append(f"{base}{prev_video_labels[j]}overlay={x}:{y}{overlay_label}")
                base = overlay_label
            final_video = base

        # 音频混合
        final_audio = ""
        if len(prev_audio_labels) > 1:
            audio_mix_label = self._next_label("am")
            inputs = "".join(prev_audio_labels)
            parts.append(f"{inputs}amix=inputs={len(prev_audio_labels)}:duration=longest{audio_mix_label}")
            final_audio = audio_mix_label
        elif len(prev_audio_labels) == 1:
            final_audio = prev_audio_labels[0]

        # 构建输出映射
        map_part = f"-map \"{final_video}\""
        if final_audio:
            map_part += f" -map \"{final_audio}\""

        filter_str = ";".join(parts)
        if filter_str:
            filter_str = f"-filter_complex \"{filter_str}\" {map_part}"

        return filter_str

    def build_blur_background(self, input_path: str, bg_scale: tuple = (1920, 1080)) -> str:
        """构建模糊背景效果（用于竖屏+横屏素材混合）"""
        return (
            f"[0:v]split[original][copy];"
            f"[copy]scale={bg_scale[0]}:{bg_scale[1]}:force_original_aspect_ratio=decrease,boxblur=20[bg];"
            f"[bg][original]overlay=(W-w)/2:(H-h)/2[v]"
        )

    def build_pip(self, main_idx: int = 0, pip_idx: int = 1,
                  pip_scale: tuple = (480, 270), position: str = "W-w-20:H-h-20") -> str:
        """构建画中画效果"""
        return (
            f"[{pip_idx}:v]scale={pip_scale[0]}:{pip_scale[1]}[pip];"
            f"[{main_idx}:v][pip]overlay={position}[v]"
        )


def build_filter_complex(req: VideoMixRequest) -> str:
    """快捷函数：根据请求构建 filter_complex"""
    builder = FilterGraphBuilder()
    return builder.build(req)
