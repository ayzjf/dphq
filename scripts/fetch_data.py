import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

def fetch_all_data():
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "north_fund": []  # 北向资金
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    # ====== 抓取乐咕乐股 北向资金流向页面 ======
    try:
        print("正在抓取乐咕乐股北向资金数据...")
        url = "https://www.legulegu.com/stockdata/hk-to-a"
        
        res = requests.get(url, headers=headers, timeout=15)
        print(f"状态码: {res.status_code}")
        
        if res.status_code != 200:
            raise Exception(f"HTTP {res.status_code}")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 查找包含北向资金数据的表格
        # 乐咕乐股页面中，表格在 div 或直接是 table 标签内
        tables = soup.find_all('table')
        print(f"找到 {len(tables)} 个表格")
        
        target_rows = []
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    texts = [cell.get_text(strip=True) for cell in cells]
                    # 判断是否是数据行（第一列是日期格式 YYYY-MM-DD）
                    if re.match(r'\d{4}-\d{2}-\d{2}', texts[0]):
                        target_rows.append(texts)
                        print(f"  数据行: {texts}")
        
        # 提取数据
        for row in target_rows:
            date_str = row[0]
            # 提取数值（去掉"亿"字）
            north_total = _extract_float(row[1])
            hgt = _extract_float(row[2])
            sgt = _extract_float(row[3])
            
            data["north_fund"].append({
                "date": date_str,
                "total": north_total,
                "hgt": hgt,
                "sgt": sgt
            })
        
        print(f"✅ 北向资金: {len(data['north_fund'])} 条")
        
    except Exception as e:
        print(f"❌ 北向资金抓取失败: {e}")
        # 备用方案：用 AKShare 接口
        print("尝试备用方案 (AKShare)...")
        try:
            import akshare as ak
            df = ak.stock_hsgt_north_net_flow_in_em(symbol="北向")
            df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            records = df.sort_values('日期', ascending=False).head(30).to_dict('records')
            for r in records:
                data["north_fund"].append({
                    "date": r.get('日期', ''),
                    "total": round(float(r.get('北向资金', 0)) / 1e8, 2),
                    "hgt": round(float(r.get('沪股通', 0)) / 1e8, 2),
                    "sgt": round(float(r.get('深股通', 0)) / 1e8, 2)
                })
            print(f"✅ 北向资金(AKShare备用): {len(data['north_fund'])} 条")
        except Exception as e2:
            print(f"❌ 备用方案也失败: {e2}")

    # 保存
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！更新时间: {data['update_time']}")
    print(f"   北向资金: {len(data['north_fund'])} 条")


def _extract_float(text):
    """从文本中提取浮点数（如 '3131.78亿' -> 3131.78）"""
    match = re.search(r'(-?\d+\.?\d*)', text)
    if match:
        return round(float(match.group(1)), 2)
    return 0.0


if __name__ == "__main__":
    fetch_all_data()
