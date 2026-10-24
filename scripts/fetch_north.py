# scripts/fetch_north.py
import requests
import pandas as pd
import json
import os
from datetime import datetime

def fetch_north_data():
    print(f"[{datetime.now()}] 开始从乐咕乐股抓取北向资金数据...")
    
    url = "https://www.legulegu.com/stockdata/hk-to-a"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 提取网页中的所有表格
        dfs = pd.read_html(response.text)
        
        target_df = None
        # 遍历所有表格，寻找行数大于10且包含“日期”和“北向资金”的表格
        for df in dfs:
            if len(df) >= 10 and '日期' in df.columns and '北向资金' in df.columns:
                target_df = df
                break
                
        if target_df is None:
            print("警告：未在网页中找到包含20天数据的表格。")
            return
            
        # 只取前 20 行
        target_df = target_df.head(20)
        
        # 数据清洗函数：把 "3131.78亿" 转换为 313178000000.0
        def clean_money(val):
            if pd.isna(val) or val == '-': return 0.0
            val_str = str(val).replace('亿', '').replace(',', '').strip()
            try:
                return float(val_str) * 100000000
            except:
                return 0.0

        data_list = []
        for index, row in target_df.iterrows():
            # 读取对应列的数据
            item = {
                "date": str(row['日期']),
                "north_total": clean_money(row['北向资金']),
                "north_sh": clean_money(row['沪股通']),
                "north_sz": clean_money(row['深股通'])
            }
            data_list.append(item)
            
        # 确保 data 文件夹存在
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 保存为 JSON
        output_path = os.path.join(data_dir, 'north_data.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
            
        print(f"成功抓取并保存 {len(data_list)} 条数据到 {output_path}")

    except Exception as e:
        print(f"抓取失败，报错信息: {e}")

if __name__ == "__main__":
    fetch_north_data()
