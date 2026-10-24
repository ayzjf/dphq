import akshare as ak
import pandas as pd
import json
from datetime import datetime, timedelta
import time

def fetch_all_data():
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "turnover": [],
        "margin": [],
        "main_fund": []
    }

    today = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=100)).strftime("%Y%m%d")

    # ====== 1. 两市成交额（东方财富指数日线，中文列名） ======
    try:
        print("正在获取成交额数据...")
        sh_df = ak.index_zh_a_hist(symbol="000001", period="daily", start_date="20250101", end_date=today)
        sz_df = ak.index_zh_a_hist(symbol="399001", period="daily", start_date="20250101", end_date=today)
        
        print(f"上证列名: {sh_df.columns.tolist()}")
        print(f"深证列名: {sz_df.columns.tolist()}")
        
        sh_df['date'] = pd.to_datetime(sh_df['日期']).dt.strftime('%Y-%m-%d')
        sz_df['date'] = pd.to_datetime(sz_df['日期']).dt.strftime('%Y-%m-%d')
        
        merged = pd.merge(sh_df[['date', '成交额']], sz_df[['date', '成交额']], 
                         on='date', suffixes=('_sh', '_sz'))
        
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
        print(f"❌ 成交额失败: {e}")

    # ====== 2. 两市融资余额（范围日期查询） ======
    try:
        print("正在获取融资余额数据...")
        time.sleep(1)  # 防反爬
        
        sse_df = ak.stock_margin_sse(start_date=start_date, end_date=today)
        szse_df = ak.stock_margin_szse(start_date=start_date, end_date=today)
        
        print(f"上交所融资行数: {len(sse_df)}, 列名: {sse_df.columns.tolist()}")
        print(f"深交所融资行数: {len(szse_df)}, 列名: {szse_df.columns.tolist()}")
        
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
        print(f"❌ 融资余额失败: {e}")

    # ====== 3. 大盘资金流向（无参数接口，最稳定） ======
    try:
        print("正在获取大盘资金流向数据...")
        time.sleep(1)
        
        flow_df = ak.stock_market_fund_flow()
        print(f"资金流向列名: {flow_df.columns.tolist()}")
        print(f"资金流向行数: {len(flow_df)}")
        
        flow_df['date'] = pd.to_datetime(flow_df['日期']).dt.strftime('%Y-%m-%d')
        flow_df_sorted = flow_df.sort_values('date', ascending=False).head(30)
        
        records_f = flow_df_sorted.to_dict('records')
        for r in records_f:
            try:
                total_net = float(r.get('主力净流入-净额', 0))
                data["main_fund"].append({
                    "date": r['date'],
                    "total": round(total_net, 2),
                    "compare": None
                })
            except (ValueError, TypeError) as e:
                print(f"解析失败: {r}, 错误: {e}")
                pass
        
        # 计算 compare
        for i in range(1, len(data["main_fund"])):
            try:
                data["main_fund"][i]["compare"] = round(
                    data["main_fund"][i]["total"] - data["main_fund"][i-1]["total"], 2
                )
            except:
                pass
        
        print(f"✅ 主力净流入: {len(data['main_fund'])} 条")
    except Exception as e:
        print(f"❌ 资金流向失败: {e}")

    # 保存
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！更新时间: {data['update_time']}")
    print(f"   成交额: {len(data['turnover'])} 条 | 融资余额: {len(data['margin'])} 条 | 主力净流入: {len(data['main_fund'])} 条")

if __name__ == "__main__":
    fetch_all_data()
