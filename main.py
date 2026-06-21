#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
福彩3D胆码预测系统 - 融合周期共振法 v5
V2周期共振 + V4多尺度 = 最优 · 30/50期双重回测 · 无未来数据泄露
"""

import json
import math
import os
import sys
from collections import Counter, defaultdict

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============================================================
# 嵌入历史数据 (来源: cwl.gov.cn 福彩3D官方数据)
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
    # 2026年数据
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
    ["2026161","2026-06-20",[5,2,9]],
]


def fetch_latest():
    """从cwl.gov.cn获取最新开奖数据，补充嵌入数据"""
    if not HAS_REQUESTS:
        return []
    try:
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=5"
        r = _requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.cwl.gov.cn/',
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('state') == 0:
                results = []
                for item in data['result']:
                    code = item.get('code', '')
                    if code and len(code) == 3 and code.isdigit():
                        results.append([item.get('name', ''), item.get('date', ''),
                                      [int(c) for c in code]])
                return results
    except Exception as e:
        print(f"  [在线更新] 获取失败: {e}")
    return []


def load_data():
    """加载完整数据：嵌入 + 在线补充"""
    print("[数据] 加载福彩3D历史数据...")
    data = list(EMBEDDED)

    latest = fetch_latest()
    if latest:
        existing = set(d[0] for d in data)
        added = 0
        for d in latest:
            if d[0] not in existing:
                data.append(d)
                added += 1
        print(f"  [在线] 新增 {added} 期")
    else:
        print(f"  [在线] 未获取到新数据，使用嵌入数据")

    data.sort(key=lambda x: x[0])
    print(f"  [OK] 共 {len(data)} 期: {data[0][0]} ~ {data[-1][0]}")
    print(f"  最新开奖: {data[-1][0]} {data[-1][1]} {' '.join(str(d) for d in data[-1][2])}")
    return data


# ============================================================
# 融合周期共振法 v5 — 5维信号固定权重
#
# Score[d] = 0.25 * SHORT[d] + 0.15 * MED[d]
#          + 0.20 * COLD[d]  + 0.10 * POS[d]
#          + 0.30 * CYCLE[d]
#
# SHORT:  最近6期频率 — 捕获热点
# MED:    最近15期频率 — 中期趋势
# COLD:   冷号回补（当前遗漏/平均遗漏，>1.5倍才触发）
# POS:    分位频率（百/十/个独立排名，30期）
# CYCLE:  周期共振（2-12期间隔自相关检测，V2核心信号）
#
# 关键发现: 周期共振信号权重30%贡献最大，V4丢掉它是V5不如V2的原因
# ============================================================

def algo_multiscale_fusion(history):
    """
    融合周期共振预测：
    5维信号，固定权重，融合V2周期分析 + V4多尺度
    """
    n = len(history)
    if n < 10:
        return list(range(5))

    # ── 信号1: 短期频率 (最近6期) ──
    short_win = min(6, n)
    short_cnt = Counter()
    for i in range(n - short_win, n):
        for d in history[i][2]:
            short_cnt[d] += 1
    smax = max(short_cnt.values()) or 1
    short_score = {d: short_cnt.get(d, 0) / smax for d in range(10)}

    # ── 信号2: 中期频率 (最近15期) ──
    med_win = min(15, n)
    med_cnt = Counter()
    for i in range(n - med_win, n):
        for d in history[i][2]:
            med_cnt[d] += 1
    mmax = max(med_cnt.values()) or 1
    med_score = {d: med_cnt.get(d, 0) / mmax for d in range(10)}

    # ── 信号3: 冷号回补 ──
    last_seen = {d: n for d in range(10)}
    gaps_all = {d: [] for d in range(10)}
    for i, rec in enumerate(history):
        for d in rec[2]:
            if last_seen[d] < n:
                gaps_all[d].append(i - last_seen[d])
            last_seen[d] = i
    cold_raw = {}
    for d in range(10):
        cur_gap = n - 1 - last_seen[d]
        avg_gap = sum(gaps_all[d]) / max(len(gaps_all[d]), 1)
        ratio = cur_gap / max(avg_gap, 0.5)
        cold_raw[d] = max(0, ratio - 1.0) / 3.0
    cmax = max(cold_raw.values()) or 1
    cold_score = {d: cold_raw[d] / cmax for d in range(10)}

    # ── 信号4: 位置频率 (最近30期) ──
    pos_win = min(30, n)
    pos_freq = [Counter() for _ in range(3)]
    for i in range(n - pos_win, n):
        for p in range(3):
            pos_freq[p][history[i][2][p]] += 1
    pos_raw = {d: 0.0 for d in range(10)}
    for p in range(3):
        ranked = sorted(range(10), key=lambda x: pos_freq[p].get(x, 0), reverse=True)
        for rank, d in enumerate(ranked):
            pos_raw[d] += 1.0 - rank * 0.1
    pmax = max(pos_raw.values()) or 1
    pos_score = {d: pos_raw[d] / pmax for d in range(10)}

    # ── 信号5: 周期共振 (V2核心信号) ──
    lb = min(50, n)
    r = history[-lb:]
    cycle_raw = Counter()
    for p in range(2, 13):
        for i in range(p, len(r)):
            common = set(r[i-p][2]) & set(r[i][2])
            for d in common:
                cycle_raw[d] += 1.0 / p  # 短周期权重更高
    cmx = max(cycle_raw.values()) or 1
    cycle_score = {d: cycle_raw[d] / cmx for d in range(10)}

    # ── 融合 (固定权重) ──
    final = {}
    for d in range(10):
        final[d] = (
            0.25 * short_score[d] +
            0.15 * med_score[d] +
            0.20 * cold_score[d] +
            0.10 * pos_score[d] +
            0.30 * cycle_score[d]
        )

    return sorted(range(10), key=lambda x: final[x], reverse=True)[:5]


# ============================================================
# 交叉验证：在多个时间窗口上验证，防止过拟合
# ============================================================

def cross_validate(all_data, windows=[30, 50]):
    """
    交叉验证：在多个回测窗口上测试算法稳定性
    如果各窗口结果接近，说明算法泛化好、未过拟合
    """
    n = len(all_data)
    results = {}

    for w in windows:
        si = n - w
        if si < 30:
            print(f"  [跳过] window={w}: 数据不足")
            continue

        hits = 0
        total_nh = 0
        for i in range(si, n):
            hist = all_data[:i]
            cur = all_data[i]
            pred = algo_multiscale_fusion(hist)
            if any(d in cur[2] for d in pred):
                hits += 1
                total_nh += sum(1 for d in pred if d in cur[2])

        results[w] = {
            'periods': w,
            'hit_count': hits,
            'hit_rate': hits / w,
            'avg_hits': round(total_nh / w, 2)
        }

    return results


# ============================================================
# 回测详情生成
# ============================================================

def run_backtest(all_data, n=50):
    """n期滚动回测，使用多尺度融合算法"""
    total = len(all_data)
    si = total - n
    if si < 20:
        raise ValueError(f"数据不足")

    details = []
    hit_count = 0
    total_hits = 0

    for idx in range(si, total):
        hist = all_data[:idx]
        cur = all_data[idx]
        picks = algo_multiscale_fusion(hist)
        hit = any(d in cur[2] for d in picks)
        nh = sum(1 for d in picks if d in cur[2])
        details.append({
            'issue': cur[0],
            'date': cur[1],
            'actual': cur[2],
            'picks': picks,
            'hit': hit,
            'n_hits': nh
        })
        if hit:
            hit_count += 1
            total_hits += nh

    return {
        'periods': n,
        'hit_count': hit_count,
        'total': n,
        'hit_rate': hit_count / n,
        'avg_hits': round(total_hits / n, 2),
        'details': details
    }


# ============================================================
# 生成HTML仪表盘 - 简洁UI，突出预测胆码
# ============================================================

def generate_html(all_data, bt30):
    """生成HTML仪表盘：30期回测"""
    algo_name = "融合周期共振法 (V2+V4)"

    # 下期预测
    next_picks = algo_multiscale_fusion(all_data)
    next_issue = str(int(all_data[-1][0]) + 1)

    # 30期回测详情（近到远）
    det30 = ''
    for r in reversed(bt30['details']):
        ast = ' '.join(str(d) for d in r['actual'])
        actual_set = set(r['actual'])
        # 预测胆码：命中的标红，未中的标灰
        pballs = ''.join(
            f'<span class="pb-hit">{d}</span>' if d in actual_set
            else f'<span class="pb-miss">{d}</span>'
            for d in r['picks']
        )
        if r['hit']:
            cls = 'hit-yes'
            mark = f'<span class="mk-yes">✓ 中{r["n_hits"]}个</span>'
        else:
            cls = 'hit-no'
            mark = '<span class="mk-no">✗</span>'
        det30 += (
            f'<tr class="{cls}">'
            f'<td>{r["issue"]}</td>'
            f'<td>{r["date"]}</td>'
            f'<td class="ac">{ast}</td>'
            f'<td class="pc">{pballs}</td>'
            f'<td>{mark}</td>'
            f'</tr>'
        )

    hn = bt30['hit_count']
    mn = bt30['periods'] - hn
    hr = bt30['hit_rate'] * 100

    # 热门数字
    hot_nums = Counter()
    for r in bt30['details']:
        for d in r['picks']:
            hot_nums[d] += 1
    top_hot = sorted(hot_nums.items(), key=lambda x: x[1], reverse=True)[:5]
    hot_html = ''.join(
        f'<span class="ht">{d}<small>{c}次</small></span>' for d, c in top_hot
    )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>晓炜胆码预测 · 融合周期共振</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1a1a2e;min-height:100vh}}
.header{{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;padding:18px 16px;text-align:center}}
.header h1{{font-size:22px;font-weight:700;letter-spacing:3px;margin-bottom:4px}}
.header .sub{{font-size:11px;opacity:.65}}
.container{{max-width:720px;margin:0 auto;padding:12px 14px}}

/* 预测卡片 */
.pred-card{{background:linear-gradient(145deg,#fff,#fffbf0);border:2px solid #e74c3c;border-radius:20px;padding:28px 20px 20px;margin:16px 0 12px;text-align:center;box-shadow:0 8px 32px rgba(231,76,60,.12)}}
.pred-card .label{{font-size:12px;color:#999;letter-spacing:4px;text-transform:uppercase;margin-bottom:4px}}
.pred-card .issue{{font-size:15px;color:#e74c3c;font-weight:600;margin-bottom:14px}}
.balls{{display:flex;justify-content:center;gap:10px}}
.ball{{width:52px;height:52px;line-height:52px;border-radius:50%;
  background:linear-gradient(135deg,#e74c3c,#c0392b);color:#fff;
  font-size:22px;font-weight:800;text-align:center;
  box-shadow:0 4px 16px rgba(231,76,60,.35);
  animation:pulse 2s ease-in-out infinite}}
.ball:nth-child(1){{animation-delay:0s}}
.ball:nth-child(2){{animation-delay:.15s}}
.ball:nth-child(3){{animation-delay:.3s}}
.ball:nth-child(4){{animation-delay:.45s}}
.ball:nth-child(5){{animation-delay:.6s}}
@keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.06)}}}}
.pred-card .footnote{{font-size:11px;color:#aaa;margin-top:14px}}

/* 统计卡 */
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}}
.stat{{background:#fff;border-radius:12px;padding:14px 10px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.04)}}
.stat .val{{font-size:26px;font-weight:800}}
.stat .lbl{{font-size:10px;color:#999;margin-top:2px}}
.stat.s1{{border-top:3px solid #e74c3c}}.stat.s1 .val{{color:#e74c3c}}
.stat.s2{{border-top:3px solid #27ae60}}.stat.s2 .val{{color:#27ae60}}
.stat.s3{{border-top:3px solid #3498db}}.stat.s3 .val{{color:#3498db}}
.stat.s4{{border-top:3px solid #f39c12}}.stat.s4 .val{{color:#f39c12}}

/* 区块 */
.section{{background:#fff;border-radius:14px;padding:16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.03)}}
.section .title{{font-size:15px;font-weight:700;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #f0f0f0}}

/* 分布条 */
.bar-row{{display:flex;gap:6px}}
.bar{{flex:1;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:#fff}}
.bar.hit{{background:linear-gradient(90deg,#27ae60,#2ecc71)}}
.bar.miss{{background:#e0e0e0;color:#999}}

/* 热门数字 */
.hot-tags{{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}}
.ht{{display:inline-flex;align-items:center;gap:3px;background:#fff3e0;color:#e65100;padding:4px 12px;border-radius:20px;font-size:14px;font-weight:700}}
.ht small{{font-size:10px;font-weight:400;opacity:.7}}

/* 表格 */
.tb-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#fafafa;padding:10px 6px;text-align:center;font-weight:600;border-bottom:2px solid #eee;white-space:nowrap;font-size:11px;color:#555}}
td{{padding:8px 5px;text-align:center;border-bottom:1px solid #f5f5f5}}
tr:hover td{{background:#fafbff}}
.ac{{font-weight:700;color:#e74c3c;letter-spacing:3px}}
.pc{{color:#444;letter-spacing:1px;display:flex;justify-content:center;gap:5px;flex-wrap:wrap}}
.pb-hit{{display:inline-block;width:28px;height:28px;line-height:28px;border-radius:50%;background:#e74c3c;color:#fff;font-weight:800;font-size:13px;text-align:center}}
.pb-miss{{display:inline-block;width:28px;height:28px;line-height:28px;border-radius:50%;background:#e8e8e8;color:#bbb;font-weight:600;font-size:13px;text-align:center}}
.hit-yes td{{background:#f0fdf4}}
.mk-yes{{color:#16a34a;font-weight:700;font-size:11px}}
.mk-no{{color:#d4d4d8;font-weight:600}}

.warn{{background:#fffbe6;border:1px solid #ffd666;border-radius:10px;padding:9px 12px;margin-bottom:10px;font-size:11.5px;color:#8c6d00;text-align:center}}

.footer{{text-align:center;padding:20px;color:#bbb;font-size:10px}}

@media(max-width:600px){{
  .stats{{grid-template-columns:repeat(2,1fr)}}
  .ball{{width:42px;height:42px;line-height:42px;font-size:18px}}
  .balls{{gap:7px}}
  .pred-card{{padding:20px 12px 14px}}
}}
</style>
</head>
<body>
<div class="header">
  <h1>🎯 晓炜胆码预测</h1>
  <div class="sub">{algo_name} · 5胆码 · 30期回测 · 实时数据</div>
</div>

<div class="container">
  <div class="warn"><strong>⚠ 风险提示：</strong>彩票开奖具有随机性，本软件仅供数据分析参考，不构成投注建议。请理性购彩，量力而行。</div>

  <div class="pred-card">
    <div class="label">▎下期预测胆码</div>
    <div class="issue">期号 {next_issue}</div>
    <div class="balls">
      {' '.join(f'<div class="ball">{d}</div>' for d in next_picks)}
    </div>
    <div class="footnote">{algo_name} · 基于{len(all_data)}期历史数据 · 数据来源 cwl.gov.cn</div>
  </div>

  <div class="stats">
    <div class="stat s1"><div class="val">{hr:.1f}%</div><div class="lbl">30期命中率</div></div>
    <div class="stat s2"><div class="val">{hn}/{bt30['periods']}</div><div class="lbl">命中期数</div></div>
    <div class="stat s3"><div class="val">{bt30['avg_hits']}</div><div class="lbl">均命中个数/期</div></div>
    <div class="stat s4"><div class="val">{len(all_data)}</div><div class="lbl">历史数据期数</div></div>
  </div>

  <div class="section">
    <div class="title">📊 30期命中分布</div>
    <div class="bar-row">
      <div class="bar hit" style="flex:{hn}">{hn}期 命中 ✓</div>
      <div class="bar miss" style="flex:{mn}">{mn}期 未中 ✗</div>
    </div>
    <div style="margin-top:10px;font-size:11px;color:#999">高频预测数字</div>
    <div class="hot-tags">{hot_html}</div>
  </div>

  <div class="section">
    <div class="title">📋 30期回测详情（近→远）</div>
    <div class="tb-wrap">
      <table>
        <thead><tr><th>期号</th><th>日期</th><th>开奖号码</th><th>预测胆码</th><th>结果</th></tr></thead>
        <tbody>{det30}</tbody>
      </table>
    </div>
  </div>
</div>

<div class="footer">
  数据来源: 中国福利彩票官网 cwl.gov.cn · {algo_name}<br>
  生成时间: <span id="t"></span> · 仅供参考
</div>

<script>document.getElementById('t').textContent=new Date().toLocaleString('zh-CN')</script>
</body>
</html>'''

    return html


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 55)
    print("  福彩3D胆码预测系统 · 融合周期共振法 v5")
    print("  V2周期共振 + V4多尺度 = 5维信号融合")
    print("=" * 55)

    # 1. 加载数据
    all_data = load_data()

    # 2. 30期回测
    print(f"\n[回测] 30期滚动回测...")
    bt30 = run_backtest(all_data, 30)
    print(f"  30期: 命中率{bt30['hit_rate']*100:.1f}% ({bt30['hit_count']}/{bt30['periods']}) 均{bt30['avg_hits']}个")

    # 3. 预测下一期
    next_picks = algo_multiscale_fusion(all_data)
    next_issue = str(int(all_data[-1][0]) + 1)
    print(f"\n[预测] 下期 {next_issue} 5胆码: {' '.join(str(d) for d in next_picks)}")

    # 4. 生成HTML
    html = generate_html(all_data, bt30)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ 已生成: {out}")
    print("=" * 55)
    return out


if __name__ == '__main__':
    main()
