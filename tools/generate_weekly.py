#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周周报自动生成脚本
- 调用 DeepSeek（OpenAI 兼容接口）汇总本周（周一至周五）涉外法律要点
- 写入项目根目录的 weekly.json，供 daily-report.html「生成本周周报」按钮动态读取
- 由 .github/workflows/weekly-report.yml 每周五自动运行

环境变量：
  DEEPSEEK_API_KEY  （必填）你的 DeepSeek 密钥，存在 GitHub Secrets 里
  DEEPSEEK_MODEL    （选填）默认 deepseek-chat
  DEEPSEEK_BASE     （选填）默认 https://api.deepseek.com

失败时以非 0 退出且不覆盖 weekly.json。
"""
import os, sys, json, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "weekly.json")

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
MODEL   = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
BASE    = os.environ.get("DEEPSEEK_BASE", "https://api.deepseek.com").strip().rstrip("/")


def week_meta():
    # 北京时间
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    # 本周一与本周五
    monday = now - datetime.timedelta(days=now.weekday())
    friday = monday + datetime.timedelta(days=4)
    label = "%d年%d月%d日 – %d月%d日 · 本周周报" % (
        monday.year, monday.month, monday.day, friday.month, friday.day)
    EN_M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    label_en = "%s %d – %s %d, %d · Weekly Digest" % (
        EN_M[monday.month-1], monday.day, EN_M[friday.month-1], friday.day, friday.year)
    issue = now.isocalendar()[1]  # 当年第几周，作为期号
    span = "%d.%02d.%02d–%02d.%02d" % (monday.year, monday.month, monday.day, friday.month, friday.day)
    return label, label_en, issue, span


PROMPT = """你是「律连全球 · iGlobal Law 国际商贸法律日报」的资深主编（主笔为涉外律师秦林蒿）。
现在请撰写本周（{span}）的「本周周报」，对本周国际商贸与涉外法律领域做一次系统性的回顾汇总。
要求：
1. 面向中国出海企业与跨境业务客户，专业、务实、有全局视角，体现"一周综述"的高度（而非单日快讯）。
2. 四个栏目各 1 条：
   - focus（本周要闻）：综述本周最值得关注的国际经贸/出口管制/制裁/关税主线动向，点出趋势。
   - case（本周案例）：一条本周具有指导意义的跨境/涉外司法或仲裁案例要点及启示。
   - policy（本周政策）：综述本周中国（尤其粤港澳大湾区）涉外/跨境相关的政策法规要点。
   - analysis（律师研判）：以「秦林蒿律师周度研判：」开头，对本周趋势给出面向出海企业的实务建议与下周关注点。
3. 每条包含中文 title（25-45字）/summary（150-220字）/source，以及对应英文 title_en / summary_en / source_en（地道专业英文，analysis 英文以「Attorney Qin's weekly view: 」开头）。
4. 内容须自洽、可信、不得编造具体红头文件编号或不存在的判决书号；来源可写机构名+大致时间。
5. 仅输出 JSON，结构严格如下，不要任何额外文字：
{{
  "focus":    {{"title":"...","summary":"...","source":"来源：... · 本周","title_en":"...","summary_en":"...","source_en":"Source: ... · this week"}},
  "case":     {{"title":"...","summary":"...","source":"来源：...","title_en":"...","summary_en":"...","source_en":"Source: ..."}},
  "policy":   {{"title":"...","summary":"...","source":"来源：...","title_en":"...","summary_en":"...","source_en":"Source: ..."}},
  "analysis": {{"title":"...","summary":"...","source":"来源：...","title_en":"...","summary_en":"...","source_en":"Source: ..."}}
}}"""


def call_api(prompt):
    url = BASE + "/chat/completions"
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是专业的涉外法律资讯主编，只输出合法的 JSON。"},
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
        for f in ("title", "summary", "source", "title_en", "summary_en", "source_en"):
            if not d[k].get(f):
                raise ValueError("栏目 %s 缺少字段 %s" % (k, f))
    return True


def main():
    if not API_KEY:
        print("ERROR: 未设置 DEEPSEEK_API_KEY，跳过生成（保留旧 weekly.json）。", file=sys.stderr)
        sys.exit(1)
    label, label_en, issue, span = week_meta()
    prompt = PROMPT.format(span=span)
    raw = call_api(prompt)
    try:
        content = json.loads(raw)
    except Exception:
        s, e = raw.find("{"), raw.rfind("}")
        content = json.loads(raw[s:e+1])
    validate(content)
    content["weekLabel"] = label
    content["weekLabel_en"] = label_en
    content["issue"] = issue
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(content, fh, ensure_ascii=False, indent=2)
    print("OK: 已写入 %s（第 %d 周 · %s）" % (OUT, issue, label))


if __name__ == "__main__":
    main()
