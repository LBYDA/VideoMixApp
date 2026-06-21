"""提取 ECutAuto 中的完整 AI 混剪 prompt - 输出到文件"""
import re

EXE_PATH = "D:/ECutauto/ECutAuto.exe"
OUTPUT = "D:/projects/video-mix-app/ecutauto_prompts.txt"

def extract_text(binary_path):
    with open(binary_path, "rb") as f:
        # 分段读取，只保留UTF-8有效部分
        chunk_size = 1024 * 1024  # 1MB
        offset = 0
        f.seek(0, 2)
        total = f.tell()
        f.seek(0)

        all_text = []
        while offset < total:
            chunk = f.read(min(chunk_size, total - offset))
            try:
                decoded = chunk.decode("utf-8", errors="strict")
                all_text.append(decoded)
            except UnicodeDecodeError:
                # 跳过包含无效字节的块
                pass
            offset += chunk_size

        return "".join(all_text)

def main():
    print("[info] 提取 UTF-8 文本...")
    text = extract_text(EXE_PATH)
    print(f"[info] 有效文本长度: {len(text):,} 字符")

    results = []

    # 1. 提取 prompt 模式
    results.append("=" * 80)
    results.append("ECutAuto AI 智能混剪 - 完整 Prompt 分析")
    results.append("=" * 80)

    # 搜索 "你是一个" 到下一个不连贯的文本
    for m in re.finditer(r'(你是一个.{50,2500}?)(?=\x00{3,}|pB[A-Z]|[A-Z]{3,}[a-z]{3,}|$)', text):
        raw = m.group(1)
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
        clean = re.sub(r'[a-zA-Z]{10,}', '', clean)
        clean = re.sub(r'\s{3,}', '\n', clean)
        if len(clean) > 100:
            results.append(f"\n{'='*80}")
            results.append(clean.strip())
            results.append(f"{'='*80}")

    # 2. 搜索特定结构
    results.append(f"\n\n{'='*80}")
    results.append("结构关键词搜索")
    results.append(f"{'='*80}")

    keywords_config = {
        "内容类型判断": r'内容类型判断(.{20,600})',
        "推广带货结构": r'推广带货(.{20,800})',
        "知识分享结构": r'知识分享(.{20,800})',
        "观点输出结构": r'观点输出(.{20,800})',
        "结构要求": r'结构要求(.{20,800})',
        "秒定生死": r'秒定生死(.{20,400})',
        "Vlog": r'Vlog.{0,100}剪辑(.{20,800})',
        "混剪方案": r'混剪方案(.{20,400})',
        "自定义prompt": r'custom_prompt(.{10,300})',
        "Volcengine API": r'(ark\.cn-beijing\.volces\.com[^\x00]{10,200})',
        "TTS API": r'(api/v3/tts[^\x00]{10,200})',
    }

    for name, pattern in keywords_config.items():
        results.append(f"\n--- {name} ---")
        found = False
        for m in re.finditer(pattern, text):
            raw = m.group(0)
            clean = re.sub(r'[\x00-\x1f]', ' ', raw)
            clean = re.sub(r'\s+', ' ', clean)
            results.append(clean[:500])
            found = True
        if not found:
            results.append("(未找到)")

    # 3. UI 相关前端字符串
    results.append(f"\n\n{'='*80}")
    results.append("前端 UI 字符串 (Vue.js 组件)")
    results.append(f"{'='*80}")

    ui_patterns = [
        r'(AI.{0,5}智能.{0,5}混剪.{0,50})',
        r'(selectedClip.{0,100})',
        r'(clipOrder.{0,100})',
        r'(dragHandle.{0,100})',
        r'(方案预览.{0,50})',
        r'(方案生成中.{0,30})',
    ]

    for pat in ui_patterns:
        results.append(f"\n[pattern: {pat[:40]}]")
        for m in re.finditer(pat, text):
            clean = re.sub(r'[\x00-\x1f]', ' ', m.group(1))
            results.append(clean[:300])

    # 写入文件
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print(f"[done] 结果写入: {OUTPUT}")
    # 同时打印到控制台
    print("\n".join(results[:50]))
    print("... (完整结果见 ecutauto_prompts.txt)")

if __name__ == "__main__":
    main()
