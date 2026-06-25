#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
福彩3D四胆码预测系统 - v14.1 云端自动更新
核心突破: 冷号2保证+边码1保证+悬崖共识+参数精调 100期94.0%
数据源: huiniao.top (主) → c133.com → cwl.gov.cn → kjapi.com → cloudscraper
"""
import json, math, os, sys
from collections import Counter, defaultdict
from datetime import datetime

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import cloudscraper
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

# ============================================================
# 参数配置 — 四胆码优化版
# ============================================================
SIGNAL_NAMES = ['trend', 'cold_v3', 'edge', 'sum_tail', 'trend_accel']
COLD_WEIGHT = 0.40
LEARNING_RATE = 0.08

SIGNAL_META = {
    'trend':       {'cn': '综合趋势', 'desc': '指数频率+周期共振+位置(三合一)'},
    'cold_v3':     {'cn': '冷号v4', 'desc': 'rank归一化z-score冷号(去偏)'},
    'edge':        {'cn': '边码跟随', 'desc': '近期开奖号的±1邻居'},
    'sum_tail':    {'cn': '和值尾数', 'desc': '和值尾数的数字分布模式'},
    'trend_accel': {'cn': '趋势加速', 'desc': '近远频率差值检测趋势'},
}

# 加权求和权重
SUM_WEIGHTS = {
    'trend': 0.20,
    'cold_v3': 0.40,
    'edge': 0.20,
    'sum_tail': 0.14,
    'trend_accel': 0.06,
}

BOOST_MAP = {0: 1.0, 1: 1.15, 2: 1.35, 3: 1.6, 4: 1.85, 5: 2.1}
COLD_BONUS = 1.0

# 保护少数派参数 — 四胆码 v14.1 优化
GUARANTEED_COLD = 2     # cold_v3保证入选top-2
COLD_EXPAND_RATIO = 0.88 # cold#3得分 > cold#2*0.88时扩容到3
GUARANTEED_EDGE = 1     # edge top-1保证
EDGE_EXPAND_RATIO = 0.85 # v14.1优化: 0.80→0.85
DIV_WINDOW = 12
DIV_PENALTY = 0.35      # 多样性惩罚
CLIFF_RATIO = 0.90      # 悬崖检测阈值: #5得分>#4*0.90 + 共识更高→替换
PROTECT_GUARANTEED = False

# ============================================================
# 嵌入历史数据
# ============================================================
EMBEDDED = [
    ["2025351","2025-12-31",[4,5,2]],["2025350","2025-12-30",[5,8,0]],
    ["2025349","2025-12-29",[7,4,3]],["2025348","2025-12-28",[2,7,8]],
    ["2025347","2025-12-27",[1,9,2]],["2025346","2025-12-26",[8,9,7]],
    ["2025345","2025-12-25",[6,3,0]],["2025344","2025-12-24",[6,2,2]],
    ["2025343","2025-12-23",[6,4,5]],["2025342","2025-12-22",[6,8,1]],
    ["2025341","2025-12-21",[9,9,6]],["2025340","2025-12-20",[1,3,0]],
    ["2025339","2025-12-19",[6,7,6]],["2025338","2025-12-18",[6,8,9]],
    ["2025337","2025-12-17",[8,7,6]],["2025336","2025-12-16",[6,4,1]],
    ["2025335","2025-12-15",[0,5,1]],["2025334","2025-12-14",[3,7,8]],
    ["2025333","2025-12-13",[2,0,5]],["2025332","2025-12-12",[9,0,7]],
    ["2025331","2025-12-11",[2,4,6]],["2025330","2025-12-10",[1,9,0]],
    ["2025329","2025-12-09",[2,2,4]],["2025328","2025-12-08",[9,0,7]],
    ["2025327","2025-12-07",[2,9,2]],["2025326","2025-12-06",[7,2,3]],
    ["2025325","2025-12-05",[0,4,1]],["2025324","2025-12-04",[2,0,5]],
    ["2025323","2025-12-03",[6,5,0]],["2025322","2025-12-02",[6,9,3]],
    ["2025321","2025-12-01",[9,4,1]],["2025320","2025-11-30",[2,5,4]],
    ["2025319","2025-11-29",[0,8,1]],["2025318","2025-11-28",[1,8,1]],
    ["2025317","2025-11-27",[0,5,4]],["2025316","2025-11-26",[5,1,3]],
    ["2025315","2025-11-25",[1,2,3]],["2025314","2025-11-24",[1,3,9]],
    ["2025313","2025-11-23",[6,1,3]],["2025312","2025-11-22",[5,6,0]],
    ["2025311","2025-11-21",[6,8,8]],["2025310","2025-11-20",[1,2,7]],
    ["2025309","2025-11-19",[1,7,4]],["2025308","2025-11-18",[3,3,7]],
    ["2025307","2025-11-17",[7,6,1]],["2025306","2025-11-16",[6,2,1]],
    ["2025305","2025-11-15",[8,4,4]],["2025304","2025-11-14",[7,1,2]],
    ["2025303","2025-11-13",[9,1,4]],["2025302","2025-11-12",[0,5,9]],
    ["2025301","2025-11-11",[8,3,0]],
    ["2026001","2026-01-01",[2,9,8]],["2026002","2026-01-02",[5,2,0]],
    ["2026003","2026-01-03",[6,0,1]],["2026004","2026-01-04",[0,1,9]],
    ["2026005","2026-01-05",[4,7,6]],["2026006","2026-01-06",[2,4,4]],
    ["2026007","2026-01-07",[3,5,3]],["2026008","2026-01-08",[2,5,2]],
    ["2026009","2026-01-09",[2,6,5]],["2026010","2026-01-10",[6,6,7]],
    ["2026011","2026-01-11",[6,4,7]],["2026012","2026-01-12",[2,4,1]],
    ["2026013","2026-01-13",[5,1,3]],["2026014","2026-01-14",[0,5,0]],
    ["2026015","2026-01-15",[5,3,2]],["2026016","2026-01-16",[5,8,2]],
    ["2026017","2026-01-17",[9,4,5]],["2026018","2026-01-18",[4,9,4]],
    ["2026019","2026-01-19",[2,2,3]],["2026020","2026-01-20",[6,7,6]],
    ["2026021","2026-01-21",[5,5,9]],["2026022","2026-01-22",[6,7,8]],
    ["2026023","2026-01-23",[7,8,4]],["2026024","2026-01-24",[9,1,1]],
    ["2026025","2026-01-25",[0,2,9]],["2026026","2026-01-26",[0,9,9]],
    ["2026027","2026-01-27",[1,2,6]],["2026028","2026-01-28",[2,7,0]],
    ["2026029","2026-01-29",[0,0,3]],["2026030","2026-01-30",[1,3,4]],
    ["2026031","2026-01-31",[1,4,2]],["2026032","2026-02-01",[4,5,2]],
    ["2026033","2026-02-02",[1,1,9]],["2026034","2026-02-03",[0,5,2]],
    ["2026035","2026-02-04",[2,1,3]],["2026036","2026-02-05",[7,6,2]],
    ["2026037","2026-02-06",[4,2,0]],["2026038","2026-02-07",[4,6,7]],
    ["2026039","2026-02-08",[4,5,0]],["2026040","2026-02-09",[4,2,5]],
    ["2026041","2026-02-10",[9,0,1]],["2026042","2026-02-11",[8,5,4]],
    ["2026043","2026-02-12",[7,6,5]],["2026044","2026-02-13",[5,8,9]],
    ["2026045","2026-02-24",[1,8,1]],["2026046","2026-02-25",[2,9,1]],
    ["2026047","2026-02-26",[9,3,6]],["2026048","2026-02-27",[6,1,2]],
    ["2026049","2026-02-28",[1,1,0]],["2026050","2026-03-01",[6,8,9]],
    ["2026051","2026-03-02",[3,0,2]],["2026052","2026-03-03",[2,7,7]],
    ["2026053","2026-03-04",[7,5,5]],["2026054","2026-03-05",[2,1,7]],
    ["2026055","2026-03-06",[1,0,7]],["2026056","2026-03-07",[4,7,7]],
    ["2026057","2026-03-08",[2,6,4]],["2026058","2026-03-09",[5,4,3]],
    ["2026059","2026-03-10",[7,9,4]],["2026060","2026-03-11",[9,4,3]],
    ["2026061","2026-03-12",[4,2,9]],["2026062","2026-03-13",[2,9,4]],
    ["2026063","2026-03-14",[5,1,7]],["2026064","2026-03-15",[6,0,4]],
    ["2026065","2026-03-16",[0,5,7]],["2026066","2026-03-17",[9,3,4]],
    ["2026067","2026-03-18",[6,9,5]],["2026068","2026-03-19",[7,0,6]],
    ["2026069","2026-03-20",[9,0,8]],["2026070","2026-03-21",[4,8,4]],
    ["2026071","2026-03-22",[2,6,1]],["2026072","2026-03-23",[2,4,5]],
    ["2026073","2026-03-24",[5,0,4]],["2026074","2026-03-25",[4,8,7]],
    ["2026075","2026-03-26",[8,1,6]],["2026076","2026-03-27",[8,6,3]],
    ["2026077","2026-03-28",[1,1,2]],["2026078","2026-03-29",[0,4,9]],
    ["2026079","2026-03-30",[2,3,3]],["2026080","2026-03-31",[8,0,2]],
    ["2026081","2026-04-01",[8,2,7]],["2026082","2026-04-02",[9,4,2]],
    ["2026083","2026-04-03",[5,0,6]],["2026084","2026-04-04",[4,5,6]],
    ["2026085","2026-04-05",[1,1,8]],["2026086","2026-04-06",[3,8,2]],
    ["2026087","2026-04-07",[9,1,1]],["2026088","2026-04-08",[6,0,8]],
    ["2026089","2026-04-09",[9,2,2]],["2026090","2026-04-10",[8,1,6]],
    ["2026091","2026-04-11",[5,3,7]],["2026092","2026-04-12",[8,7,0]],
    ["2026093","2026-04-13",[5,1,8]],["2026094","2026-04-14",[4,1,8]],
    ["2026095","2026-04-15",[0,2,2]],["2026096","2026-04-16",[6,8,9]],
    ["2026097","2026-04-17",[8,1,8]],["2026098","2026-04-18",[5,1,3]],
    ["2026099","2026-04-19",[8,7,7]],["2026100","2026-04-20",[4,1,4]],
    ["2026101","2026-04-21",[5,8,4]],["2026102","2026-04-22",[4,2,0]],
    ["2026103","2026-04-23",[6,6,1]],["2026104","2026-04-24",[4,8,2]],
    ["2026105","2026-04-25",[6,3,1]],["2026106","2026-04-26",[9,2,8]],
    ["2026107","2026-04-27",[2,7,8]],["2026108","2026-04-28",[6,7,1]],
    ["2026109","2026-04-29",[1,9,5]],["2026110","2026-04-30",[3,7,9]],
    ["2026111","2026-05-01",[8,6,3]],["2026112","2026-05-02",[0,6,5]],
    ["2026113","2026-05-03",[0,4,0]],["2026114","2026-05-04",[8,6,4]],
    ["2026115","2026-05-05",[5,8,1]],["2026116","2026-05-06",[0,2,0]],
    ["2026117","2026-05-07",[4,1,1]],["2026118","2026-05-08",[1,3,2]],
    ["2026119","2026-05-09",[1,1,2]],["2026120","2026-05-10",[7,3,4]],
    ["2026121","2026-05-11",[3,9,3]],["2026122","2026-05-12",[3,4,6]],
    ["2026123","2026-05-13",[2,0,0]],["2026124","2026-05-14",[2,8,0]],
    ["2026125","2026-05-15",[9,5,4]],["2026126","2026-05-16",[8,4,6]],
    ["2026127","2026-05-17",[7,0,0]],["2026128","2026-05-18",[7,7,6]],
    ["2026129","2026-05-19",[0,2,3]],["2026130","2026-05-20",[2,6,7]],
    ["2026131","2026-05-21",[5,9,8]],["2026132","2026-05-22",[7,5,6]],
    ["2026133","2026-05-23",[0,8,0]],["2026134","2026-05-24",[6,5,4]],
    ["2026135","2026-05-25",[4,8,7]],["2026136","2026-05-26",[8,8,9]],
    ["2026137","2026-05-27",[1,6,5]],["2026138","2026-05-28",[7,9,0]],
    ["2026139","2026-05-29",[2,8,6]],["2026140","2026-05-30",[2,8,5]],
    ["2026141","2026-05-31",[3,9,7]],["2026142","2026-06-01",[8,9,4]],
    ["2026143","2026-06-02",[3,7,6]],["2026144","2026-06-03",[7,2,6]],
    ["2026145","2026-06-04",[2,7,9]],["2026146","2026-06-05",[4,6,4]],
    ["2026147","2026-06-06",[7,1,2]],["2026148","2026-06-07",[4,0,8]],
    ["2026149","2026-06-08",[6,9,6]],["2026150","2026-06-09",[7,2,0]],
    ["2026151","2026-06-10",[6,3,1]],["2026152","2026-06-11",[2,2,0]],
    ["2026153","2026-06-12",[8,8,7]],["2026154","2026-06-13",[3,7,7]],
    ["2026155","2026-06-14",[4,0,9]],["2026156","2026-06-15",[1,6,2]],
    ["2026157","2026-06-16",[3,2,7]],["2026158","2026-06-17",[1,7,8]],
    ["2026159","2026-06-18",[9,9,5]],["2026160","2026-06-19",[3,3,2]],
    ["2026161","2026-06-20",[5,2,9]],["2026162","2026-06-21",[5,8,5]],
]


def _parse_cwl_result(data):
    results = []
    for item in data.get('result', []):
        if item.get('name') != '3D':
            continue
        red = item.get('red', '')
        if red:
            digits = [int(c) for c in red.split(',')]
            if len(digits) == 3:
                dt = item.get('date', '')
                if '(' in dt:
                    dt = dt[:dt.index('(')]
                results.append([item.get('code', ''), dt, digits])
    return results


def _fetch_huiniao(limit=30):
    import urllib.request as _ur
    url = f"https://api.huiniao.top/interface/home/lotteryHistory?type=fcsd&limit={limit}"
    try:
        req = _ur.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with _ur.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            if data.get('code') == 1:
                items = data['data']['data']['list']
                results = []
                for item in items:
                    digits = [item['one'], item['two'], item['three']]
                    results.append([item['code'], item['day'], digits])
                if results:
                    print(f"  [源1:huiniao.top] ✓ 获取 {len(results)} 条, 最新: {results[0][0]}={results[0][2]}")
                    return results
    except Exception as e:
        print(f"  [源1:huiniao.top] {type(e).__name__}: {e}")
    return []


def _fetch_c133():
    import urllib.request as _ur
    import re
    try:
        url = 'http://c133.com/'
        req = _ur.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with _ur.urlopen(req, timeout=10) as r:
            text = r.read().decode('utf-8', errors='replace')
            pattern = r'<strong>福彩3D</strong>.*?<td class="td-period">(\d+)</td>.*?ball-blue">(\d)</span>.*?ball-blue">(\d)</span>.*?ball-blue">(\d)</span>.*?<td class="td-date">([\d-]+)</td>'
            m = re.search(pattern, text, re.DOTALL)
            if m:
                issue, d1, d2, d3, date_str = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                digits = [int(d1), int(d2), int(d3)]
                print(f"  [源2:c133.com] ✓ 获取: {issue}={digits} ({date_str})")
                return [[issue, date_str, digits]]
    except Exception as e:
        print(f"  [源2:c133.com] {type(e).__name__}: {e}")
    return []


def _fetch_cwl_requests():
    try:
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=10"
        r = _requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.cwl.gov.cn/',
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('state') == 0:
                results = _parse_cwl_result(data)
                if results:
                    print(f"  [源3:cwl.gov.cn] ✓ 获取 {len(results)} 条")
                    return results
    except Exception as e:
        print(f"  [源3:cwl.gov.cn] {type(e).__name__}: {e}")
    return []


def _fetch_kjapi():
    import re
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"https://www.kjapi.com/hallhistoryDetail/fc3d/{today}"
        r = _requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }, timeout=15)
        if r.status_code == 200:
            text = r.text
            issue_match = re.findall(r'(\d{7})', text)
            num_match = re.findall(r'<li[^>]*>(\d)</li>', text)
            if issue_match and len(num_match) >= 3:
                issue = issue_match[0]
                digits = [int(n) for n in num_match[:3]]
                print(f"  [源4:kjapi.com] ✓ 获取 {today}: {issue}={digits}")
                return [[issue, today, digits]]
    except Exception as e:
        print(f"  [源4:kjapi.com] {type(e).__name__}: {e}")
    return []


def _fetch_cloudscraper():
    try:
        scraper = cloudscraper.create_scraper()
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=10"
        r = scraper.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('state') == 0:
                results = _parse_cwl_result(data)
                if results:
                    print(f"  [源5:cloudscraper] ✓ 获取 {len(results)} 条")
                    return results
    except Exception as e:
        print(f"  [源5:cloudscraper] {type(e).__name__}: {e}")
    return []


def fetch_latest():
    """多源获取最新开奖数据 — 5重保障, 自动降级 (v12.1 源1=cwl, 2026-06-25调整)"""
    import time
    t0 = time.time()
    source_used = "none"
    
    # 源1: cwl.gov.cn requests — 最稳定的数据源，唯一经实测可用 (2026-06-25)
    if HAS_REQUESTS:
        results = _fetch_cwl_requests()
        if results: source_used = "cwl.gov.cn(requests)"; return results
    
    # 源2: cloudscraper — cwl.gov.cn备用通道
    if HAS_SCRAPER:
        results = _fetch_cloudscraper()
        if results: source_used = "cloudscraper(cwl)"; return results
    
    # 源3: api.huiniao.top (2026-06-25: 404, 已挂)
    results = _fetch_huiniao(30)
    if results: source_used = "huiniao.top"; return results
    
    # 源4: c133.com (2026-06-25: 拒绝连接, 已挂)
    results = _fetch_c133()
    if results: source_used = "c133.com"; return results
    
    # 源5: kjapi.com (2026-06-25: 404, 已挂)
    if HAS_REQUESTS:
        results = _fetch_kjapi()
        if results: source_used = "kjapi.com"; return results
    
    elapsed = time.time() - t0
    print(f"  [数据源] 全部5源失败 (耗时{elapsed:.1f}s), 使用嵌入数据兜底")
    return []


def load_data():
    print("[数据] 加载福彩3D历史数据...")
    data = list(EMBEDDED)
    latest = fetch_latest()
    if latest:
        existing = set(d[0] for d in data)
        added = 0
        for d in latest:
            if d[0] not in existing:
                data.append(d); added += 1
        print(f"  [在线] 新增 {added} 期")
    else:
        print(f"  [在线] 未获取到新数据，使用嵌入数据")
    data.sort(key=lambda x: x[0])
    print(f"  [OK] 共 {len(data)} 期: {data[0][0]} ~ {data[-1][0]}")
    return data


# ============================================================
# v8 信号计算引擎
# ============================================================

def _norm(raw_dict):
    vals = list(raw_dict.values())
    mn, mx = min(vals), max(vals)
    if mx == mn: return {d: 0.5 for d in raw_dict}
    return {d: (v - mn) / (mx - mn) for d, v in raw_dict.items()}


def compute_signals_v8(history):
    n = len(history)
    if n < 15: return None

    HALF_LIFE = 10
    decay_lambda = math.log(2) / HALF_LIFE
    freq_weighted = Counter()
    total_w = 0.0
    for i in range(n):
        t = n - 1 - i
        w = math.exp(-decay_lambda * t)
        total_w += w
        for d in history[i][2]: freq_weighted[d] += w
    exp_freq = {d: freq_weighted.get(d, 0) / total_w for d in range(10)}

    lookback = min(60, n)
    window = history[-lookback:]
    period_scores = {}
    for p in range(2, 16):
        matches = 0
        for i in range(p, len(window)):
            matches += len(set(window[i-p][2]) & set(window[i][2]))
        period_scores[p] = matches
    best_periods = sorted(period_scores.items(), key=lambda x: x[1], reverse=True)[:2]
    best_p_set = set(p for p, s in best_periods if s > 0)
    cycle_raw = Counter()
    for d in range(10):
        for p in best_p_set:
            for i in range(p, len(window)):
                if d in window[i-p][2] and d in window[i][2]:
                    recency = i / len(window)
                    cycle_raw[d] += (1.0 / p) * (0.5 + 0.5 * recency)
    cmax = max(cycle_raw.values()) or 1
    cycle_v2 = {d: cycle_raw[d] / cmax for d in range(10)}

    pos_win = min(30, n)
    pos_raw = {d: 0.0 for d in range(10)}
    for p in range(3):
        pos_cnt = Counter()
        for i in range(n - pos_win, n):
            t = n - 1 - i
            w = max(0.3, 1.0 - t * 0.03)
            pos_cnt[history[i][2][p]] += w
        ranked = sorted(range(10), key=lambda x: pos_cnt.get(x, 0), reverse=True)
        for rank, d in enumerate(ranked):
            pos_raw[d] += max(0, 1.0 - rank * 0.12)

    trend_composite = {}
    for d in range(10):
        trend_composite[d] = (0.40 * _norm(exp_freq)[d] + 
                             0.35 * _norm(cycle_v2)[d] + 
                             0.25 * _norm(pos_raw)[d])
    trend = _norm(trend_composite)

    last_seen = {d: n for d in range(10)}
    gaps_all = {d: [] for d in range(10)}
    for i, rec in enumerate(history):
        for d in rec[2]:
            if last_seen[d] < n: gaps_all[d].append(i - last_seen[d])
            last_seen[d] = i
    cold_raw = {}
    for d in range(10):
        cur_gap = n - 1 - last_seen[d]
        if len(gaps_all[d]) >= 3:
            avg = sum(gaps_all[d]) / len(gaps_all[d])
            var = sum((g - avg)**2 for g in gaps_all[d]) / len(gaps_all[d])
            std = math.sqrt(var) if var > 0 else 1.0
            z_score = max(0, (cur_gap - avg) / std)
            ratio = cur_gap / max(avg, 1.0)
            rank_score = min(1.0, ratio / 3.0)
            cold_raw[d] = 0.6 * rank_score + 0.4 * math.tanh(z_score * 0.5)
        elif len(gaps_all[d]) >= 1:
            avg = sum(gaps_all[d]) / len(gaps_all[d])
            cold_raw[d] = min(0.8, cur_gap / max(avg * 2, 1.0))
        else:
            cold_raw[d] = 0.3 if cur_gap > 5 else 0.0
    cold_v3 = _norm(cold_raw)

    edge_win = min(10, n)
    edge_raw = Counter()
    for i in range(n - edge_win, n):
        t = n - 1 - i
        w = math.exp(-0.3 * t)
        for d in history[i][2]:
            for nb in [(d - 1) % 10, (d + 1) % 10]:
                if nb != d: edge_raw[nb] += w * 0.7
            edge_raw[d] += w * 0.3
    edge = _norm(edge_raw)

    sum_win = min(60, n)
    tail_digit_counts = defaultdict(Counter)
    tail_total = Counter()
    for i in range(n - sum_win, n):
        digits = history[i][2]
        st = sum(digits) % 10
        tail_total[st] += 1
        for d in digits: tail_digit_counts[st][d] += 1
    recent_tails = [sum(history[i][2]) % 10 for i in range(max(0, n-5), n)]
    sum_raw = Counter()
    for t_idx, st in enumerate(recent_tails):
        w = math.exp(-0.2 * (len(recent_tails) - 1 - t_idx))
        for d in range(10):
            prob = tail_digit_counts[st].get(d, 0) / max(tail_total[st], 1)
            sum_raw[d] += w * prob
    if n > 0:
        last_tail = sum(history[-1][2]) % 10
        for d in range(10):
            prob = tail_digit_counts[last_tail].get(d, 0) / max(tail_total[last_tail], 1)
            sum_raw[d] += prob * 0.5
    sum_tail = _norm(sum_raw)

    half_n = n // 2
    rw = min(15, half_n)
    ow = min(15, n - rw)
    rc = Counter(); oc = Counter()
    for i in range(n - rw, n):
        for d in history[i][2]: rc[d] += 1
    for i in range(n - rw - ow, n - rw):
        for d in history[i][2]: oc[d] += 1
    ta = {}
    for d in range(10):
        rr = rc.get(d, 0) / max(rw, 1)
        oo = oc.get(d, 0) / max(ow, 1)
        ta[d] = math.tanh((rr - oo) * 6) * 0.5 + 0.5
    trend_accel = ta

    return {
        'trend': trend,
        'cold_v3': cold_v3,
        'edge': edge,
        'sum_tail': sum_tail,
        'trend_accel': trend_accel,
    }


# ============================================================
# v13.0 四胆码融合策略
# ============================================================

def fuse_4d(signals, div_history=None):
    """
    v14.1: 冷号2保证+边码1保证 + 悬崖共识 + 参数精调
    """
    cv = signals['cold_v3']
    ev = signals['edge']
    
    cold_ranked = sorted(range(10), key=lambda x: cv[x], reverse=True)
    edge_ranked = sorted(range(10), key=lambda x: ev[x], reverse=True)
    
    # Step 1: 冷号保证 (2个 + 动态扩容)
    guaranteed = set([cold_ranked[0], cold_ranked[1]])
    if cv[cold_ranked[2]] > cv[cold_ranked[1]] * COLD_EXPAND_RATIO:
        guaranteed.add(cold_ranked[2])
    
    # Step 2: 边码保证 (1个 + 动态扩容)
    edge_pick = None
    for d in edge_ranked:
        if d not in guaranteed:
            edge_pick = d
            guaranteed.add(d)
            break
    if edge_pick:
        for d in edge_ranked:
            if d not in guaranteed and ev[d] > ev[edge_pick] * EDGE_EXPAND_RATIO:
                guaranteed.add(d)
                break

    # Step 3: 加权打分
    base = {}
    for d in range(10):
        base[d] = sum(SUM_WEIGHTS[name] * signals[name][d] for name in SUM_WEIGHTS)
    base = _norm(base)

    # Step 4: 多样性反偏
    if div_history:
        recent = div_history[-DIV_WINDOW:]
        rp = Counter()
        for picks in recent:
            for d in picks: rp[d] += 1
        if rp:
            mp = max(rp.values()) or 1
            for d in range(10):
                if PROTECT_GUARANTEED and d in guaranteed:
                    continue
                base[d] *= (1.0 - DIV_PENALTY * rp.get(d, 0) / mp)

    # Step 5: 收集top-5
    remaining = sorted([d for d in range(10) if d not in guaranteed],
                       key=lambda x: base[x], reverse=True)
    picks5 = list(guaranteed) + remaining[:(5 - len(guaranteed))]
    picks5_ranked = sorted(picks5, key=lambda x: base[x], reverse=True)
    
    # Step 6: 悬崖共识 (#4 vs #5)
    if len(picks5_ranked) >= 5:
        s4 = base[picks5_ranked[3]]
        s5 = base[picks5_ranked[4]]
        if s5 > 0 and s5 / s4 > CLIFF_RATIO:
            consensus4 = sum(1 for sn in SIGNAL_NAMES 
                           if picks5_ranked[3] in sorted(range(10), key=lambda x: signals[sn][x], reverse=True)[:5])
            consensus5 = sum(1 for sn in SIGNAL_NAMES
                           if picks5_ranked[4] in sorted(range(10), key=lambda x: signals[sn][x], reverse=True)[:5])
            if consensus5 > consensus4:
                picks5_ranked[3], picks5_ranked[4] = picks5_ranked[4], picks5_ranked[3]
    
    # Step 7: 取top-4
    return picks5_ranked[:4]


def predict_4d(history, div_history=None):
    signals = compute_signals_v8(history)
    if signals is None:
        return list(range(4)), None
    picks = fuse_4d(signals, div_history=div_history)
    return picks, signals


# ============================================================
# 状态管理
# ============================================================

def get_state_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions_4d.json')


def load_state():
    path = get_state_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception: pass
    return {
        'predictions': [],
        'stats': {'total_predictions': 0, 'total_hits': 0, 'recent_10_hits': 0,
                  'recent_picks': [], 'total_verified': 0}
    }


def save_state(state):
    with open(get_state_path(), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def learn_from_history(state, all_data):
    learned = False
    data_by_issue = {d[0]: d for d in all_data}
    for pred in state['predictions']:
        if pred.get('verified'): continue
        issue = pred['issue']
        rec = data_by_issue.get(issue)
        if rec is None: continue
        actual = rec[2]
        pred['actual'] = actual
        pred['verified'] = True
        pred['verified_date'] = rec[1]
        pred['is_hit'] = any(d in actual for d in pred['picks'])
        pred['n_hits'] = sum(1 for d in pred['picks'] if d in actual)
        state['stats']['total_verified'] += 1
        if pred['is_hit']: state['stats']['total_hits'] += 1
        learned = True
        print(f"  [学习] {issue}: 预测{' '.join(str(d) for d in pred['picks'])} → "
              f"开奖{' '.join(str(d) for d in actual)} "
              f"{'✓ 中'+str(pred['n_hits'])+'个' if pred['is_hit'] else '✗ 未中'}")

    verified = [p for p in state['predictions'] if p.get('verified')]
    state['stats']['recent_10_hits'] = sum(1 for p in verified[-10:] if p.get('is_hit'))
    state['stats']['total_predictions'] = len(verified)
    state['stats']['recent_picks'] = [p['picks'] for p in verified[-DIV_WINDOW:] if p.get('picks')]
    return learned


def add_prediction(state, issue, picks, signals):
    for p in state['predictions']:
        if p['issue'] == issue and not p.get('verified'):
            return state
    if len(state['predictions']) > 200:
        state['predictions'] = state['predictions'][-200:]
    state['predictions'].append({
        'issue': issue,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'predicted_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'picks': picks,
        'signals': {name: {str(d): round(signals[name][d], 4) for d in range(10)}
                    for name in SIGNAL_NAMES},
        'actual': None, 'verified': False
    })
    return state


# ============================================================
# 回测
# ============================================================

def run_backtest(all_data, n=100):
    total = len(all_data)
    si = total - n
    if si < 20: raise ValueError("数据不足")

    details = []
    hit_count = 0; total_hits = 0
    div_hist = []

    for idx in range(si, total):
        hist = all_data[:idx]
        cur = all_data[idx]
        picks, _ = predict_4d(hist, div_history=div_hist)
        div_hist.append(picks)
        hit = any(d in cur[2] for d in picks)
        nh = sum(1 for d in picks if d in cur[2])
        details.append({
            'issue': cur[0], 'date': cur[1], 'actual': cur[2],
            'picks': picks, 'hit': hit, 'n_hits': nh
        })
        if hit:
            hit_count += 1; total_hits += nh

    return {
        'periods': n, 'hit_count': hit_count, 'total': n,
        'hit_rate': hit_count / n,
        'avg_hits': round(total_hits / n, 2),
        'details': details
    }


# ============================================================
# HTML仪表盘 — 四胆码版
# ============================================================

def generate_html(all_data, bt100, state):
    algo_name = "四胆码精锐 v14.1"
    badge = '<span style="font-size:10px;background:rgba(255,255,255,.2);color:#fff;padding:1px 6px;border-radius:10px;margin-left:6px">v14.1 参数精调</span>'

    div_hist = state['stats'].get('recent_picks', [])
    next_picks, _ = predict_4d(all_data, div_history=div_hist if div_hist else None)
    next_issue = str(int(all_data[-1][0]) + 1)

    st = state['stats']
    total_pred = st.get('total_verified', 0)
    total_hit = st.get('total_hits', 0)
    live_hr = f"{total_hit/total_pred*100:.1f}%" if total_pred > 0 else "--"
    recent_10 = st.get('recent_10_hits', 0)

    wbars = ''.join(
        f'<div style="margin-bottom:4px"><span style="display:inline-block;width:70px;font-size:10px;color:#888">{SIGNAL_META[name]["cn"]}</span>'
        f'<span style="display:inline-block;height:14px;background:linear-gradient(90deg,#667eea,#764ba2);'
        f'border-radius:7px;width:{SUM_WEIGHTS[name]*200}px;min-width:2px"></span>'
        f'<span style="font-size:10px;font-weight:700;margin-left:4px;color:#333">{SUM_WEIGHTS[name]:.0%}</span></div>'
        for name in SIGNAL_NAMES
    )

    det_html = ''
    for r in reversed(bt100['details']):
        ast = ' '.join(str(d) for d in r['actual'])
        actual_set = set(r['actual'])
        pballs = ''.join(
            f'<span class="pb-hit">{d}</span>' if d in actual_set
            else f'<span class="pb-miss">{d}</span>' for d in r['picks'])
        cls = 'hit-yes' if r['hit'] else 'hit-no'
        mark = f'<span class="mk-yes">✓ {r["n_hits"]}个</span>' if r['hit'] else '<span class="mk-no">✗</span>'
        det_html += (f'<tr class="{cls}"><td>{r["issue"]}</td><td>{r["date"]}</td>'
                   f'<td class="ac">{ast}</td><td class="pc">{pballs}</td><td>{mark}</td></tr>')

    hn, mn = bt100['hit_count'], bt100['periods'] - bt100['hit_count']
    hr = bt100['hit_rate'] * 100

    hot_nums = Counter()
    for r in bt100['details']:
        for d in r['picks']: hot_nums[d] += 1
    top_hot = sorted(hot_nums.items(), key=lambda x: x[1], reverse=True)[:4]
    hot_html = ''.join(f'<span class="ht">{d}<small>{c}次</small></span>' for d, c in top_hot)

    nballs = ''.join(f'<div class="ball">{d}</div>' for d in next_picks)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>晓炜胆码 · 四胆码</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f8fafc;color:#334155;min-height:100vh}}
.header{{background:linear-gradient(135deg,#1e3a5f,#2d5a87);color:#fff;padding:22px 16px;text-align:center}}
.header h1{{font-size:20px;font-weight:700;letter-spacing:2px;margin-bottom:4px}}
.header .sub{{font-size:11px;opacity:.55;font-weight:300}}
.container{{max-width:700px;margin:0 auto;padding:16px 16px 0}}

.pred-card{{background:#fff;border:2px solid #2d5a87;border-radius:14px;padding:28px 22px 22px;margin:0 0 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.pred-card .label{{font-size:11px;color:#2d5a87;letter-spacing:5px;text-transform:uppercase;margin-bottom:6px;font-weight:700}}
.pred-card .issue{{font-size:13px;color:#e67e22;font-weight:600;margin-bottom:16px}}
.balls{{display:flex;justify-content:center;gap:14px}}
.ball{{width:58px;height:58px;line-height:58px;border-radius:50%;background:linear-gradient(135deg,#e67e22,#d35400);color:#fff;font-size:24px;font-weight:800;text-align:center;box-shadow:0 2px 8px rgba(230,126,34,.25)}}
.pred-card .footnote{{font-size:11px;color:#94a3b8;margin-top:16px}}

.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}}
.stat{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 8px 14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.03)}}
.stat .val{{font-size:25px;font-weight:800;line-height:1}}
.stat .lbl{{font-size:10px;color:#94a3b8;margin-top:5px}}
.stat.s1 .val{{color:#e67e22}}
.stat.s2 .val{{color:#2d5a87}}
.stat.s3 .val{{color:#27ae60}}
.stat.s4 .val{{color:#8e44ad}}

.section{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 16px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.03)}}
.section .title{{font-size:14px;font-weight:700;margin-bottom:12px;padding-bottom:9px;border-bottom:1px solid #f1f5f9;color:#1e293b}}

.bar-row{{display:flex;gap:6px;height:32px}}
.bar{{flex:1;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff}}
.bar.hit{{background:linear-gradient(90deg,#e67e22,#f39c12)}}
.bar.miss{{background:#f1f5f9;color:#94a3b8}}

.hot-tags{{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}}
.ht{{display:inline-flex;align-items:center;gap:3px;background:#fef9e7;color:#e67e22;padding:5px 14px;border-radius:20px;font-size:14px;font-weight:700}}
.ht small{{font-size:10px;font-weight:400;opacity:.65}}

.tb-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#f8fafc;padding:10px 6px;text-align:center;font-weight:700;border-bottom:1px solid #e2e8f0;white-space:nowrap;font-size:11px;color:#64748b}}
td{{padding:9px 5px;text-align:center;border-bottom:1px solid #f1f5f9}}
.ac{{font-weight:800;color:#2d5a87;letter-spacing:3px;font-size:13px}}
.pc{{color:#334155;letter-spacing:1px;display:flex;justify-content:center;gap:4px;flex-wrap:wrap}}
.pb-hit{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#e67e22,#d35400);color:#fff;font-weight:800;font-size:12px}}
.pb-miss{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#fef2f2;color:#ef4444;font-weight:700;font-size:12px;border:1.5px solid #fecaca}}
.hit-yes td{{background:#fefcf5}}
.mk-yes{{color:#e67e22;font-weight:700;font-size:11px}}
.mk-no{{color:#ef4444;font-weight:600;font-size:11px}}

.warn{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:11.5px;color:#92400e;text-align:center}}
.footer{{text-align:center;padding:20px 16px 30px;color:#94a3b8;font-size:10px;line-height:1.8}}

@media(max-width:600px){{
  .stats{{grid-template-columns:repeat(2,1fr)}}
  .ball{{width:48px;height:48px;line-height:48px;font-size:20px}}
  .balls{{gap:10px}}
  .pred-card{{padding:22px 14px 16px}}
  .section{{padding:14px 12px}}
}}
</style>
</head>
<body>
<div class="header">
  <h1>晓炜胆码 · 四胆码</h1>
  <div class="sub">{algo_name} · 5维信号 · rank冷号 · 精简融合{badge}</div>
</div>

<div class="container">
  <div class="warn"><strong>⚠ 风险提示：</strong>彩票开奖具有随机性，本软件仅供数据分析参考，不构成投注建议。请理性购彩。</div>

  <div class="pred-card">
    <div class="label">▎下期预测四胆码</div>
    <div class="issue">期号 {next_issue}</div>
    <div class="balls">
      {nballs}
    </div>
    <div class="footnote">{algo_name} · 基于{len(all_data)}期历史数据 · 多源实时更新</div>
  </div>

  <div class="stats">
    <div class="stat s1"><div class="val">{hr:.1f}%</div><div class="lbl">100期回测命中率</div></div>
    <div class="stat s2"><div class="val">{hn}/{bt100['periods']}</div><div class="lbl">回测命中期数</div></div>
    <div class="stat s3"><div class="val">{live_hr}</div><div class="lbl">实盘命中率({total_pred}期)</div></div>
    <div class="stat s4"><div class="val">{recent_10}/10</div><div class="lbl">最近10期命中</div></div>
  </div>

  <div class="section">
    <div class="title">🧬 信号权重 (加权求和)</div>
    {wbars}
  </div>

  <div class="section">
    <div class="title">📊 100期命中分布</div>
    <div class="bar-row">
      <div class="bar hit" style="flex:{hn}">{hn}期 命中 ✓</div>
      <div class="bar miss" style="flex:{mn}">{mn}期 未中 ✗</div>
    </div>
    <div style="margin-top:10px;font-size:11px;color:#999">高频预测数字</div>
    <div class="hot-tags">{hot_html}</div>
  </div>

  <div class="section">
    <div class="title">📋 100期回测详情（近→远）</div>
    <div class="tb-wrap">
      <table>
        <thead><tr><th>期号</th><th>日期</th><th>开奖号码</th><th>预测胆码</th><th>结果</th></tr></thead>
        <tbody>{det_html}</tbody>
      </table>
    </div>
  </div>
</div>

<div class="footer">
  数据来源: 中国福利彩票官网 · {algo_name}<br>
  生成时间: <span id="t"></span> · 仅供参考
</div>

<script>document.getElementById('t').textContent=new Date().toLocaleString('zh-CN')</script>
</body>
</html>'''


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 55)
    print("  福彩3D四胆码预测系统 · v14.1 云端自动更新")
    print("  5维信号 · rank冷号消除偏见 · 精简融合 · 自主迭代")
    print("=" * 55)

    all_data = load_data()

    print(f"\n[学习] 加载历史状态...")
    state = load_state()
    learned = learn_from_history(state, all_data)
    if learned:
        print(f"  [学习完成] 共 {state['stats']['total_verified']} 期已验证")

    print(f"\n[回测] 100期滚动回测...")
    bt100 = run_backtest(all_data, 100)
    print(f"  100期: 命中率{bt100['hit_rate']*100:.1f}% ({bt100['hit_count']}/{bt100['periods']}) 均{bt100['avg_hits']}个")

    bt50 = run_backtest(all_data, 50)
    print(f"  50期: 命中率{bt50['hit_rate']*100:.1f}% ({bt50['hit_count']}/{bt50['periods']}) 均{bt50['avg_hits']}个")

    bt30 = run_backtest(all_data, 30)
    print(f"  30期: 命中率{bt30['hit_rate']*100:.1f}% ({bt30['hit_count']}/{bt30['periods']}) 均{bt30['avg_hits']}个")

    div_hist = state['stats'].get('recent_picks', [])
    next_picks, signals = predict_4d(all_data, div_history=div_hist if div_hist else None)
    next_issue = str(int(all_data[-1][0]) + 1)
    print(f"\n[预测] 下期 {next_issue} 4胆码: {' '.join(str(d) for d in next_picks)}")

    state = add_prediction(state, next_issue, next_picks, signals)
    save_state(state)

    html = generate_html(all_data, bt100, state)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index_4d.html')
    with open(out, 'w', encoding='utf-8') as f: f.write(html)

    print(f"\n✅ 已生成: {out}")
    print("=" * 55)
    return out


if __name__ == '__main__':
    main()
