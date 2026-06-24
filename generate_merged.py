#!/usr/bin/env python3
"""合并页面生成器 — 从两个predictions.json读取数据生成单页"""
import json, os, sys

def generate_merged():
    # 确保在部署目录
    deploy_dir = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(deploy_dir, 'predictions.json'), encoding='utf-8') as f:
        p5 = json.load(f)
    with open(os.path.join(deploy_dir, 'predictions_4d.json'), encoding='utf-8') as f:
        p4 = json.load(f)
    
    last5 = p5['predictions'][-1] if p5['predictions'] else {'picks':[0]*5, 'issue':'?'}
    last4 = p4['predictions'][-1] if p4['predictions'] else {'picks':[0]*4, 'issue':'?'}
    s5, s4 = p5['stats'], p4['stats']
    
    issue = last5['issue']
    picks5 = last5['picks']
    picks4 = last4['picks']
    
    # 五胆码实盘
    t5 = s5.get('total_verified', 0)
    h5 = s5.get('total_hits', 0)
    live5 = f"{h5/t5*100:.0f}%" if t5 > 0 else "--"
    r10_5 = s5.get('recent_10_hits', 0)
    
    # 四胆码实盘
    t4 = s4.get('total_verified', 0)
    h4 = s4.get('total_hits', 0)
    live4 = f"{h4/t4*100:.0f}%" if t4 > 0 else "--"
    r10_4 = s4.get('recent_10_hits', 0)
    
    # 从HTML读回测数据
    import re
    hr5, hc5, hp5 = "98.0", "98", "100"
    hr4, hc4, hp4 = "93.0", "93", "100"
    
    try:
        with open(os.path.join(deploy_dir, 'index.html'), encoding='utf-8') as f:
            h5t = f.read()
        m = re.search(r'(\d+\.?\d*)%.*?100期回测命中率', h5t)
        if m: hr5 = m.group(1)
        m = re.search(r'(\d+)/(\d+).*?回测命中期数', h5t)
        if m: hc5, hp5 = m.group(1), m.group(2)
    except: pass
    
    try:
        with open(os.path.join(deploy_dir, 'index_4d.html'), encoding='utf-8') as f:
            h4t = f.read()
        m = re.search(r'(\d+\.?\d*)%.*?100期回测命中率', h4t)
        if m: hr4 = m.group(1)
        m = re.search(r'(\d+)/(\d+).*?回测命中期数', h4t)
        if m: hc4, hp4 = m.group(1), m.group(2)
    except: pass
    
    # 生成HTML
    balls5 = ''.join(f'<span class="ball orange">{d}</span>' for d in picks5)
    balls4 = ''.join(f'<span class="ball blue">{d}</span>' for d in picks4)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>晓炜胆码</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f0f4f8;color:#1e293b;min-height:100vh;padding-bottom:30px}}
.header{{background:linear-gradient(135deg,#1a365d,#2c5282);color:#fff;padding:20px 16px 16px;text-align:center}}
.header h1{{font-size:18px;font-weight:800;letter-spacing:3px;margin-bottom:2px}}
.header p{{font-size:10px;opacity:.5}}
.container{{max-width:440px;margin:0 auto;padding:12px}}
.pred-section{{background:#fff;border-radius:14px;overflow:hidden;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.pred-head{{padding:14px 16px 8px;display:flex;justify-content:space-between;align-items:center}}
.pred-head .badge{{font-size:10px;font-weight:700;padding:4px 10px;border-radius:12px;letter-spacing:1px}}
.badge.orange{{background:#fff3e0;color:#e65100}}
.badge.blue{{background:#e3f2fd;color:#1565c0}}
.pred-head .issue{{font-size:15px;font-weight:800;color:#1e293b;letter-spacing:1px}}
.pred-head .issue span{{color:#e65100}}
.pred-body{{text-align:center;padding:4px 16px 18px}}
.pred-body .balls{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}}
.pred-body .ball{{width:50px;height:50px;line-height:50px;border-radius:50%;font-size:22px;font-weight:800;color:#fff;text-align:center;box-shadow:0 3px 10px rgba(0,0,0,.12)}}
.ball.orange{{background:linear-gradient(135deg,#e67e22,#d35400)}}
.ball.blue{{background:linear-gradient(135deg,#2563eb,#1d4ed8)}}
.pred-body .meta{{font-size:10px;color:#94a3b8;margin-top:10px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:8px 16px 14px}}
.stats .s{{background:#f8fafc;border-radius:10px;padding:12px 6px;text-align:center}}
.stats .s .v{{font-size:18px;font-weight:800}}
.stats .s .l{{font-size:9px;color:#94a3b8;margin-top:2px}}
.s.c1 .v{{color:#e65100}}
.s.c2 .v{{color:#2563eb}}
.warn{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:10px 14px;margin:0 16px 14px;font-size:10px;color:#92400e;text-align:center}}
.footer{{text-align:center;padding:20px;color:#94a3b8;font-size:9px;line-height:2}}
.footer a{{color:#64748b;text-decoration:none}}
</style>
</head>
<body>
<div class="header"><h1>晓炜胆码</h1><p>福彩3D · v12.0五胆+v14.1四胆 · 云端全自动</p></div>
<div class="container">
<div class="warn">⚠ 彩票有风险，本页面仅供数据参考，不构成投注建议。</div>

<div class="pred-section">
<div class="pred-head">
<span class="badge orange">五胆码 v12.0</span>
<span class="issue">下期 <span>{issue}</span></span>
</div>
<div class="pred-body">
<div class="balls">{balls5}</div>
<div class="meta">5维信号 · rank冷号 · 云端实时更新</div>
</div>
<div class="stats">
<div class="s c1"><div class="v">{hr5}%</div><div class="l">100期命中</div></div>
<div class="s c1"><div class="v">{hc5}/{hp5}</div><div class="l">命中期数</div></div>
<div class="s c1"><div class="v">{live5}</div><div class="l">实盘({t5}期)</div></div>
<div class="s c1"><div class="v">{r10_5}/10</div><div class="l">近10期</div></div>
</div>
</div>

<div class="pred-section">
<div class="pred-head">
<span class="badge blue">四胆码 v14.1</span>
<span class="issue">下期 <span>{issue}</span></span>
</div>
<div class="pred-body">
<div class="balls">{balls4}</div>
<div class="meta">cold2+edge1保证 · 悬崖共识 · 参数精调</div>
</div>
<div class="stats">
<div class="s c2"><div class="v">{hr4}%</div><div class="l">100期命中</div></div>
<div class="s c2"><div class="v">{hc4}/{hp4}</div><div class="l">命中期数</div></div>
<div class="s c2"><div class="v">{live4}</div><div class="l">实盘({t4}期)</div></div>
<div class="s c2"><div class="v">{r10_4}/10</div><div class="l">近10期</div></div>
</div>
</div>

<div style="background:#fff;border-radius:14px;padding:14px 16px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.06)">
<div style="font-size:13px;font-weight:700;margin-bottom:12px">📊 命中率对比 (100期回测)</div>
<div style="display:flex;align-items:center;justify-content:space-between;font-size:11px;font-weight:700;margin-bottom:4px">
<span style="color:#e65100">五胆码</span><span style="color:#e65100;font-size:14px">{hr5}%</span>
</div>
<div style="height:10px;background:#f1f5f9;border-radius:5px;margin-bottom:12px;overflow:hidden">
<div style="height:100%;width:{hr5}%;background:linear-gradient(90deg,#e67e22,#f39c12);border-radius:5px"></div>
</div>
<div style="display:flex;align-items:center;justify-content:space-between;font-size:11px;font-weight:700;margin-bottom:4px">
<span style="color:#2563eb">四胆码</span><span style="color:#2563eb;font-size:14px">{hr4}%</span>
</div>
<div style="height:10px;background:#f1f5f9;border-radius:5px;overflow:hidden">
<div style="height:100%;width:{hr4}%;background:linear-gradient(90deg,#2563eb,#3b82f6);border-radius:5px"></div>
</div>
</div>

<div class="footer">
晓炜工作室 · 甘肃平凉<br>
<a href="index.html">五胆码独立页</a> · <a href="index_4d.html">四胆码独立页</a><br>
生成于 <span id="t"></span>
</div>
</div>
<script>document.getElementById('t').textContent=new Date().toLocaleString('zh-CN')</script>
</body>
</html>'''
    
    out_path = os.path.join(deploy_dir, 'index_merged.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[合并] 已生成: {out_path}")
    return out_path

if __name__ == '__main__':
    generate_merged()
