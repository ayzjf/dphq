# scripts/fetch_north.py
import akshare as ak
import pandas as pd
import json
import os
from datetime import datetime

def fetch_north_data():
    print(f"[{datetime.now()}] 开始抓取北向资金详细数据...")
    
    try:
        # 分别获取沪股通和深股通的历史数据
        print("正在获取沪股通数据...")
        df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
        
        print("正在获取深股通数据...")
        df_sz = ak.stock_hsgt_hist_em(symbol="深股通")
        
        if df_sh is None or df_sh.empty or df_sz is None or df_sz.empty:
            print("警告：未获取到完整的沪深股通数据。")
            return
            
        # 打印一下列名，方便以后排查
        print("沪股通数据列名:", df_sh.columns.tolist())

        # 清洗数据的内部函数：把各种奇怪格式转为纯数字，处理 NaN
        def safe_float(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            val_str = str(val).replace('亿', '').replace(',', '').strip()
            try:
                return float(val_str)
            except:
                return 0.0

        # 尝试计算总成交额（兼容各种可能改版的接口）
        def get_turnover(df):
            # 情况1：直接有“成交总额”或“成交额”列
            for col in ['成交总额', '成交额']:
                if col in df.columns:
                    return df[col].apply(safe_float)
            
            # 情况2：只有“买入成交额”和“卖出成交额”
            if '买入成交额' in df.columns and '卖出成交额' in df.columns:
                return df['买入成交额'].apply(safe_float) + df['卖出成交额'].apply(safe_float)
                
            # 情况3：实在没有，返回全0（防止出现NaN导致前端崩溃）
            print("警告：未能找到成交额相关的列，返回0")
            return pd.Series([0.0] * len(df))

        df_sh['沪股通成交额'] = get_turnover(df_sh)
        df_sz['深股通成交额'] = get_turnover(df_sz)
        
        # 确保日期格式统一（防止一个是 datetime 一个是 string）
        df_sh['日期'] = df_sh['日期'].astype(str)
        df_sz['日期'] = df_sz['日期'].astype(str)
        
        # 按日期合并
        merged_df = pd.merge(df_sh[['日期', '沪股通成交额']], df_sz[['日期', '深股通成交额']], on='日期', how='inner')
        
        # 计算合计
        merged_df['合计成交额'] = merged_df['沪股通成交额'] + merged_df['深股通成交额']
        
        # 只取最近 20 天，并按日期倒序（最新的在最上面）
        merged_df = merged_df.tail(20).sort_values(by='日期', ascending=False)
        
        data_list = []
        for index, row in merged_df.iterrows():
            item = {
                "date": str(row['日期']),
                "north_sh": float(row['沪股通成交额']),
                "north_sz": float(row['深股通成交额']),
                "north_total": float(row['合计成交额'])
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
            
        print(f"成功抓取并保存 {len(data_list)} 条北向资金数据到 {output_path}")

    except Exception as e:
        print(f"抓取失败，报错信息: {e}")

if __name__ == "__main__":
    fetch_north_data()
