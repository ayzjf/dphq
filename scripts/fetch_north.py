# scripts/fetch_north.py
import requests
import pandas as pd
import json
import os
from datetime import datetime

def fetch_legulegu_north():
    print(f"[{datetime.now()}] 开始从乐咕乐股抓取北向资金数据...")
    
    url = "https://www.legulegu.com/stockdata/hk-to-a"
    
    # 伪装成浏览器，防止被网站拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # 检查请求是否成功
        
        # 使用 pandas 直接读取网页中的所有表格
        dfs = pd.read_html(response.text)
        
        # 寻找包含“北向资金”的那个表格
        target_df = None
        for df in dfs:
            if '北向资金' in df.columns or '日期' in df.columns:
                target_df = df
                break
        
        if target_df is None:
            print("未在网页中找到北向资金的表格，网站结构可能已改变。")
            return

        # 只取前 20 行（最新的20天）
        target_df = target_df.head(20)
        
        data_list = []
        for index, row in target_df.iterrows():
            date_str = str(row['日期'])
            
            # 清洗数据：把 "3131.78亿" 转换为纯数字 313178000000
            def clean_money(val):
                if pd.isna(val) or val == '-': return 0.0
                val_str = str(val).replace('亿', '').replace(',', '')
                try:
                    return float(val_str) * 100000000 # 乘以一亿
                except:
                    return 0.0

            item = {
                "date": date_str,
                "north_total": clean_money(row['北向资金']),
                "north_sh": clean_money(row['沪股通']),
                "north_sz": clean_money(row['深股通'])
            }
            data_list.append(item)
            
        # 获取当前脚本所在目录的上一级（即项目根目录），确保存在 data 文件夹
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 保存为 JSON
        output_path = os.path.join(data_dir, 'north_data.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
            
        print(f"成功抓取并保存 {len(data_list)} 条数据到 {output_path}")

    except Exception as e:
        print(f"抓取失败: {e}")

if __name__ == "__main__":
    fetch_legulegu_north()
