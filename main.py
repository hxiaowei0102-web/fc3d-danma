#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
福彩3D胆码预测系统 - v16 云端自动更新
核心突破: cold强制席2→3, 500期94.8%!
数据源(2026-06-25重排): cwl.gov.cn(主) → cjcp.cn → c133.com → cloudscraper → kjapi.com → huiniao.top
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
# 参数配置
# ============================================================
SIGNAL_NAMES = ['trend', 'cold_v3', 'edge', 'sum_tail', 'trend_accel']
COLD_WEIGHT = 0.34
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
    'cold_v3': 0.34,
    'edge': 0.20,
    'sum_tail': 0.14,
    'trend_accel': 0.12,
}

# 共识boost映射（保留兼容）
BOOST_MAP = {0: 1.0, 1: 1.15, 2: 1.35, 3: 1.6, 4: 1.85, 5: 2.1}
COLD_BONUS = 1.0
# 保护少数派参数
GUARANTEED_COLD = 2     # cold_v3保证入选top-N (基础)
COLD_EXPAND_RATIO = 0.85 # cold#3得分 > cold#2*0.85时扩容到3
GUARANTEED_EDGE = 1     # edge保证入选top-N (基础)
EDGE_EXPAND_RATIO = 0.80 # edge#2得分 > edge#1*0.80时扩容到2
DIV_WINDOW = 12
DIV_PENALTY = 0.30

# ============================================================
# 嵌入历史数据
# ============================================================
EMBEDDED = [
    ["2025351","2025-12-31",[4,5,2],
    ["2025301","2025-11-11",[8,3,0]],
    ["2025302","2025-11-12",[0,5,9]],
    ["2025303","2025-11-13",[9,1,4]],
    ["2025304","2025-11-14",[7,1,2]],
    ["2025305","2025-11-15",[8,4,4]],
    ["2025306","2025-11-16",[6,2,1]],
    ["2025307","2025-11-17",[7,6,1]],
    ["2025308","2025-11-18",[3,3,7]],
    ["2025309","2025-11-19",[1,7,4]],
    ["2025310","2025-11-20",[1,2,7]],
    ["2025311","2025-11-21",[6,8,8]],
    ["2025312","2025-11-22",[5,6,0]],
    ["2025313","2025-11-23",[6,1,3]],
    ["2025314","2025-11-24",[1,3,9]],
    ["2025315","2025-11-25",[1,2,3]],
    ["2025316","2025-11-26",[5,1,3]],
    ["2025317","2025-11-27",[0,5,4]],
    ["2025318","2025-11-28",[1,8,1]],
    ["2025319","2025-11-29",[0,8,1]],
    ["2025320","2025-11-30",[2,5,4]],
    ["2025321","2025-12-01",[9,4,1]],
    ["2025322","2025-12-02",[6,9,3]],
    ["2025323","2025-12-03",[6,5,0]],
    ["2025324","2025-12-04",[2,0,5]],
    ["2025325","2025-12-05",[0,4,1]],
    ["2025326","2025-12-06",[7,2,3]],
    ["2025327","2025-12-07",[2,9,2]],
    ["2025328","2025-12-08",[9,0,7]],
    ["2025329","2025-12-09",[2,2,4]],
    ["2025330","2025-12-10",[1,9,0]],
    ["2025331","2025-12-11",[2,4,6]],
    ["2025332","2025-12-12",[9,0,7]],
    ["2025333","2025-12-13",[2,0,5]],
    ["2025334","2025-12-14",[3,7,8]],
    ["2025335","2025-12-15",[0,5,1]],
    ["2025336","2025-12-16",[6,4,1]],
    ["2025337","2025-12-17",[8,7,6]],
    ["2025338","2025-12-18",[6,8,9]],
    ["2025339","2025-12-19",[6,7,6]],
    ["2025340","2025-12-20",[1,3,0]],
    ["2025341","2025-12-21",[9,9,6]],
    ["2025342","2025-12-22",[6,8,1]],
    ["2025343","2025-12-23",[6,4,5]],
    ["2025344","2025-12-24",[6,2,2]],
    ["2025345","2025-12-25",[6,3,0]],
    ["2025346","2025-12-26",[8,9,7]],
    ["2025347","2025-12-27",[1,9,2]],
    ["2025348","2025-12-28",[2,7,8]],
    ["2025349","2025-12-29",[7,4,3]],
    ["2025350","2025-12-30",[5,8,0]],
    ["2026001","2026-01-01",[2,9,8]],
    ["2026002","2026-01-02",[5,2,0]],
    ["2026003","2026-01-03",[6,0,1]],
    ["2026004","2026-01-04",[0,1,9]],
    ["2026005","2026-01-05",[4,7,6]],
    ["2026006","2026-01-06",[2,4,4]],
    ["2026007","2026-01-07",[3,5,3]],
    ["2026008","2026-01-08",[2,5,2]],
    ["2026009","2026-01-09",[2,6,5]],
    ["2026010","2026-01-10",[6,6,7]],
    ["2026011","2026-01-11",[6,4,7]],
    ["2026012","2026-01-12",[2,4,1]],
    ["2026013","2026-01-13",[5,1,3]],
    ["2026014","2026-01-14",[0,5,0]],
    ["2026015","2026-01-15",[5,3,2]],
    ["2026016","2026-01-16",[5,8,2]],
    ["2026017","2026-01-17",[9,4,5]],
    ["2026018","2026-01-18",[4,9,4]],
    ["2026019","2026-01-19",[2,2,3]],
    ["2026020","2026-01-20",[6,7,6]],
    ["2026021","2026-01-21",[5,5,9]],
    ["2026022","2026-01-22",[6,7,8]],
    ["2026023","2026-01-23",[7,8,4]],
    ["2026024","2026-01-24",[9,1,1]],
    ["2026025","2026-01-25",[0,2,9]],
    ["2026026","2026-01-26",[0,9,9]],
    ["2026027","2026-01-27",[1,2,6]],
    ["2026028","2026-01-28",[2,7,0]],
    ["2026029","2026-01-29",[0,0,3]],
    ["2026030","2026-01-30",[1,3,4]],
    ["2026031","2026-01-31",[1,4,2]],
    ["2026032","2026-02-01",[4,5,2]],
    ["2026033","2026-02-02",[1,1,9]],
    ["2026034","2026-02-03",[0,5,2]],
    ["2026035","2026-02-04",[2,1,3]],
    ["2026036","2026-02-05",[7,6,2]],
    ["2026037","2026-02-06",[4,2,0]],
    ["2026038","2026-02-07",[4,6,7]],
    ["2026039","2026-02-08",[4,5,0]],
    ["2026040","2026-02-09",[4,2,5]],
    ["2026041","2026-02-10",[9,0,1]],
    ["2026042","2026-02-11",[8,5,4]],
    ["2026043","2026-02-12",[7,6,5]],
    ["2026044","2026-02-13",[5,8,9]],
    ["2026045","2026-02-24",[1,8,1]],
    ["2026046","2026-02-25",[2,9,1]],
    ["2026047","2026-02-26",[9,3,6]],
    ["2026048","2026-02-27",[6,1,2]],
    ["2026049","2026-02-28",[1,1,0]],
    ["2026050","2026-03-01",[6,8,9]],
    ["2026051","2026-03-02",[3,0,2]],
    ["2026052","2026-03-03",[2,7,7]],
    ["2026053","2026-03-04",[7,5,5]],
    ["2026054","2026-03-05",[2,1,7]],
    ["2026055","2026-03-06",[1,0,7]],
    ["2026056","2026-03-07",[4,7,7]],
    ["2026057","2026-03-08",[2,6,4]],
    ["2026058","2026-03-09",[5,4,3]],
    ["2026059","2026-03-10",[7,9,4]],
    ["2026060","2026-03-11",[9,4,3]],
    ["2026061","2026-03-12",[4,2,9]],
    ["2026062","2026-03-13",[2,9,4]],
    ["2026063","2026-03-14",[5,1,7]],
    ["2026064","2026-03-15",[6,0,4]],
    ["2026065","2026-03-16",[0,5,7]],
    ["2026066","2026-03-17",[9,3,4]],
    ["2026067","2026-03-18",[6,9,5]],
    ["2026068","2026-03-19",[7,0,6]],
    ["2026069","2026-03-20",[9,0,8]],
    ["2026070","2026-03-21",[4,8,4]],
    ["2026071","2026-03-22",[2,6,1]],
    ["2026072","2026-03-23",[2,4,5]],
    ["2026073","2026-03-24",[5,0,4]],
    ["2026074","2026-03-25",[4,8,7]],
    ["2026075","2026-03-26",[8,1,6]],
    ["2026076","2026-03-27",[8,6,3]],
    ["2026077","2026-03-28",[1,1,2]],
    ["2026078","2026-03-29",[0,4,9]],
    ["2026079","2026-03-30",[2,3,3]],
    ["2026080","2026-03-31",[8,0,2]],
    ["2026081","2026-04-01",[8,2,7]],
    ["2026082","2026-04-02",[9,4,2]],
    ["2026083","2026-04-03",[5,0,6]],
    ["2026084","2026-04-04",[4,5,6]],
    ["2026085","2026-04-05",[1,1,8]],
    ["2026086","2026-04-06",[3,8,2]],
    ["2026087","2026-04-07",[9,1,1]],
    ["2026088","2026-04-08",[6,0,8]],
    ["2026089","2026-04-09",[9,2,2]],
    ["2026090","2026-04-10",[8,1,6]],
    ["2026091","2026-04-11",[5,3,7]],
    ["2026092","2026-04-12",[8,7,0]],
    ["2026093","2026-04-13",[5,1,8]],
    ["2026094","2026-04-14",[4,1,8]],
    ["2026095","2026-04-15",[0,2,2]],
    ["2026096","2026-04-16",[6,8,9]],
    ["2026097","2026-04-17",[8,1,8]],
    ["2026098","2026-04-18",[5,1,3]],
    ["2026099","2026-04-19",[8,7,7]],
    ["2026100","2026-04-20",[4,1,4]],
    ["2026101","2026-04-21",[5,8,4]],
    ["2026102","2026-04-22",[4,2,0]],
    ["2026103","2026-04-23",[6,6,1]],
    ["2026104","2026-04-24",[4,8,2]],
    ["2026105","2026-04-25",[6,3,1]],
    ["2026106","2026-04-26",[9,2,8]],
    ["2026107","2026-04-27",[2,7,8]],
    ["2026108","2026-04-28",[6,7,1]],
    ["2026109","2026-04-29",[1,9,5]],
    ["2026110","2026-04-30",[3,7,9]],
    ["2026111","2026-05-01",[8,6,3]],
    ["2026112","2026-05-02",[0,6,5]],
    ["2026113","2026-05-03",[0,4,0]],
    ["2026114","2026-05-04",[8,6,4]],
    ["2026115","2026-05-05",[5,8,1]],
    ["2026116","2026-05-06",[0,2,0]],
    ["2026117","2026-05-07",[4,1,1]],
    ["2026118","2026-05-08",[1,3,2]],
    ["2026119","2026-05-09",[1,1,2]],
    ["2026120","2026-05-10",[7,3,4]],
    ["2026121","2026-05-11",[3,9,3]],
    ["2026122","2026-05-12",[3,4,6]],
    ["2026123","2026-05-13",[2,0,0]],
    ["2026124","2026-05-14",[2,8,0]],
    ["2026125","2026-05-15",[9,5,4]],
    ["2026126","2026-05-16",[8,4,6]],
    ["2026127","2026-05-17",[7,0,0]],
    ["2026128","2026-05-18",[7,7,6]],
    ["2026129","2026-05-19",[0,2,3]],
    ["2026130","2026-05-20",[2,6,7]],
    ["2026131","2026-05-21",[5,9,8]],
    ["2026132","2026-05-22",[7,5,6]],
    ["2026133","2026-05-23",[0,8,0]],
    ["2026134","2026-05-24",[6,5,4]],
    ["2026135","2026-05-25",[4,8,7]],
    ["2026136","2026-05-26",[8,8,9]],
    ["2026137","2026-05-27",[1,6,5]],
    ["2026138","2026-05-28",[7,9,0]],
    ["2026139","2026-05-29",[2,8,6]],
    ["2026140","2026-05-30",[2,8,5]],
    ["2026141","2026-05-31",[3,9,7]],
    ["2026142","2026-06-01",[8,9,4]],
    ["2026143","2026-06-02",[3,7,6]],
    ["2026144","2026-06-03",[7,2,6]],
    ["2026145","2026-06-04",[2,7,9]],
    ["2026146","2026-06-05",[4,6,4]],
    ["2026147","2026-06-06",[7,1,2]],
    ["2026148","2026-06-07",[4,0,8]],
    ["2026149","2026-06-08",[6,9,6]],
    ["2026150","2026-06-09",[7,2,0]],
    ["2026151","2026-06-10",[6,3,1]],
    ["2026152","2026-06-11",[2,2,0]],
    ["2026153","2026-06-12",[8,8,7]],
    ["2026154","2026-06-13",[3,7,7]],
    ["2026155","2026-06-14",[4,0,9]],
    ["2026156","2026-06-15",[1,6,2]],
    ["2026157","2026-06-16",[3,2,7]],
    ["2026158","2026-06-17",[1,7,8]],
    ["2026159","2026-06-18",[9,9,5]],
    ["2026160","2026-06-19",[3,3,2]],
    ["2026161","2026-06-20",[5,2,9]],
    ["2026162","2026-06-21",[5,8,5]],
    ["2026163","2026-06-22",[5,3,7]]],["2025350","2025-12-30",[5,8,0]],
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
    ["2026163","2026-06-22",[5,3,7]],["2026164","2026-06-23",[6,9,0]],
    ["2026165","2026-06-24",[4,2,4]],["2026166","2026-06-25",[9,0,0]],
    ["2026167","2026-06-26",[6,3,1]],["2026168","2026-06-27",[1,3,0]],
    ["2026169","2026-06-28",[8,3,2]],["2026170","2026-06-29",[8,0,5]],
    ["2026171","2026-06-30",[1,3,4]],["2026172","2026-07-01",[4,4,5]],
    ["2026173","2026-07-02",[6,7,7]],["2026174","2026-07-03",[6,1,8]],
    ["2026175","2026-07-04",[4,2,1]],["2026176","2026-07-05",[2,6,9]],
    ["2026177","2026-07-06",[8,0,8]],["2026178","2026-07-07",[2,6,6]],
    
    ["2026182","2026-07-11",[6, 6, 2]],
    ["2026183","2026-07-12",[9, 2, 3]],
    ["2026184","2026-07-13",[9, 0, 2]],
    ["2026185","2026-07-14",[3, 9, 7]],
    ["2026186","2026-07-15",[0, 4, 5]],
    ["2026187","2026-07-16",[0, 2, 3]],
    ["2026188","2026-07-17",[9, 6, 9]],
    ["2026189","2026-07-18",[5, 5, 8]],
    ["2026190","2026-07-19",[0, 2, 6]],
    ["2026191","2026-07-20",[9, 0, 6]],
]


def _parse_cwl_result(data):
    """解析cwl.gov.cn API返回数据"""
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
    """源6: api.huiniao.top — JSON API, 纯urllib (可能已挂)"""
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
                    print(f"  [源6:huiniao.top] ✓ 获取 {len(results)} 条, 最新: {results[0][0]}={results[0][2]}")
                    return results
    except Exception as e:
        print(f"  [源6:huiniao.top] {type(e).__name__}: {e}")
    return []


def _fetch_c133():
    """源3: c133.com — HTML抓取, 纯urllib, 每次1条最新"""
    import urllib.request as _ur
    import re
    try:
        url = 'http://c133.com/'
        req = _ur.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with _ur.urlopen(req, timeout=10) as r:
            text = r.read().decode('utf-8', errors='replace')
            # 解析: <strong>福彩3D</strong> → <td class="td-period">2026163</td> → ball-blue数字 → td-date日期
            pattern = r'<strong>福彩3D</strong>.*?<td class="td-period">(\d+)</td>.*?ball-blue">(\d)</span>.*?ball-blue">(\d)</span>.*?ball-blue">(\d)</span>.*?<td class="td-date">([\d-]+)</td>'
            m = re.search(pattern, text, re.DOTALL)
            if m:
                issue, d1, d2, d3, date_str = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                digits = [int(d1), int(d2), int(d3)]
                print(f"  [源3:c133.com] ✓ 获取: {issue}={digits} ({date_str})")
                return [[issue, date_str, digits]]
    except Exception as e:
        print(f"  [源3:c133.com] {type(e).__name__}: {e}")
    return []


def _fetch_cjcp():
    """源2: cjcp.cn — 彩经网HTML抓取, 纯urllib+gbk解码, 多期数据"""
    import urllib.request as _ur
    import re
    try:
        url = 'https://www.cjcp.cn/3dkaijiang/'
        req = _ur.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with _ur.urlopen(req, timeout=15) as r:
            raw = r.read()
            text = raw.decode('gbk', errors='replace')
            pattern = r'福彩3D第(\d{7})期开奖结果</div>\s*<div class="date">(\d{4}-\d{2}-\d{2})[^<]*</div>.*?num-ball[^>]*>(\d)<.*?num-ball[^>]*>(\d)<.*?num-ball[^>]*>(\d)<'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                results = []
                for issue, date_str, d1, d2, d3 in matches[:10]:
                    digits = [int(d1), int(d2), int(d3)]
                    results.append([issue, date_str, digits])
                if results:
                    print(f"  [源2:cjcp.cn] 获取 {len(results)} 条, 最新: {results[0][0]}={results[0][2]}")
                    return results
    except Exception as e:
        print(f"  [源2:cjcp.cn] {type(e).__name__}: {e}")
    return []


def _fetch_cwl_requests():
    """源1: cwl.gov.cn — requests直连, 最稳定JSON API"""
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
                    print(f"  [源1:cwl.gov.cn] ✓ 获取 {len(results)} 条")
                    return results
    except Exception as e:
        print(f"  [源1:cwl.gov.cn] {type(e).__name__}: {e}")
    return []


def _fetch_kjapi():
    """源5: kjapi.com — HTML抓取"""
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
                print(f"  [源5:kjapi.com] ✓ 获取 {today}: {issue}={digits}")
                return [[issue, today, digits]]
    except Exception as e:
        print(f"  [源5:kjapi.com] {type(e).__name__}: {e}")
    return []


def _fetch_cloudscraper():
    """源4: cloudscraper — 绕过Cloudflare防护"""
    try:
        scraper = cloudscraper.create_scraper()
        url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=10"
        r = scraper.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('state') == 0:
                results = _parse_cwl_result(data)
                if results:
                    print(f"  [源4:cloudscraper] ✓ 获取 {len(results)} 条")
                    return results
    except Exception as e:
        print(f"  [源4:cloudscraper] {type(e).__name__}: {e}")
    return []


def fetch_latest():
    """多源获取最新开奖数据 — 6重保障, 自动降级 (v12.2, 2026-06-25)"""
    import time
    t0 = time.time()
    source_used = "none"
    
    # 源1: cwl.gov.cn requests — 最稳定JSON API
    if HAS_REQUESTS:
        results = _fetch_cwl_requests()
        if results: source_used = "cwl.gov.cn(requests)"; return results
    
    # 源2: cjcp.cn — 彩经网HTML, 多期(gbk)
    results = _fetch_cjcp()
    if results: source_used = "cjcp.cn"; return results
    
    # 源3: c133.com — HTML抓取, 恢复可用
    results = _fetch_c133()
    if results: source_used = "c133.com"; return results
    
    # 源4: cloudscraper — cwl.gov.cn备用通道
    if HAS_SCRAPER:
        results = _fetch_cloudscraper()
        if results: source_used = "cloudscraper(cwl)"; return results
    
    # 源5: kjapi.com — HTML抓取, 恢复可用
    if HAS_REQUESTS:
        results = _fetch_kjapi()
        if results: source_used = "kjapi.com"; return results
    
    # 源6: api.huiniao.top — JSON API (可能已挂)
    results = _fetch_huiniao(30)
    if results: source_used = "huiniao.top"; return results
    
    elapsed = time.time() - t0
    print(f"  [数据源] 全部6源失败 (耗时{elapsed:.1f}s), 使用嵌入数据兜底")
    return []


def load_data():
    print("[数据] 加载福彩3D历史数据...")
    
    # 主数据源: CSV文件(8690期, 2002~2026)
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fc3d_history.csv')
    data = []
    csv_loaded = False
    if os.path.exists(csv_path):
        try:
            import csv as _csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = _csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    issue = row[0].strip()
                    date = row[1].strip()
                    digits = [int(row[2]), int(row[3]), int(row[4])]
                    # 严格校验
                    if _validate_issue(issue) and len(digits) == 3 and all(_validate_digit(x) for x in digits):
                        data.append([issue, date, digits])
            csv_loaded = True
            print(f"  [CSV] 加载 {len(data)} 期: {data[0][0]} ~ {data[-1][0]}")
        except Exception as e:
            print(f"  [CSV] 加载失败: {e}")
    
    # 在线增量: 获取CSV没有的最新数据
    if csv_loaded:
        latest = fetch_latest()
        if latest:
            existing = set(d[0] for d in data)
            added, rejected = 0, 0
            for d in latest:
                if d[0] not in existing:
                    if not _validate_issue(d[0]) or len(d[2])!=3 or not all(_validate_digit(x) for x in d[2]):
                        rejected += 1; continue
                    data.append(d); added += 1
            if added or rejected:
                print(f"  [在线] 新增 {added} 期, 拒绝 {rejected} 条乱码")
            # 自动追加到CSV文件, 保持CSV永远最新
            if added > 0:
                try:
                    new_entries = [d for d in latest if d[0] not in existing 
                                   and _validate_issue(d[0]) and len(d[2])==3 
                                   and all(_validate_digit(x) for x in d[2])]
                    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                        writer = _csv.writer(f)
                        for entry in sorted(new_entries, key=lambda x: x[0]):
                            writer.writerow([entry[0], entry[1], entry[2][0], entry[2][1], entry[2][2], '', ''])
                    print(f"  [CSV同步] 追加 {len(new_entries)} 期到CSV文件")
                except Exception as e:
                    print(f"  [CSV同步] 写入失败: {e}")
    else:
        # CSV不可用 → 降级到EMBEDDED+在线
        data = list(EMBEDDED)
        latest = fetch_latest()
        if latest:
            existing = set(d[0] for d in data)
            added, rejected = 0, 0
            for d in latest:
                if d[0] not in existing:
                    if not _validate_issue(d[0]) or len(d[2])!=3 or not all(_validate_digit(x) for x in d[2]):
                        rejected += 1; continue
                    data.append(d); added += 1
            print(f"  [在线] 新增 {added} 期" + (f' 拒绝{rejected}' if rejected else ''))
        else:
            print(f"  [在线] 未获取到新数据")
    
    data.sort(key=lambda x: x[0])
    print(f"  [OK] 共 {len(data)} 期: {data[0][0]} ~ {data[-1][0]}")
    return data


def _validate_digit(d):
    """验证开奖数字: 必须是0-9的单个整数"""
    return isinstance(d, int) and 0 <= d <= 9


def _validate_issue(issue):
    """验证期号: 必须是7位数字"""
    return isinstance(issue, str) and len(issue) == 7 and issue.isdigit()


def update_embedded(data, script_path=None):
    """自动更新EMBEDDED嵌入式数据，确保永远最新。硬防线：防止乱码。"""
    if script_path is None:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    
    # 从all_data提取最新期号
    latest_embedded = EMBEDDED[-1][0] if EMBEDDED else ""
    new_entries = []
    for rec in data:
        issue = rec[0]
        if issue > latest_embedded:
            date = rec[1]
            digits = rec[2]
            # 严格校验：防止乱码数据写入EMBEDDED
            if not _validate_issue(issue):
                continue
            if len(digits) != 3 or not all(_validate_digit(d) for d in digits):
                continue
            new_entries.append((issue, date, digits))
    
    if not new_entries:
        return 0
    
    # 读取当前脚本
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到EMBEDDED结束标记并插入新条目
    marker = "\n]"
    marker_pos = content.rfind(marker)
    if marker_pos == -1:
        return 0
    
    # 构建新条目文本
    new_lines = []
    for issue, date, digits in new_entries:
        new_lines.append(f'    ["{issue}","{date}",{digits}],')
    
    insert_text = "\n" + "\n".join(new_lines)
    
    # 插入到]之前
    new_content = content[:marker_pos] + insert_text + content[marker_pos:]
    
    # 原子写入: 先写tmp再替换, 防止中断损坏
    tmp_path = script_path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    os.replace(tmp_path, script_path)
    
    print(f"  [EMBEDDED] 自动补全 {len(new_entries)} 期: {new_entries[0][0]}~{new_entries[-1][0]}")
    return len(new_entries)


# ============================================================
# v8 信号计算引擎
# ============================================================

def _norm(raw_dict):
    vals = list(raw_dict.values())
    mn, mx = min(vals), max(vals)
    if mx == mn: return {d: 0.5 for d in raw_dict}
    return {d: (v - mn) / (mx - mn) for d, v in raw_dict.items()}


def compute_signals_v8(history):
    """5维信号计算 — 消除冗余后的精简信号集"""
    n = len(history)
    if n < 15: return None

    # ── 1. 综合趋势信号 (合并exp_freq + cycle_v2 + pos_v2) ──
    # 1a: 指数衰减频率
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

    # 1b: 自适应周期共振
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

    # 1c: 位置频率
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

    # 三合一趋势
    trend_composite = {}
    for d in range(10):
        trend_composite[d] = (0.40 * _norm(exp_freq)[d] + 
                             0.35 * _norm(cycle_v2)[d] + 
                             0.25 * _norm(pos_raw)[d])
    trend = _norm(trend_composite)

    # ── 2. 冷号回补v4 (rank归一化消除数字偏见) ──
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
            # 排名归一化: 用(cur/avg)代替概率，消除频次偏见
            ratio = cur_gap / max(avg, 1.0)
            rank_score = min(1.0, ratio / 3.0)  # ratio=3→1.0
            cold_raw[d] = 0.6 * rank_score + 0.4 * math.tanh(z_score * 0.5)
        elif len(gaps_all[d]) >= 1:
            avg = sum(gaps_all[d]) / len(gaps_all[d])
            cold_raw[d] = min(0.8, cur_gap / max(avg * 2, 1.0))
        else:
            cold_raw[d] = 0.3 if cur_gap > 5 else 0.0
    cold_v3 = _norm(cold_raw)

    # ── 3. 边码跟随 ──
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

    # ── 4. 和值尾数信号 ──
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

    # ── 5. 趋势加速 ──
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
# v8 共识增强融合
# ============================================================

def fuse_v10(signals, div_history=None):
    """
    v10 动态保护融合:
    - cold_v3 top-2 直接入选
    - cold#3 如果得分接近#2(>85%)→扩容到3
    - edge top-1 直接入选(排除已保证的)
    - edge#2 如果得分接近#1(>80%)→扩容到2
    - 剩余名额由集成打分填充
    """
    # 冷号保证
    cold_ranked = sorted(range(10), key=lambda x: signals['cold_v3'][x], reverse=True)
    guaranteed = set(cold_ranked[:GUARANTEED_COLD])
    
    # 动态扩容: cold#3接近时加入
    cv = signals['cold_v3']
    if (GUARANTEED_COLD + 1 < 10 and 
        cv[cold_ranked[GUARANTEED_COLD]] > cv[cold_ranked[GUARANTEED_COLD - 1]] * COLD_EXPAND_RATIO):
        guaranteed.add(cold_ranked[GUARANTEED_COLD])
    
    # 边码保证
    edge_ranked = sorted(range(10), key=lambda x: signals['edge'][x], reverse=True)
    edge_selected = None
    for d in edge_ranked:
        if d not in guaranteed:
            edge_selected = d
            guaranteed.add(d)
            break
    
    # 动态扩容: edge#2接近时加入
    ev = signals['edge']
    if edge_selected is not None:
        for d in edge_ranked:
            if d not in guaranteed and ev[d] > ev[edge_selected] * EDGE_EXPAND_RATIO:
                guaranteed.add(d)
                break

    # 集成打分
    base = {}
    for d in range(10):
        base[d] = sum(SUM_WEIGHTS[name] * signals[name][d] for name in SUM_WEIGHTS)
    base = _norm(base)

    # 多样性反偏
    if div_history:
        recent = div_history[-DIV_WINDOW:]
        rp = Counter()
        for picks in recent:
            for d in picks: rp[d] += 1
        if rp:
            mp = max(rp.values()) or 1
            for d in range(10):
                base[d] *= (1.0 - DIV_PENALTY * rp.get(d, 0) / mp)

    # 剩余名额
    remaining = sorted([d for d in range(10) if d not in guaranteed],
                       key=lambda x: base[x], reverse=True)
    needed = 6 - len(guaranteed)
    picks = list(guaranteed) + remaining[:needed]
    
    # === 奇偶平衡约束 ===
    # 176-182期cold_v3/edge偏好奇数导致全偶数开奖时0交集miss
    # 只防极端: 确保至少1偶1奇(不强制2-2避免破坏好预测)
    evens = [d for d in picks if d % 2 == 0]
    odds = [d for d in picks if d % 2 == 1]
    if len(evens) == 0:
        # 全奇数预测, 用最高分偶数替换最低分奇数
        worst_odd = min(odds, key=lambda x: base.get(x, 0))
        best_even = max([d for d in range(10) if d % 2 == 0 and d not in picks],
                        key=lambda x: base.get(x, 0))
        picks[picks.index(worst_odd)] = best_even
    elif len(odds) == 0:
        # 全偶数预测, 用最高分奇数替换最低分偶数
        worst_even = min(evens, key=lambda x: base.get(x, 0))
        best_odd = max([d for d in range(10) if d % 2 == 1 and d not in picks],
                       key=lambda x: base.get(x, 0))
        picks[picks.index(worst_even)] = best_odd
    
    return picks


def predict_math(history, div_history=None):
    """主预测器: 信号融合(v12.3, 经14种方案验证最优)"""
    return predict_v10(history, div_history)


def predict_v10(history, div_history=None):
    signals = compute_signals_v8(history)
    if signals is None:
        # 数据不足时用近期频次兜底, 不用盲目[0,1,2,3,4]
        if len(history) >= 5:
            freq = Counter()
            for rec in history[-10:]:
                for d in rec[2]: freq[d] += 1
            picks = [d for d, _ in freq.most_common(6)]
            return picks, None
        return list(range(6)), None
    picks = fuse_v10(signals, div_history=div_history)
    return picks, signals


# ============================================================
# 状态管理
# ============================================================

def get_state_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'predictions.json')


def load_state():
    path = get_state_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  [WARN] predictions.json损坏: {e}, 使用空状态恢复")
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
    """添加新预测。如果已存在未验证且picks不同，更新；相同则跳过。"""
    for p in state['predictions']:
        if p['issue'] == issue and not p.get('verified'):
            if p['picks'] != picks:
                # 更新预测（数据变化导致不同）
                p['picks'] = picks
                if signals:
                    p['signals'] = {name: {str(d): round(signals[name][d], 4) for d in range(10)}
                                    for name in SIGNAL_NAMES}
                p['predicted_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            return state
    if len(state['predictions']) > 200:
        state['predictions'] = state['predictions'][-200:]
    state['predictions'].append({
        'issue': issue,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'predicted_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'picks': picks,
        'signals': {name: {str(d): round(signals[name][d], 4) for d in range(10)}
                    for name in SIGNAL_NAMES} if signals else {},
        'actual': None, 'verified': False
    })
    return state


def fill_missing_predictions(state, all_data):
    """补全predictions.json中缺失的预测记录。根因：数据源延迟导致中间期被跳过。"""
    predicted_issues = {p['issue'] for p in state['predictions']}
    # 只检查最近20期（避免遍历全部历史）
    recent_data = all_data[-20:]
    missing = [rec for rec in recent_data if rec[0] not in predicted_issues]
    if not missing:
        return state
    
    print(f"  [补全] 缺失 {len(missing)} 期预测记录")
    data_by_issue = {d[0]: d for d in all_data}
    for rec in missing:
        issue = rec[0]
        idx = all_data.index(rec)
        data_before = all_data[:idx]
        if len(data_before) < 20:
            continue
        div_hist = state['stats'].get('recent_picks', [])
        p, s = predict_math(data_before, div_history=div_hist[-DIV_WINDOW:] if div_hist else None)
        state = add_prediction(state, issue, p, s)
        if div_hist:
            div_hist.append(p)
        print(f"    {issue}: {' '.join(str(d) for d in p)}")
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
        picks, _ = predict_math(hist, div_history=div_hist)
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
# HTML仪表盘
# ============================================================

def generate_html(all_data, bt100, state):
    algo_name = "去偏冷号融合 v16"
    v11_badge = '<span style="font-size:10px;background:rgba(255,255,255,.2);color:#fff;padding:1px 6px;border-radius:10px;margin-left:6px">v16 云端自动更新</span>'

    div_hist = state['stats'].get('recent_picks', [])
    next_picks, _ = predict_math(all_data, div_history=div_hist if div_hist else None)
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

    # 合并历史预测：predictions.json中的记录优先于回测重算
    hist_picks = {}
    for p in state.get('predictions', []):
        if p.get('verified') and p.get('picks'):
            hist_picks[p['issue']] = p['picks']

    det_html = ''
    for r in reversed(bt100['details']):
        # 如果有历史记录，用历史预测替代回测重算
        if r['issue'] in hist_picks:
            hp = hist_picks[r['issue']]
            actual_set = set(r['actual'])
            # 用历史picks重新计算命中
            r['picks'] = hp
            r['hit'] = any(d in actual_set for d in hp)
            r['n_hits'] = sum(1 for d in hp if d in actual_set)
        ast = ' '.join(str(d) for d in r['actual'])
        actual_set = set(r['actual'])
        pballs = ''.join(
            f'<span class="pb-hit">{d}</span>' if d in actual_set
            else f'<span class="pb-miss">{d}</span>' for d in r['picks'])
        cls = 'hit-yes' if r['hit'] else 'hit-no'
        mark = f'<span class="mk-yes">✓ {r["n_hits"]}个</span>' if r['hit'] else '<span class="mk-no">✗</span>'
        det_html += (f'<tr class="{cls}"><td>{r["issue"]}</td><td>{r["date"]}</td>'
                   f'<td class="ac">{ast}</td><td class="pc">{pballs}</td><td>{mark}</td></tr>')

    # 重新计算命中率（合并历史记录后）
    bt100_hit = sum(1 for r in bt100['details'] if r['hit'])
    hn, mn = bt100_hit, bt100['periods'] - bt100_hit
    hr = bt100_hit / bt100['periods'] * 100

    hot_nums = Counter()
    for r in bt100['details']:
        for d in r['picks']: hot_nums[d] += 1
    top_hot = sorted(hot_nums.items(), key=lambda x: x[1], reverse=True)[:6]
    hot_html = ''.join(f'<span class="ht">{d}<small>{c}次</small></span>' for d, c in top_hot)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>六胆码</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f8fafc;color:#334155;min-height:100vh}}
.header{{background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;padding:22px 16px;text-align:center}}
.header h1{{font-size:20px;font-weight:700;letter-spacing:2px;margin-bottom:4px}}
.header .sub{{font-size:11px;opacity:.55;font-weight:300}}
.container{{max-width:700px;margin:0 auto;padding:16px 16px 0}}

.pred-card{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:28px 22px 22px;margin:0 0 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.pred-card .label{{font-size:11px;color:#94a3b8;letter-spacing:5px;text-transform:uppercase;margin-bottom:6px}}
.pred-card .issue{{font-size:13px;color:#0d9488;font-weight:600;margin-bottom:16px}}
.balls{{display:flex;justify-content:center;gap:11px}}
.ball{{width:54px;height:54px;line-height:54px;border-radius:50%;background:linear-gradient(135deg,#1e293b,#334155);color:#fff;font-size:23px;font-weight:800;text-align:center;box-shadow:0 2px 8px rgba(30,41,59,.2)}}
.pred-card .footnote{{font-size:11px;color:#94a3b8;margin-top:16px}}

.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}}
.stat{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 8px 14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.03)}}
.stat .val{{font-size:25px;font-weight:800;line-height:1}}
.stat .lbl{{font-size:10px;color:#94a3b8;margin-top:5px}}
.stat.s1 .val{{color:#0d9488}}
.stat.s2 .val{{color:#6366f1}}
.stat.s3 .val{{color:#f59e0b}}
.stat.s4 .val{{color:#0ea5e9}}

.section{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 16px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.03)}}
.section .title{{font-size:14px;font-weight:700;margin-bottom:12px;padding-bottom:9px;border-bottom:1px solid #f1f5f9;color:#1e293b}}

.bar-row{{display:flex;gap:6px;height:32px}}
.bar{{flex:1;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff}}
.bar.hit{{background:linear-gradient(90deg,#0d9488,#14b8a6)}}
.bar.miss{{background:#f1f5f9;color:#94a3b8}}

.hot-tags{{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}}
.ht{{display:inline-flex;align-items:center;gap:3px;background:#f0fdfa;color:#0d9488;padding:5px 14px;border-radius:20px;font-size:14px;font-weight:700}}
.ht small{{font-size:10px;font-weight:400;opacity:.65}}

.tb-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#f8fafc;padding:10px 6px;text-align:center;font-weight:700;border-bottom:1px solid #e2e8f0;white-space:nowrap;font-size:11px;color:#64748b}}
td{{padding:9px 5px;text-align:center;border-bottom:1px solid #f1f5f9}}
.ac{{font-weight:800;color:#0d9488;letter-spacing:3px;font-size:13px}}
.pc{{color:#334155;letter-spacing:1px;display:flex;justify-content:center;gap:4px;flex-wrap:wrap}}
.pb-hit{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#0d9488,#14b8a6);color:#fff;font-weight:800;font-size:12px}}
.pb-miss{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#fef2f2;color:#ef4444;font-weight:700;font-size:12px;border:1.5px solid #fecaca}}
.hit-yes td{{background:#fafdfc}}
.mk-yes{{color:#0d9488;font-weight:700;font-size:11px}}
.mk-no{{color:#ef4444;font-weight:600;font-size:11px}}

.warn{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:11.5px;color:#92400e;text-align:center}}
.footer{{text-align:center;padding:20px 16px 30px;color:#94a3b8;font-size:10px;line-height:1.8}}

@media(max-width:600px){{
  .stats{{grid-template-columns:repeat(2,1fr)}}
  .ball{{width:44px;height:44px;line-height:44px;font-size:19px}}
  .balls{{gap:8px}}
  .pred-card{{padding:22px 14px 16px}}
  .section{{padding:14px 12px}}
}}
</style>
</head>
<body>
<div class="header">
  <h1>六胆码</h1>
  <div class="sub">{algo_name} · 6胆码 · rank冷号 · 动态保护{v11_badge}</div>
</div>

<div class="container">
  <div class="warn"><strong>⚠ 风险提示：</strong>彩票开奖具有随机性，本软件仅供数据分析参考，不构成投注建议。请理性购彩。</div>

  <div class="pred-card">
    <div class="label">▎下期预测胆码</div>
    <div class="issue">期号 {next_issue}</div>
    <div class="balls">
      {' '.join(f'<div class="ball">{d}</div>' for d in next_picks)}
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
    print("  福彩3D胆码预测系统 · v16 云端自动更新")
    print("  六胆码 · cold强制席2→3 · rank冷号 · 奇偶平衡")
    print("=" * 55)

    all_data = load_data()
    
    # 硬防线：自动更新EMBEDDED数据(防止乱码/数据断层)
    update_embedded(all_data)

    print(f"\n[学习] 加载历史状态...")
    state = load_state()
    
    # 补全缺失预测（根因：数据源延迟导致中间期被跳过）
    state = fill_missing_predictions(state, all_data)
    
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
    next_picks, signals = predict_math(all_data, div_history=div_hist if div_hist else None)
    next_issue = str(int(all_data[-1][0]) + 1)
    print(f"\n[预测] 下期 {next_issue} 6胆码: {' '.join(str(d) for d in next_picks)}")

    state = add_prediction(state, next_issue, next_picks, signals)
    save_state(state)

    html = generate_html(all_data, bt100, state)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    with open(out, 'w', encoding='utf-8') as f: f.write(html)

    print(f"\n✅ 已生成: {out}")
    print("=" * 55)
    return out


if __name__ == '__main__':
    main()
