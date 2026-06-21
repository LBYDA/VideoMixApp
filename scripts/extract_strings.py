"""从 ECutAuto.exe 中提取中文/英文关键字符串"""
import re
import sys

EXE_PATH = "D:/ECutauto/ECutAuto.exe"

KEYWORDS = [
    # AI混剪
    "混剪", "智能", "文案", "策划", "提炼", "策划师",
    "smart", "mix", "prompt", "system", "assistant",
    # 分类混剪
    "分类", "category", "group",
    # 视频处理
    "ffmpeg", "filter", "codec", "encode",
    # AI相关
    "LLM", "GPT", "OpenAI", "ark", "volces", "token",
    "temperature", "model",
]

def main():
    print("[info] 搜索 ECutAuto.exe 中... (这可能需要1-2分钟)")

    with open(EXE_PATH, "rb") as f:
        data = f.read()

    # 提取所有可读文本块
    # 使用正则匹配连续的 printable UTF-8 字符
    text = ""
    try:
        text = data.decode("utf-8", errors="ignore")
    except:
        pass

    # 搜索关键词
    found = {}
    for keyword in KEYWORDS:
        matches = []
        for m in re.finditer(keyword, text, re.IGNORECASE):
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 200)
            context = text[start:end].replace("\n", " ").replace("\r", " ").replace("\x00", "")
            # 清理不可见字符
            context = re.sub(r'[^\x20-\x7e\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', '', context)
            if len(context) > 10:
                matches.append(context)

        if matches:
            found[keyword] = matches[:5]  # 每个关键词取前5条

    # 输出
    for kw, contexts in sorted(found.items()):
        print(f"\n{'='*60}")
        print(f"### [{kw}] - {len(contexts)} matches")
        print(f"{'='*60}")
        for i, ctx in enumerate(contexts):
            print(f"  [{i}] ...{ctx[:200]}...")

    # 特殊搜索：找完整的 prompt 文本
    print(f"\n{'='*60}")
    print("### [完整 Prompt 搜索]")
    print(f"{'='*60}")

    # 搜索 "你是一个" 开头的长文本（常见中文prompt开头）
    for m in re.finditer(r'你是一个.{20,800}', text):
        print(f"\n  --- Prompt ---")
        print(f"  {m.group()[:500]}")

    # 搜索 JSON 格式的 prompt
    for m in re.finditer(r'\"system\"\s*:\s*\"[^\"]{15,500}\"', text):
        print(f"\n  --- System prompt (JSON) ---")
        print(f"  {m.group()[:500]}")

if __name__ == "__main__":
    main()
