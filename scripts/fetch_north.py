import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

def fetch():
    data = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    url = "https://www.legulegu.com/stockdata/hk-to-a"
    print(f"正在抓取: {url}")
    
    res = requests.get(url, headers=headers, timeout=15)
    print(f"状态码: {res.status_code}")
    print(f"页面长度: {len(res.text)} 字符")
    
    if res.status_code != 200:
        raise Exception(f"HTTP {res.status_code}")
    
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # 查找所有表格
    tables = soup.find_all('table')
    print(f"找到 {len(tables)} 个 table 标签")
    
    for idx, table in enumerate(tables):
        rows = table.find_all('tr')
        print(f"  表格{idx+1}: 找到 {len(rows)} 行 (tr)")
        
        for r_idx, row in enumerate(rows):
            cells_td = row.find_all('td')
            cells_th = row.find_all('th')
            all_cells = cells_td + cells_th
            
            if len(all_cells) >= 1:
                texts = [cell.get_text(strip=True) for cell in all_cells]
                first = texts[0] if texts else ""
                
                # 判断是否是日期行
                if re.match(r'^20\d{2}-\d{2}-\d{2}$', first):
                    print(f"    → 数据行: {texts}")
                    if len(texts) >= 4:
                        total = _num(texts[1])
                        hgt = _num(texts[2])
                        sgt = _num(texts[3])
                        data.append({
                            "date": first,
                            "total": total,
                            "hgt": hgt,
                            "sgt": sgt
                        })
    
    # 排序（日期降序）
    data.sort(key=lambda x: x['date'], reverse=True)
    data = data[:20]  # 只取最近20天
    
    # 计算 compare
    for i in range(1, len(data)):
        try:
            data[i]["compare"] = round(data[i]["total"] - data[i-1]["total"], 2)
        except:
            data[i]["compare"] = None
    
    if data:
        data[0]["compare"] = None
    
    result = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "north_fund": data
    }
    
    with open('data/north_fund.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 北向资金抓取完成，共 {len(data)} 条")
    for d in data:
        print(f"   {d['date']} | 北向:{d['total']}亿 | 沪股通:{d['hgt']}亿 | 深股通:{d['sgt']}亿")
    return len(data)

def _num(text):
    match = re.search(r'(-?\d+\.?\d*)', str(text))
    return round(float(match.group(1)), 2) if match else 0.0

if __name__ == "__main__":
    fetch()

