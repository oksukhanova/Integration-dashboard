import requests, json, os, re
from datetime import datetime

EMAIL = os.environ["JIRA_EMAIL"]
TOKEN = os.environ["JIRA_TOKEN"]
CLOUD = "dfe4a487-a270-42e0-a8cb-6a00c563efda"
JQL = '''project = PP AND updated >= -30d AND (
  summary ~ "Development:" OR summary ~ "Transfer to Live" OR
  summary ~ "Transfer to support" OR summary ~ "Cost and fee setup" OR
  summary ~ "Set up payment limits" OR summary ~ "[Bug]" OR
  summary ~ "Integrate " OR summary ~ "Integration:"
) ORDER BY updated DESC'''

def fetch_issues():
    url = f"https://api.atlassian.com/ex/jira/{CLOUD}/rest/api/3/search"
    auth = (EMAIL, TOKEN)
    headers = {"Accept": "application/json"}
    issues, start = [], 0
    while True:
        r = requests.get(url, auth=auth, headers=headers, params={
            "jql": JQL, "startAt": start, "maxResults": 100,
            "fields": "summary,status,assignee,updated,issuetype"
        })
        data = r.json()
        batch = data.get("issues", [])
        issues.extend(batch)
        start += len(batch)
        if start >= data.get("total", 0) or not batch:
            break
    return issues

def convert(issues):
    result = []
    for i in issues:
        f = i["fields"]
        s = f.get("summary", "")
        sl = s.lower()
        if not any(sl.startswith(p) or p in sl for p in [
            "development:", "transfer to live", "transfer to support",
            "cost and fee", "set up payment", "[bug]", "integrate ", "integration:"
        ]):
            continue
        result.append({
            "k": i["key"],
            "s": s,
            "st": f.get("status", {}).get("name", ""),
            "a": (f.get("assignee") or {}).get("displayName", ""),
            "u": (f.get("updated") or "")[:10],
            "bug": (f.get("issuetype") or {}).get("name") == "Баг"
        })
    return result

def build_html(issues, snapshot):
    data_json = json.dumps(issues, ensure_ascii=False)
    # читаем шаблон и вставляем данные
    with open("template.html") as f:
        html = f.read()
    html = re.sub(r'const ISSUES = \[.*?\];', f'const ISSUES = {data_json};',
                  html, flags=re.DOTALL)
    html = html.replace('26 Mar 2026', snapshot)
    return html

if __name__ == "__main__":
    snapshot = datetime.now().strftime("%-d %b %Y")
    print("Fetching from Jira...")
    raw = fetch_issues()
    issues = convert(raw)
    print(f"Got {len(issues)} issues")
    html = build_html(issues, snapshot)
    with open("index.html", "w") as f:
        f.write(html)
    print("index.html updated!")
