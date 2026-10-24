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

    # ====== 1. 两市成交额（新浪财经K线接口） ======
    try:
        print("正在获取成交额数据（新浪）...")
        # 新浪历史K线接口（240分钟=日线，30条）
        url_sh = "https://stock.finance.sina.com.cn/his/api/jsonp.php/var%20sh_history=/ChinaStockService.getHistoryKLine?symbol=sh000001&scale=240&datalen=30"
        url_sz = "https://stock.finance.sina.com.cn/his/api/jsonp.php/var%20sz_history=/ChinaStockService.getHistoryKLine?symbol=sz399001&scale=240&datalen=30"
        
        res_sh = requests.get(url_sh, timeout=10)
        res_sz = requests.get(url_sz, timeout=10)
        
        # 解析 JSONP: var sh_history=[{"date":"2025-10-24","open":...,"high":...,"low":...,"close":...,"volume":...},...]
        text_sh = res_sh.text
        match_sh = re.search(r'\[(.*?)\]', text_sh, re.DOTALL)
        sh_list = json.loads("[" + match_sh.group(1) + "]") if match_sh else []
        
        text_sz = res_sz.text
        match_sz = re.search(r'\[(.*?)\]', text_sz, re.DOTALL)
        sz_list = json.loads("[" + match_sz.group(1) + "]") if match_sz else []
        
        # 新浪 volume 字段是成交额（单位：股/手，实际是金额元）
        # 实际字段名可能是 amount 或 volume
        sz_dict = {}
        for item in sz_list:
            date_str = item.get('date', item.get('day', ''))
            amt = float(item.get('amount', item.get('volume', 0)))
            sz_dict[date_str] = amt
        
        for item in sh_list:
            date_str = item.get('date', item.get('day', ''))
            sh_amt = float(item.get('amount', item.get('volume', 0))) / 1e8
            sz_amt = sz_dict.get(date_str, 0) / 1e8
            total = round(sh_amt + sz_amt, 2)
            
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

    # ====== 2. 融资余额（同花顺数据中心） ======
    try:
        print("正在获取融资余额数据（同花顺）...")
        # 同花顺融资融券汇总页
        url = "http://data.10jqka.com.cn/market/rzrq/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get(url, headers=headers, timeout=15)
        html = res.text
        
        # 用正则提取表格中的日期和融资余额
        # 表格行格式类似: <tr><td>2025-10-24</td><td>xxx</td>...<td>融资余额</td>...</tr>
        # 同花顺页面用 <tbody> 包裹，每行 <tr>
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 2:
                # 第一列通常是日期
                date_text = re.sub(r'<[^>]+>', '', cells[0]).strip()
                # 融资余额列 - 根据同花顺实际列位置调整
                # 同花顺融资融券页: 日期|融资金额|融资净买入|融资余额|融券余量|融券余额|融资融券余额
                # 融资余额大约在第4列(索引3)
                if len(cells) >= 4:
                    rzye_text = re.sub(r'<[^>]+>', '', cells[3]).strip()
                    rzye_text = rzye_text.replace(',', '').replace(' ', '')
                    try:
                        rzye = float(rzye_text)
                        # 同花顺单位是亿元
                        data["margin"].append({
                            "date": date_text,
                            "total": rzye,
                            "compare": None
                        })
                    except ValueError:
                        pass
        
        if not data["margin"]:
            # 备用方案：尝试东方财富融资融券汇总HTML页
            print("  同花顺未抓到，尝试东方财富...")
            url_em = "https://data.eastmoney.com/rzrq/"
            res_em = requests.get(url_em, headers=headers, timeout=15)
            html_em = res_em.text
            # 东方财富页面有最近20天汇总
            # 查找日期和融资余额的 pattern
            pattern = re.compile(r'(\d{4}-\d{2}-\d{2}).*?融资余额.*?([\d,]+\.?\d*)')
            
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

    # ====== 3. 大盘主力资金（新浪财经资金流向） ======
    try:
        print("正在获取主力资金数据（新浪）...")
        # 新浪大盘资金流向接口
        url = "https://vip.stock.finance.sina.com.cn/q/go.php/vMoneyFlows/history/p/stockid/000001.phtml"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get(url, headers=headers, timeout=15)
        html = res.text
        
        # 新浪资金流向页面表格
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        count = 0
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row)
            if len(cells) >= 3:
                date_text = re.sub(r'<[^>]+>', '', cells[0]).strip()
                # 主力净流入列
                net_text = re.sub(r'<[^>]+>', '', cells[2]).strip()
                net_text = net_text.replace(',', '').replace(' ', '')
                try:
                    net = float(net_text)
                    data["main_fund"].append({
                        "date": date_text,
                        "total": round(net, 2),
                        "compare": None
                    })
                    count += 1
                except ValueError:
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
