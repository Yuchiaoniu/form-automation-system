import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

from docx_extractor import extract_text
from gemini_analyzer import analyze_form

for fname, label in [
    ('sample-forms/附件二、115年國民體適能科技檢測問卷(成人).docx', '成人'),
    ('sample-forms/附件四、115年國民體適能科技檢測問卷(銀髮).docx', '銀髮'),
]:
    print(f'\n=== {label} ===')
    text, truncated = extract_text(fname)
    print(f'字元數: {len(text)}, 截斷: {truncated}')
    result = analyze_form(text)
    if result['error']:
        print('錯誤:', result['error'])
    else:
        fields = result['fields']
        print(f'識別欄位數: {len(fields)}')
        print(json.dumps(fields[:5], ensure_ascii=False, indent=2))
