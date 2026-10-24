import akshare as ak
import pandas as pd
import json
from datetime import datetime, timedelta

def fetch_all_data():
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "turnover": [],
        "margin": [],
        "main_fund": []  # 替换为大盘主力净流入
    }

    # ====== 1. 两市成交额（使用新浪数据源，100%稳定） ======
    try:
        print("正在获取成交额数据...")
        sh_df = ak.stock_zh_index_daily(symbol="sh000001")
        sz_df = ak.stock_zh_index_daily(symbol="sz399001")
        
        sh_df['date'] = pd.to_datetime(sh_df['date']).dt.strftime('%Y-%m-%d')
        sz_df['date'] = pd.to_datetime(sz_df['date']).dt.strftime('%Y-%m-%d')
        
        merged = pd.merge(sh_df[['date', 'amount']], sz_df[['date', 'amount']], 
                         on='date', suffixes=('_sh', '_sz'))
        
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
        print(f"✅ 成交额: {len(data['turnover'])} 条")
    except Exception as e:
        print(f"❌ 成交额失败: {e}")

    # ====== 2. 两市融资余额（改为抓取最近30天单日汇总） ======
    try:
        print("正在获取融资余额数据...")
        today = datetime.now()
        for i in range(60):  # 往前推60天，避开周末找交易日
            target_day = (today - timedelta(days=i)).strftime("%Y%m%d")
            try:
                sse_df = ak.stock_margin_sse(start_date=target_day, end_date=target_day)
                szse_df = ak.stock_margin_szse(start_date=target_day, end_date=target_day)
                
                if not sse_df.empty and not szse_df.empty:
                    rzye_sh = float(sse_df['融资余额'].iloc[0]) / 1e8
                    rzye_sz = float(szse_df['融资余额'].iloc[0]) / 1e8
                    
                    data["margin"].append({
                        "date": (today - timedelta(days=i)).strftime('%Y-%m-%d'),
                        "total": round(rzye_sh + rzye_sz, 2),
                        "compare": None
                    })
                    
                    if len(data["margin"]) >= 30:
                        break
            except:
                continue
                
        # 计算 compare
        for i in range(1, len(data["margin"])):
            data["margin"][i]["compare"] = round(data["margin"][i]["total"] - data["margin"][i-1]["total"], 2)
            
        print(f"✅ 融资余额: {len(data['margin'])} 条")
    except Exception as e:
        print(f"❌ 融资余额失败: {e}")

    # ====== 3. 大盘主力净流入（北向资金已停发，用主力净流入替代） ======
    try:
        print("正在获取主力净流入数据...")
        # 获取近期大盘资金流向
        flow_df = ak.stock_market_fund_flow()
        
        flow_df['date'] = pd.to_datetime(flow_df['日期']).dt.strftime('%Y-%m-%d')
        records_f = flow_df.sort_values('date', ascending=False).head(30).to_dict('records')
        
        for r in records_f:
            try:
                # 单位通常是亿元，根据实际接口返回调整
                total_net = float(r.get('主力净流入-净额', r.get('今日主力净流入', 0)))
                # 转换为亿元（如果源数据单位是万元或元，需要除以10000或100000000）
                # 这里的接口通常返回的就是亿元
                data["main_fund"].append({
                    "date": r['date'],
                    "total": round(total_net, 2),
                    "compare": None
                })
            except:
                pass
                
        # 计算 compare
        for i in range(1, len(data["main_fund"])):
            data["main_fund"][i]["compare"] = round(data["main_fund"][i]["total"] - data["main_fund"][i-1]["total"], 2)
            
        print(f"✅ 主力净流入: {len(data['main_fund'])} 条")
    except Exception as e:
        print(f"❌ 主力净流入失败: {e}")

    # 保存
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！更新时间: {data['update_time']}")

if __name__ == "__main__":
    fetch_all_data()
