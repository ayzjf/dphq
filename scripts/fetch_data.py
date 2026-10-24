import requests
import re
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

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'http://www.sse.com.cn/'
    }

    today_str = datetime.now().strftime("%Y-%m-%d")

    # ====== 1. 两市成交额（东方财富 push2his K线接口，数据源自交易所） ======
    try:
        print("正在获取成交额数据...")
        # 上证指数 secid=1.000001, 深证成指 secid=0.399001
        url_sh = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f57&ut=bd1d9ddb04089700cf9c27f6f7426281&klt=101&fqt=1&lmt=35"
        url_sz = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.399001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f57&ut=bd1d9ddb04089700cf9c27f6f7426281&klt=101&fqt=1&lmt=35"
        
        res_sh = requests.get(url_sh, headers=headers, timeout=15)
        res_sz = requests.get(url_sz, headers=headers, timeout=15)
        
        data_sh = res_sh.json().get('data', {}).get('klines', [])
        data_sz = res_sz.json().get('data', {}).get('klines', [])
        
        # klines格式: ["2025-10-24,开,收,高,低,量,额,振幅,涨,涨额,换手"]
        # f57是成交额(单位：元)
        sz_dict = {}
        for item in data_sz:
            parts = item.split(',')
            if len(parts) >= 7:
                sz_dict[parts[0]] = float(parts[6])  # date -> amount
        
        sz_total = 0.0
        for item in data_sh:
            parts = item.split(',')
            if len(parts) >= 7:
                date_str = parts[0]
                sh_amt = float(parts[6]) / 1e8  # 转为亿元
                sz_amt = sz_dict.get(date_str, 0) / 1e8
                total = round(sh_amt + sz_amt, 2)
                sz_total += sz_amt
                
                data["turnover"].append({
                    "date": date_str,
                    "sh_amount": round(sh_amt, 2),
                    "sz_amount": round(sz_amt, 2),
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

    # ====== 2. 融资余额（从上交所+深交所官网逐日抓取） ======
    try:
        print("正在获取融资余额数据（交易所官网）...")
        margin_dict = {}  # date -> total
        
        for i in range(35):  # 往前推35天
            target_date = datetime.now() - timedelta(days=i)
            date_ymd = target_date.strftime("%Y%m%d")
            date_ymd_str = target_date.strftime("%Y-%m-%d")
            
            sse_amt = None
            szse_amt = None
            
            # 上交所官网HTML抓取
            try:
                url_sse = f"http://www.sse.com.cn/market/othersdata/margin/detail/index.shtml?marginDate={date_ymd}"
                res_sse = requests.get(url_sse, headers=headers, timeout=10)
                html = res_sse.text
                # 匹配融资余额(元)那一列的数字
                # 表格格式: <td>1,319,482,471,088</td>
                pattern = r'<td>([\d,]+)</td>\s*<td>[\d,]+</td>\s*<td>[\d,]+</td>\s*<td>([\d,]+)</td>'
                match = re.search(pattern, html)
                if match:
                    rzye_str = match.group(1).replace(',', '')
                    sse_amt = float(rzye_str) / 1e8
                    print(f"  上交所 {date_ymd_str}: 融资余额={sse_amt:.2f}亿")
            except Exception as e:
                pass
            
            time.sleep(1.5)  # 延时，避免被交易所封IP
            
            # 深交所JSON API抓取
            try:
                url_szse = f"https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1837&TABKEY=tab1&txtDate={date_ymd_str}"
                res_szse = requests.get(url_szse, headers=headers, timeout=10)
                result = res_szse.json()
                if result and len(result) > 0:
                    sz_data = result[0].get('data', [])
                    if sz_data and len(sz_data) > 0:
                        row = sz_data[0]
                        # 深交所返回的融资余额单位是亿元
                        rzye = row.get('rzye', row.get('RZYE', 0))
                        if rzye:
                            szse_amt = float(rzye)
                            print(f"  深交所 {date_ymd_str}: 融资余额={szse_amt:.2f}亿")
            except Exception as e:
                pass
            
            # 合并两市数据
            if sse_amt is not None or szse_amt is not None:
                total_margin = 0.0
                if sse_amt is not None:
                    total_margin += sse_amt
                if szse_amt is not None:
                    total_margin += szse_amt
                
                margin_dict[date_ymd_str] = round(total_margin, 2)
            
            time.sleep(1.5)  # 每次请求间隔
        
        # 转为列表（按日期降序）
        sorted_dates = sorted(margin_dict.keys(), reverse=True)
        for d in sorted_dates[:30]:
            data["margin"].append({
                "date": d,
                "total": margin_dict[d],
                "compare": None
            })
        
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

    # ====== 3. 大盘主力资金流向 ======
    try:
        print("正在获取主力资金数据...")
        # 上证指数资金流向
        url_fund = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?secid=1.000001&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65&ut=b2884a393a59ad64002292a3e90d46a5&klt=101&fqt=1&lmt=30"
        
        res_fund = requests.get(url_fund, headers=headers, timeout=15)
        result = res_fund.json()
        klines = result.get('data', {}).get('klines', [])
        
        for line in klines[:30]:
            parts = line.split(',')
            if len(parts) >= 3:
                date_str = parts[0]
                try:
                    # 主力净流入 = 超大单净流入 + 大单净流入（单位：元）
                    # f62=主力净流入(元)
                    main_net = float(parts[1]) / 1e8
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
        
        print(f"✅ 主力资金: {len(data['main_fund'])} 条")
    except Exception as e:
        print(f"❌ 主力资金失败: {e}")

    # 保存
    with open('data/market_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！更新时间: {data['update_time']}")
    print(f"   成交额: {len(data['turnover'])} 条")
    print(f"   融资余额: {len(data['margin'])} 条")
    print(f"   主力资金: {len(data['main_fund'])} 条")

if __name__ == "__main__":
    fetch_all_data()
