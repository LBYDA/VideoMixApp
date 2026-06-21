"""提取 ECutAuto 中的完整 AI 混剪 prompt"""
import re
import sys

EXE_PATH = "D:/ECutauto/ECutAuto.exe"

def main():
    with open(EXE_PATH, "rb") as f:
        data = f.read()

    text = ""
    try:
        text = data.decode("utf-8", errors="ignore")
    except:
        pass

    # 提取所有完整的中文 prompt（以"你是一个"开头，至少100字）
    print("=== AI 智能混剪相关的完整 Prompt ===\n")

    # 方法1: 搜索 "你是一个" 之后的完整片段
    prompts_found = set()

    for m in re.finditer(r'(你是一个.{30,3000})', text):
        raw = m.group(1)
        # 清理
        clean = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffefA-Za-z0-9\s\-\_\.\,\;\:\!\?\#\@\(\)\[\]\{\}\{\}\|\\\/\*\+\=\~\`\'\"\%\^\&\$\<\>\n]', '', raw)
        clean = re.sub(r'pB\d*', '', clean)
        clean = re.sub(r'qB\d*', '', clean)
        clean = re.sub(r'([A-Z][a-z]+)+', '', clean)
        clean = re.sub(r'\s+', ' ', clean)
        clean = clean.strip()
        if len(clean) > 60:
            prompts_found.add(clean[:2000])

    for i, prompt in enumerate(prompts_found):
        print(f"\n--- Prompt #{i+1} ---")
        print(prompt[:1500])
        print("...")

    # 方法2: 搜索特定的结构关键词
    print("\n\n=== 关键结构关键词 ===")
    patterns = [
        r'(##\s*内容类型判断.{50,500})',
        r'(##\s*推广带货.{50,500})',
        r'(##\s*知识分享.{50,500})',
        r'(##\s*观点输出.{50,500})',
        r'(##\s*结构要求.{50,500})',
        r'(秒定生死.{50,300})',
        r'(值不值.{50,300})',
        r'(信不信.{50,300})',
        r'(买不买.{50,300})',
        r'(custom_prompt.{20,200})',
        r'(system_prompt.{20,200})',
    ]

    for pat in patterns:
        for m in re.finditer(pat, text):
            raw = m.group(1)
            clean = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s\-\_\.\,\;\:\!\?\#\@\(\)\[\]\{\}\n]', '', raw)
            clean = re.sub(r'\s+', ' ', clean)
            print(f"\n[{pat[:30]}...]")
            print(clean[:300])

    # 方法3: 提取API配置
    print("\n\n=== API 配置信息 ===")
    api_patterns = [
        r'(ark\.cn-beijing\.volces\.com.{10,100})',
        r'(openai.{10,100})',
        r'(api/v3.{10,100})',
    ]
    for pat in api_patterns:
        for m in re.finditer(pat, text):
            clean = re.sub(r'[^\x20-\x7e\u4e00-\u9fff]', '', m.group(1))
            print(f"\n{clean[:200]}")

if __name__ == "__main__":
    main()
