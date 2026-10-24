import requests
import json
import re
from datetime import datetime

def fetch_all_data():
    data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "turnover": [],
        "margin": [],
        "main_fund": []
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # ====== 1. 两市成交额（抓新浪财经指数历史数据） ======
    try:
        print("正在获取上证指数成交额...")
        # 新浪历史数据接口
        url_sh = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20sh_history=/CN_MarketDataService.getKLineData?symbol=sh000001&scale=240&datalen=30"
        url_sz = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20sz_history=/CN_MarketDataService.getKLineData?symbol=sz399001&scale=240&datalen=30"
        
        res_sh = requests.get(url_sh, headers=headers, timeout=10)
        res_sz = requests.get(url_sz, headers=headers, timeout=10)
        
        # 解析 JSONP 格式：var sh_history=[{...},{...}]
        text_sh = res_sh.text
        match_sh = re.search(r'\[.*\]', text_sh)
        sh_list = json.loads(match_sh.group(0)) if match_sh else []
        
        text_sz = res_sz.text
        match_sz = re.search(r'\[.*\]', text_sz)
        sz_list = json.loads(match_sz.group(0)) if match_sz else []
        
        # 合并同一天数据
        sz_dict = {item['day']: item for item in sz_list}
        
        for item in sh_list:
            date_str = item['day']  # 格式: "2025-10-24"
            sz_item = sz_dict.get(date_str)
            if sz_item:
                sh_amt = float(item.get('volume', 0))  # 新浪单位：股/手，实际是成交额元
                sz_amt = float(sz_item.get('volume', 0))
                # 新浪volume实际是成交金额(元)
                sh_yi = round(sh_amt / 1e8, 2)
                sz_yi = round(sz_amt / 1e8, 2)
                total = round(sh_yi + sz_yi, 2)
                
                data["turnover"].append({
                    "date": date_str,
                    "sh_amount": sh_yi,
                    "sz_amount": sz_yi,
                    "total": total,
                    "compare": None
                })
        
        # 计算 compare
        for i in range(1, len(data["turnover"])):
            try:
                data["turnover"][i]["compare"] = round(
                    data["turnover"][i]["total"] - data["turnover"][i-1]["total"], 2
                )
            except:
                pass
        
        print(f"✅ 成交额: {len(data['turnover'])} 条")
    except Exception as e:
        print(f"❌ 成交额失败: {e}")

    # ====== 2. 融资余额（抓同花顺数据中心） ======
    try:
        print("正在获取融资余额数据...")
        # 同花顺融资融券数据
        url_margin = "http://data.10jqka.com.cn/market/rzrq/"
        res = requests.get(url_margin, headers=headers, timeout=10)
        
        # 用正则提取表格数据
        # 这里先尝试更简单的方案：抓取东方财富融资融券历史
        url_em = "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_HSGT&columns=ALL&filter=(DATE%3E%3D%272025-07-01%27)&sortColumns=DATE&sortTypes=-1&pageSize=30"
        
        res_em = requests.get(url_em, headers=headers, timeout=10)
        result_em = res_em.json()
        
        records = result_em.get('result', {}).get('data', [])
        for r in records:
            try:
                date_str = r.get('DATE', '')
                if date_str:
                    date_str = date_str[:10]  # 取日期部分
                rzye = float(r.get('RZYE', 0)) / 1e8  # 融资余额，单位元→亿元
                rzye_sz = float(r.get('RZYE_SZ', 0)) / 1e8
                total = round(rzye + rzye_sz, 2)
                
                data["margin"].append({
                    "date": date_str,
                    "total": total,
                    "compare": None
                })
            except:
                pass
        
        # 计算 compare
        for i in range(1, len(data["margin"])):
            try:
                data["margin"][i]["compare"] = round(
                    data["margin"][i]["total"] - data["margin"][i-1]["total"], 2
                )
            except:
                pass
        
        print(f"✅ 融资余额: {len(data['margin'])} 条")
    except Exception as e:
        print(f"❌ 融资余额失败: {e}")

    # ====== 3. 大盘资金流向（抓东方财富数据中心API） ======
    try:
        print("正在获取大盘资金流向数据...")
        # 东方财富大盘资金流向
        url_fund = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?secid=1.000001&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65&ut=b2884a393a59ad64002292a3e90d46a5&klt=101&fqt=1"
        
        res_fund = requests.get(url_fund, headers=headers, timeout=10)
        result_fund = res_fund.json()
        
        klines = result_fund.get('data', {}).get('klines', [])
        for line in klines[:30]:
            # 格式: "2025-10-24,主力净流入,小单净流入,中单净流入,大单净流入,超大单净流入,..."
            parts = line.split(',')
            if len(parts) >= 3:
                date_str = parts[0]
                try:
                    # 主力净流入 = 超大单 + 大单（单位：元）
                    main_net = float(parts[1]) / 1e8  # 转为亿元
                    data["main_fund"].append({
                        "date": date_str,
                        "total": round(main_net, 2),
                        "compare": None
                    })
                except:
                    pass
        
        # 计算 compare
        for i in range(1, len(data["main_fund"])):
            try:
                data["main_fund"][i]["compare"] = round(
                    data["main_fund"][i]["total"] - data["main_fund"][i-1]["total"], 2
                )
            except:
                pass
        
        print(f"✅ 资金流向: {len(data['main_fund'])} 条")
    except Exception as e:
        print(f"❌ 资金流向失败: {e}")

    # 保存
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！更新时间: {data['update_time']}")
    print(f"   成交额: {len(data['turnover'])} 条 | 融资余额: {len(data['margin'])} 条 | 资金流向: {len(data['main_fund'])} 条")

if __name__ == "__main__":
    fetch_all_data()
