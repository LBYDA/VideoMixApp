"""用 raw bytes 方法提取 ECutAuto 的中文 prompt
核心思路：先找到所有中文文本块的起始偏移，然后提取周围更大的上下文
"""
import re

EXE_PATH = "D:/ECutauto/ECutAuto.exe"
OUTPUT = "D:/projects/video-mix-app/ecutauto_prompts.txt"

def main():
    with open(EXE_PATH, "rb") as f:
        data = f.read()

    # 把整个文件当作 latin-1 解码（每个字节映射到一个字符），这样中文会变成乱码但不会丢失
    raw_str = data.decode("latin-1")

    # 用正则找所有的 CJK 中文文本块
    cjk = r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]'

    results = []

    # 1. 提取 "你是一个..." prompt
    results.append("=" * 80)
    results.append("ECutAuto AI 完整中文 Prompt")
    results.append("=" * 80)

    # 先定位 "你是一个..."
    for m in re.finditer(r'(你是一个[\s\S]{0,3000}?)(?=\x00{4,}|[^\u4e00-\u9fff\s\w]{5,})', raw_str):
        text = m.group(1)
        # 过滤掉不可见字符
        clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        clean = re.sub(r'[a-zA-Z0-9]{15,}', '', clean)
        clean = re.sub(r'\s{3,}', '\n', clean)
        if len(clean) > 80:
            results.append(f"\n{'='*60}")
            results.append(clean.strip())
            results.append(f"{'='*60}")

    # 2. 搜索特定结构模式
    results.append(f"\n\n{'='*80}")
    results.append("结构关键词")
    results.append(f"{'='*80}")

    # 从第一次提取的中文块中搜索
    patterns = {
        "推广带货": r'推广带货[\s\S]{0,500}?(?=\x00{3,}|#+)',
        "知识分享": r'知识分享[\s\S]{0,500}?(?=\x00{3,}|#+)',
        "观点输出": r'观点输出[\s\S]{0,500}?(?=\x00{3,}|#+)',
        "结构要求": r'结构要求[\s\S]{0,500}?(?=\x00{3,}|#+)',
        "秒定生死": r'秒定生死[\s\S]{0,500}?(?=\x00{3,}|#+)',
        "值不值": r'值不值[\s\S]{0,300}?(?=\x00{3,}|#+)',
        "混剪方案": r'混剪方案[\s\S]{0,500}?(?=\x00{3,}|#+)',
    }

    for name, pattern in patterns.items():
        results.append(f"\n--- {name} ---")
        found = False
        for m in re.finditer(pattern, raw_str):
            text = m.group(0)
            clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
            clean = re.sub(r'[a-zA-Z0-9]{15,}', '', clean)
            clean = re.sub(r'\s{3,}', '\n', clean)
            results.append(clean.strip()[:800])
            found = True
        if not found:
            results.append("(未找到)")

    # 3. 搜索火山引擎 API
    results.append(f"\n\n{'='*80}")
    results.append("API 配置")
    results.append(f"{'='*80}")

    api_matches = re.findall(r'(ark\.cn-beijing\.volces\.com[^\x00]{5,200})', raw_str)
    for m in api_matches:
        clean = re.sub(r'[\x00-\x1f]', ' ', m)
        results.append(clean)

    # 4. 搜索自定义 prompt 结构
    results.append(f"\n\n{'='*80}")
    results.append("Rust 数据结构相关")
    results.append(f"{'='*80}")

    rust_matches = re.findall(r'(custom_prompt[^\x00]{5,200})', raw_str)
    for m in rust_matches:
        clean = re.sub(r'[\x00-\x1f]', ' ', m)
        results.append(clean)

    rust_matches2 = re.findall(r'(system_prompt[^\x00]{5,200})', raw_str)
    for m in rust_matches2:
        clean = re.sub(r'[\x00-\x1f]', ' ', m)
        results.append(clean)

    # 5. 提取 TTS 相关
    results.append(f"\n\n{'='*80}")
    results.append("TTS 相关信息")
    results.append(f"{'='*80}")

    tts_matches = re.findall(r'(tts[^\x00]{5,300})', raw_str, re.IGNORECASE)
    for m in tts_matches:
        clean = re.sub(r'[\x00-\x1f]', ' ', m)
        if len(clean) > 10:
            results.append(clean)

    # 写入文件
    output_text = "\n".join(results)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(output_text)

    # 尝试打印到控制台
    try:
        print(output_text[:3000])
    except:
        print("(终端编码问题，请查看输出文件)")

    print(f"\n\n[done] 结果写入: {OUTPUT}")
    print(f"总长度: {len(output_text):,} 字符")

if __name__ == "__main__":
    main()
