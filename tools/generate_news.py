#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日日报自动生成脚本
- 调用 DeepSeek（OpenAI 兼容接口）生成当日 4 条涉外法律资讯
- 写入项目根目录的 news.json，供 daily-report.html 动态读取
- 由 .github/workflows/daily-report.yml 每个工作日自动运行

环境变量：
  DEEPSEEK_API_KEY  （必填）你的 DeepSeek 密钥，存在 GitHub Secrets 里
  DEEPSEEK_MODEL    （选填）默认 deepseek-chat
  DEEPSEEK_BASE     （选填）默认 https://api.deepseek.com

失败时以非 0 退出且不覆盖 news.json，保证页面始终有可用内容。
"""
import os, sys, json, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "news.json")

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
MODEL   = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
BASE    = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com").strip().rstrip("/")

DAYS = ['星期日','星期一','星期二','星期三','星期四','星期五','星期六']

def today_meta():
    # 使用北京时间
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    label = "%d年%d月%d日 · %s" % (now.year, now.month, now.day, DAYS[(now.weekday()+1) % 7])
    issue = now.timetuple().tm_yday  # 当年第几天，作为期号
    return label, issue, now.strftime("%Y.%m.%d")

PROMPT = """你是「律连全球 · iGlobal Law 国际商贸法律日报」的资深编辑（主笔为涉外律师秦林蒿）。
请基于你掌握的国际商贸、涉外法律、跨境合规领域的常识与典型议题，撰写今天（{date}）这一期日报的 4 条内容。
要求：
1. 面向中国出海企业与跨境业务客户，专业、务实、可操作。
2. 四个栏目各 1 条：
   - focus（当日焦点）：一条当前国际经贸/出口管制/制裁/关税等领域的重要动向。
   - case（典型案例）：一条具有指导意义的跨境/涉外司法或仲裁案例要点。
   - policy（政策动态）：一条中国（尤其粤港澳大湾区）涉外/跨境相关的政策法规动态。
   - analysis（律师研判）：以「秦林蒿律师研判：」开头，对一项规则或趋势给出实务建议。
3. 每条包含 title（25-45字标题）、summary（120-180字摘要）、source（来源说明，含机构名与日期）。
4. 内容须自洽、可信、不得编造具体的红头文件编号或不存在的判决书号；来源可写机构名+大致时间。
5. 仅输出 JSON，结构严格如下，不要任何额外文字：
{{
  "focus":    {{"title":"...","summary":"...","source":"来源：... · {dotdate}"}},
  "case":     {{"title":"...","summary":"...","source":"来源：..."}},
  "policy":   {{"title":"...","summary":"...","source":"来源：..."}},
  "analysis": {{"title":"...","summary":"...","source":"来源：..."}}
}}"""

def call_api(prompt):
    url = BASE + "/chat/completions"
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是专业的涉外法律资讯编辑，只输出合法的 JSON。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def validate(d):
    for k in ("focus", "case", "policy", "analysis"):
        if k not in d or not isinstance(d[k], dict):
            raise ValueError("缺少栏目: " + k)
        for f in ("title", "summary", "source"):
            if not d[k].get(f):
                raise ValueError("栏目 %s 缺少字段 %s" % (k, f))
    return True

def main():
    if not API_KEY:
        print("ERROR: 未设置 DEEPSEEK_API_KEY，跳过生成（保留旧 news.json）。", file=sys.stderr)
        sys.exit(1)
    label, issue, dotdate = today_meta()
    prompt = PROMPT.format(date=label, dotdate=dotdate)
    raw = call_api(prompt)
    try:
        content = json.loads(raw)
    except Exception:
        # 容错：截取第一个 { 到最后一个 }
        s, e = raw.find("{"), raw.rfind("}")
        content = json.loads(raw[s:e+1])
    validate(content)
    content["dateLabel"] = label
    content["issue"] = issue
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(content, fh, ensure_ascii=False, indent=2)
    print("OK: 已写入 %s（第 %d 期 · %s）" % (OUT, issue, label))

if __name__ == "__main__":
    main()
