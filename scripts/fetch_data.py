import akshare as ak
import pandas as pd
import json
from datetime import datetime, timedelta

def fetch_all_data():
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "turnover": [],
        "margin": [],
        "northbound": []
    }

    today = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=100)).strftime("%Y%m%d")

    # ====== 1. 两市成交额（使用 index_zh_a_hist 接口） ======
    try:
        print("正在获取上证指数数据...")
        sh_df = ak.index_zh_a_hist(symbol="000001", period="daily", start_date="20250101", end_date=today)
        print(f"上证列名: {sh_df.columns.tolist()}")
        
        print("正在获取深证成指数据...")
        sz_df = ak.index_zh_a_hist(symbol="399001", period="daily", start_date="20250101", end_date=today)
        print(f"深证列名: {sz_df.columns.tolist()}")
        
        sh_df['date'] = pd.to_datetime(sh_df['日期']).dt.strftime('%Y-%m-%d')
        sz_df['date'] = pd.to_datetime(sz_df['日期']).dt.strftime('%Y-%m-%d')
        
        merged = pd.merge(sh_df[['date', '成交额']], sz_df[['date', '成交额']], 
                         on='date', suffixes=('_sh', '_sz'))
        
        # 成交额单位已经是元，转为亿元
        merged['amount_sh'] = (merged['成交额_sh'] / 1e8).round(2)
        merged['amount_sz'] = (merged['成交额_sz'] / 1e8).round(2)
        merged['amount_total'] = (merged['amount_sh'] + merged['amount_sz']).round(2)
        merged['compare'] = merged['amount_total'].diff().round(2)
        
        records = merged.sort_values('date', ascending=False).head(30).to_dict('records')
        for r in records:
            data["turnover"].append({
                "date": r['date'],
                "sh_amount": float(r['amount_sh']),
                "sz_amount": float(r['amount_sz']),
                "total": float(r['amount_total']),
                "compare": float(r['compare']) if pd.notna(r['compare']) else None
            })
        print(f"✅ 成交额: {len(data['turnover'])} 条")
    except Exception as e:
        print(f"❌ 成交额获取失败: {e}")

    # ====== 2. 两市融资余额 ======
    try:
        print("正在获取融资余额数据...")
        sse_df = ak.stock_margin_sse(start_date=start_date, end_date=today)
        print(f"上交所融资列名: {sse_df.columns.tolist()}")
        
        szse_df = ak.stock_margin_szse(start_date=start_date, end_date=today)
        print(f"深交所融资列名: {szse_df.columns.tolist()}")
        
        sse_df['date'] = pd.to_datetime(sse_df['日期']).dt.strftime('%Y-%m-%d')
        szse_df['date'] = pd.to_datetime(szse_df['日期']).dt.strftime('%Y-%m-%d')
        
        merged_m = pd.merge(sse_df[['date', '融资余额']], szse_df[['date', '融资余额']], 
                            on='date', how='inner', suffixes=('_sh', '_sz'))
        
        merged_m['rzye_sh'] = (merged_m['融资余额_sh'] / 1e8).round(2)
        merged_m['rzye_sz'] = (merged_m['融资余额_sz'] / 1e8).round(2)
        merged_m['rzye_total'] = (merged_m['rzye_sh'] + merged_m['rzye_sz']).round(2)
        merged_m['compare'] = merged_m['rzye_total'].diff().round(2)
        
        records_m = merged_m.sort_values('date', ascending=False).head(30).to_dict('records')
        for r in records_m:
            data["margin"].append({
                "date": r['date'],
                "total": float(r['rzye_total']),
                "compare": float(r['compare']) if pd.notna(r['compare']) else None
            })
        print(f"✅ 融资余额: {len(data['margin'])} 条")
    except Exception as e:
        print(f"❌ 融资余额获取失败: {e}")

    # ====== 3. 北向资金（不传symbol，直接调用） ======
    try:
        print("正在获取北向资金数据...")
        nb_df = ak.stock_hsgt_north_net_flow_in_em()
        print(f"北向资金列名: {nb_df.columns.tolist()}")
        
        nb_df['date'] = pd.to_datetime(nb_df['日期']).dt.strftime('%Y-%m-%d')
        
        # 列名根据实际返回调整
        records_n = nb_df.sort_values('date', ascending=False).head(30).to_dict('records')
        for r in records_n:
            try:
                hgt = float(r.get('沪股通净流入(亿)', r.get('沪股通', 0)))
                sgt = float(r.get('深股通净流入(亿)', r.get('深股通', 0)))
                total = float(r.get('北向资金净流入(亿)', r.get('北向资金', hgt + sgt)))
            except (ValueError, TypeError):
                hgt = sgt = total = 0.0
            
            data["northbound"].append({
                "date": r['date'],
                "hgt": round(hgt, 2),
                "sgt": round(sgt, 2),
                "total": round(total, 2),
                "compare": None
            })
        
        # 计算compare
        for i in range(1, len(data["northbound"])):
            data["northbound"][i]["compare"] = round(
                data["northbound"][i]["total"] - data["northbound"][i-1]["total"], 2
            )
        
        print(f"✅ 北向资金: {len(data['northbound'])} 条")
    except Exception as e:
        print(f"❌ 北向资金获取失败: {e}")

    # 保存为 JSON
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据更新完成！更新时间: {data['update_time']}")
    print(f"   成交额: {len(data['turnover'])} 条")
    print(f"   融资余额: {len(data['margin'])} 条")
    print(f"   北向资金: {len(data['northbound'])} 条")

if __name__ == "__main__":
    fetch_all_data()
