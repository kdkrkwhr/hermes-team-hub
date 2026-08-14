path = "local/index.html"
with open(path, encoding="utf-8") as f:
    content = f.read()

# The file has literal \\n (double backslash + n) where it should have \n (single backslash + n)
# In Python, to represent a literal backslash in a string, we use \\ 
# So to replace "\\n" (literal backslash-n) we search for r"\n" and replace with r"\\n"... no wait.

# Let's be precise:
# File contains: 브리핑입니다.\\n\\n[어제]  (where \\ is a literal backslash)
# We want:      브리핑입니다.\n\n[어제]    (where \ is a literal backslash)

# In Python raw string: r"\\" = two chars: backslash backslash
# In Python raw string: r"\" = one char: backslash

old_brief = r"function buildBrief(b){ b=b||{}; return '대장님, 오늘 브리핑입니다.\\n\\n[어제]\\n'+(b.yesterday||'—')+'\\n\\n[오늘]\\n'+(b.today||'—')+'\\n\\n[블로커]\\n'+(b.blocker||'없음'); }"
new_brief = "function buildBrief(b){ b=b||{}; return '대장님, 오늘 브리핑입니다.\\n\\n[어제]\\n'+(b.yesterday||'—')+'\\n\\n[오늘]\\n'+(b.today||'—')+'\\n\\n[블로커]\\n'+(b.blocker||'없음'); }"

if old_brief in content:
    content = content.replace(old_brief, new_brief)
    print("Replaced buildBrief successfully")
else:
    # Check what's actually there
    idx = content.find("function buildBrief")
    print(f"buildBrief at index: {idx}")
    snippet = content[idx:idx+200]
    print(f"Actual content: {repr(snippet)}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("File written")
