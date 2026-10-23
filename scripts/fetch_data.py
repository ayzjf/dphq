import akshare as ak
import pandas as pd
import json
from datetime import datetime, timedelta

def fetch_all_data():
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "turnover": [],    # 两市成交额
        "margin": [],       # 融资余额
        "northbound": []    # 北向资金
    }
    
    today = datetime.now().strftime("%Y%m%d")
    # 往前取3个月的数据，防止周末或节假日无数据
    start_date = (datetime.now() - timedelta(days=100)).strftime("%Y%m%d")

    # ====== 1. 两市成交额（上证 + 深证指数日线） ======
    try:
        sh_df = ak.stock_zh_index_daily(symbol="sh000001")
        sz_df = ak.stock_zh_index_daily(symbol="sz399001")
        
        sh_df['date'] = pd.to_datetime(sh_df['date']).dt.strftime('%Y-%m-%d')
        sz_df['date'] = pd.to_datetime(sz_df['date']).dt.strftime('%Y-%m-%d')
        
        merged = pd.merge(sh_df[['date', 'amount']], sz_df[['date', 'amount']], 
                         on='date', suffixes=('_sh', '_sz'))
        
        # 转换为“亿元”
        merged['amount_sh'] = (merged['amount_sh'] / 1e8).round(2)
        merged['amount_sz'] = (merged['amount_sz'] / 1e8).round(2)
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
    except Exception as e:
        print(f"成交额获取失败: {e}")

    # ====== 2. 两市融资余额 ======
    try:
        sse_df = ak.stock_margin_sse(start_date=start_date, end_date=today)
        sse_df['信用交易日期'] = pd.to_datetime(sse_df['信用交易日期']).dt.strftime('%Y-%m-%d')
        
        szse_df = ak.stock_margin_szse(start_date=start_date, end_date=today)
        szse_df['融资融券日期'] = pd.to_datetime(szse_df['融资融券日期']).dt.strftime('%Y-%m-%d')
        
        sse_df = sse_df.rename(columns={'信用交易日期': 'date', '融资余额': 'rzye_sh'})
        szse_df = szse_df.rename(columns={'融资融券日期': 'date', '融资余额': 'rzye_sz'})
        
        merged_m = pd.merge(sse_df[['date', 'rzye_sh']], szse_df[['date', 'rzye_sz']], 
                            on='date', how='inner')
        
        # 转换为“亿元”
        merged_m['rzye_sh'] = (merged_m['rzye_sh'] / 1e8).round(2)
        merged_m['rzye_sz'] = (merged_m['rzye_sz'] / 1e8).round(2)
        merged_m['rzye_total'] = (merged_m['rzye_sh'] + merged_m['rzye_sz']).round(2)
        merged_m['compare'] = merged_m['rzye_total'].diff().round(2)
        
        records_m = merged_m.sort_values('date', ascending=False).head(30).to_dict('records')
        for r in records_m:
            data["margin"].append({
                "date": r['date'],
                "total": float(r['rzye_total']),
                "compare": float(r['compare']) if pd.notna(r['compare']) else None
            })
    except Exception as e:
        print(f"融资余额获取失败: {e}")

    # ====== 3. 北向资金（沪股通 + 深股通 资金流向） ======
    try:
        nb_df = ak.stock_hsgt_north_net_flow_in_em(symbol="沪股通")
        nb_df['日期'] = pd.to_datetime(nb_df['日期']).dt.strftime('%Y-%m-%d')
        
        nb_sz = ak.stock_hsgt_north_net_flow_in_em(symbol="深股通")
        nb_sz['日期'] = pd.to_datetime(nb_sz['日期']).dt.strftime('%Y-%m-%d')
        
        nb_df = nb_df.rename(columns={'日期': 'date', '今日资金净流入': 'hgt_net'})
        nb_sz = nb_sz.rename(columns={'日期': 'date', '今日资金净流入': 'sgt_net'})
        
        merged_n = pd.merge(nb_df[['date', 'hgt_net']], nb_sz[['date', 'sgt_net']], 
                            on='date', how='inner')
        
        # 转换为“亿元”
        merged_n['hgt_net'] = (merged_n['hgt_net'] / 1e8).round(2)
        merged_n['sgt_net'] = (merged_n['sgt_net'] / 1e8).round(2)
        merged_n['total'] = (merged_n['hgt_net'] + merged_n['sgt_net']).round(2)
        merged_n['compare'] = merged_n['total'].diff().round(2)
        
        records_n = merged_n.sort_values('date', ascending=False).head(30).to_dict('records')
        for r in records_n:
            data["northbound"].append({
                "date": r['date'],
                "hgt": float(r['hgt_net']),
                "sgt": float(r['sgt_net']),
                "total": float(r['total']),
                "compare": float(r['compare']) if pd.notna(r['compare']) else None
            })
    except Exception as e:
        print(f"北向资金获取失败: {e}")

    # 保存为 JSON
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已更新，时间: {data['update_time']}")
    print(f"   成交额: {len(data['turnover'])} 条")
    print(f"   融资余额: {len(data['margin'])} 条")
    print(f"   北向资金: {len(data['northbound'])} 条")

if __name__ == "__main__":
    fetch_all_data()

