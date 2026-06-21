"""用字节序列直接搜索中文文本 - 解决编码问题"""
import re

EXE_PATH = "D:/ECutauto/ECutAuto.exe"

def extract_utf8_text(data: bytes) -> str:
    """从二进制数据中提取所有可解码的 UTF-8 文本片断"""
    text_parts = []
    i = 0
    while i < len(data):
        # 找到下一个 UTF-8 序列的起始字节
        for j in range(i, min(i + 4, len(data))):
            b = data[j]
            if b >= 0xC0:  # UTF-8 2/3/4 字节序列的开始
                break
            if 0x20 <= b <= 0x7E:
                break
        else:
            i += 1
            continue

        # 尝试从当前位置解码
        end = min(i + 10000, len(data))
        chunk = data[i:end]
        # 找结尾（遇到长串非打印字符）
        stop = 0
        nonprint = 0
        for k, byte in enumerate(chunk):
            if byte < 0x20 and byte not in (0x0a, 0x0d, 0x09):
                nonprint += 1
                if nonprint > 10:
                    stop = k - 10
                    break
            else:
                nonprint = 0

        if stop > 0:
            chunk = chunk[:stop]

        try:
            decoded = chunk.decode("utf-8")
            if len(decoded) > 5:
                text_parts.append(decoded)
                i += stop if stop > 0 else len(chunk)
            else:
                i += 1
        except UnicodeDecodeError:
            i += 1

    return "\n---BLOCK---\n".join(text_parts)


def main():
    with open(EXE_PATH, "rb") as f:
        # 只读前 300MB 来加速
        f.seek(0, 2)
        total = f.tell()
        f.seek(0)
        print(f"文件大小: {total/1024/1024:.1f} MB")

        # 跳过 PE 头部等，从有意义的段开始
        data = f.read(total)

    print("提取 UTF-8 文本...")
    text = extract_utf8_text(data)
    print(f"提取到 {len(text):,} 字符")

    # 搜索 "你是一个"
    prompts = []
    for m in re.finditer(r'你是一个.{100,3000}?)(?=\n---BLOCK---|$)', text, re.DOTALL):
        clean = m.group(1)
        clean = re.sub(r'[a-zA-Z0-9_]{20,}', '', clean)
        clean = re.sub(r'\s{3,}', '\n', clean)
        clean = clean.strip()
        if len(clean) > 100:
            prompts.append(clean)

    print(f"\n找到 {len(prompts)} 个 prompt\n")

    with open("D:/projects/video-mix-app/ai_prompts.txt", "w", encoding="utf-8") as f:
        for i, p in enumerate(prompts):
            f.write(f"\n{'='*80}\n")
            f.write(f"Prompt #{i+1} ({len(p)} 字)\n")
            f.write(f"{'='*80}\n")
            f.write(p)
            f.write("\n")
            print(f"Prompt #{i+1}: {len(p)} 字")
            print(p[:600])
            print()

    # 搜索其他关键词
    print("\n=== 其他关键信息 ===")
    for kw in ["内容类型判断", "推广带货", "知识分享", "观点输出", "结构要求",
                "秒定生死", "值不值", "信不信", "买不买",
                "volces.com", "custom_prompt", "AiAnalyze",
                "Vlog", "混剪方案", "文案改写", "提炼师"]:
        matches = re.findall(f'.{{0,50}}{kw}.{{0,200}}', text)
        if matches:
            print(f"\n[{kw}]: {len(matches)} 条")
            for m in matches[:3]:
                clean = re.sub(r'\s+', ' ', m)
                print(f"  {clean[:200]}")

if __name__ == "__main__":
    main()
