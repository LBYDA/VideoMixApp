"""专门提取 ECutAuto 中 "你是一个..." 开头的完整 prompt"""
import re
import json

EXE_PATH = "D:/ECutauto/ECutAuto.exe"

def main():
    with open(EXE_PATH, "rb") as f:
        data = f.read()

    text = data.decode("latin-1")

    prompts = []

    # 搜索所有 "你是一个" 开头，直到非打印字符序列
    for m in re.finditer(r'(你是一个[\s\S]{50,5000}?)(?=\x00{5,}|[^·\s\w\u4e00-\u9fff\u3000-\u303f\uff00-\uffef#*\+\-,.;:!?\d\[\(\{\}\]\)]{10,})', text):
        raw = m.group(1)
        clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw)
        clean = re.sub(r'[a-z]{15,}', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'[\w\d]{30,}', '', clean)
        clean = re.sub(r'  +', ' ', clean)
        clean = clean.strip()
        if len(clean) > 80 and clean not in prompts:
            prompts.append(clean)

    # 输出
    with open("D:/projects/video-mix-app/ai_prompts.txt", "w", encoding="utf-8") as f:
        f.write(f"找到 {len(prompts)} 个完整 Prompt\n")
        f.write("=" * 80 + "\n\n")

        for i, p in enumerate(prompts):
            f.write(f"--- Prompt #{i+1} (长度: {len(p)} 字) ---\n")
            f.write(p)
            f.write(f"\n\n{'='*80}\n\n")

    print(f"找到 {len(prompts)} 个 prompt")
    for i, p in enumerate(prompts):
        print(f"\n--- Prompt #{i+1} ({len(p)}字) ---")
        print(p[:500])
        if len(p) > 500:
            print(f"... (共 {len(p)} 字)")

    # 同时搜索结构化的设计模式
    print("\n\n=== AI 混剪请求结构 ===")
    for m in re.finditer(r'(AiAnalyzeRequest[\s\S]{0,300}?elements)', text):
        clean = re.sub(r'[\x00-\x1f]', ' ', m.group(0))
        print(clean[:300])

    for m in re.finditer(r'(custom_prompt[\s\S]{0,200}?)(?=\x00{3,})', text):
        clean = re.sub(r'[\x00-\x1f]', ' ', m.group(0))
        print(clean[:200])

if __name__ == "__main__":
    main()
