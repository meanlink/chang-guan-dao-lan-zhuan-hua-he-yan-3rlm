"""漏记完成的区间核验：在登记上限内传播两方案完成率差的不确定性。

口径：每条客流的有效漏记上限 = min(登记上限, 进区−完成)，全批补记总量不超过全批上限。
完成率差 B−A 关于补记量是线性的，区间端点必在顶点取得：
下界把补记全部计入 A，上界把补记全部计入 B。方向用整数叉积精确判号。
"""
import math

ARMS = ("A", "B")
MAX_CAP = 1_000_000


def zones_of(records):
    return sorted({str(r.get("zone", "")) for r in records if str(r.get("zone", ""))})


def check_caps(records, caps, batch_cap):
    """校验登记上限：键须为批次内客流，值为非负整数。返回规范化 caps。"""
    if isinstance(batch_cap, bool) or not isinstance(batch_cap, int) or not 0 <= batch_cap <= MAX_CAP:
        raise ValueError(f"全批漏记上限须为 0 至 {MAX_CAP} 的整数")
    known = {str(r.get("record")) for r in records}
    clean = {}
    for key, value in (caps or {}).items():
        key = str(key)
        if key not in known:
            raise ValueError(f"客流 {key} 不在该数据批次中")
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_CAP:
            raise ValueError(f"客流 {key} 的漏记上限须为 0 至 {MAX_CAP} 的整数")
        if value:
            clean[key] = value
    return clean


def _flows(records, zone):
    flows = []
    for r in records:
        try:
            v, c = float(r["visitors"]), float(r["completed"])
            name, arm = str(r["zone"]), str(r["arm"])
            if arm not in ARMS or not all(math.isfinite(x) and x.is_integer() for x in (v, c)) or v <= 0 or not 0 <= c <= v:
                raise ValueError()
            flows.append({"record": str(r["record"]), "zone": name, "arm": arm, "visitors": int(v), "completed": int(c)})
        except (ValueError, TypeError, KeyError):
            raise ValueError("方案须为 A/B，人数为整数，且 0≤完成≤进区")
    return [f for f in flows if zone == "全部" or f["zone"] == zone]


def _plan(flows, eff_cap, arm, budget):
    """确定性的补记方案：按记录键序在目标方案内依次补满，直到全批预算用完。"""
    plan, left = [], budget
    for f in sorted((f for f in flows if f["arm"] == arm), key=lambda f: f["record"]):
        if left <= 0:
            break
        added = min(eff_cap[f["record"]], left)
        if added:
            plan.append({"record": f["record"], "zone": f["zone"], "arm": arm, "added": added})
            left -= added
    return plan, budget - left


def interval_conclusion(records, zone, caps, batch_cap):
    """两方案完成率差（B−A，百分点）的上下界、方向与两端补记方案。"""
    flows = _flows(records, zone)
    if not flows:
        raise ValueError("所选展区没有可用客流记录")
    caps = caps or {}
    totals = {a: {"visitors": 0, "completed": 0, "cap": 0} for a in ARMS}
    eff_cap, clamped = {}, 0
    for f in flows:
        t = totals[f["arm"]]
        t["visitors"] += f["visitors"]
        t["completed"] += f["completed"]
        cap = min(caps.get(f["record"], 0), f["visitors"] - f["completed"])
        clamped += caps.get(f["record"], 0) > cap
        eff_cap[f["record"]] = cap
        t["cap"] += cap
    if not totals["A"]["visitors"] or not totals["B"]["visitors"]:
        raise ValueError("所选展区须同时包含 A/B 两方案客流")
    va, vb = totals["A"]["visitors"], totals["B"]["visitors"]
    ca, cb = totals["A"]["completed"], totals["B"]["completed"]
    ends = {}
    for end, arm in (("lower", "A"), ("upper", "B")):
        budget = min(totals[arm]["cap"], batch_cap)
        plan, added = _plan(flows, eff_cap, arm, budget)
        ends[end] = {"arm": arm, "added_total": added, "plan": plan}
    xa, xb = ends["lower"]["added_total"], ends["upper"]["added_total"]
    # 下界：漏记全部补到 A（压低 A−B 差距方向）；上界：全部补到 B。
    lower, upper = cb / vb - (ca + xa) / va, (cb + xb) / vb - ca / va
    if cb * va > (ca + xa) * vb:
        direction = "positive"  # 区间整体在零以上：任意补记 B 均高于 A
    elif (cb + xb) * va < ca * vb:
        direction = "negative"  # 区间整体在零以下：任意补记 A 均高于 B
    else:
        direction = "unclear"  # 区间含零：方向不明
    lower_pp, upper_pp = round(lower * 100, 4), round(upper * 100, 4)
    for end, xa_, xb_ in (("lower", xa, 0), ("upper", 0, xb)):
        ends[end]["rate_a"] = round((ca + xa_) / va * 100, 4)
        ends[end]["rate_b"] = round((cb + xb_) / vb * 100, 4)
    text = {"positive": "任意补记下 B 均高于 A", "negative": "任意补记下 A 均高于 B", "unclear": "区间含 0，方向不明，不可批准"}[direction]
    warnings = ["区间只覆盖设备漏记的不确定性，不含抽样波动；方向不明时请收紧上限或补采数据。"]
    if clamped:
        warnings.append(f"{clamped} 条客流的登记上限超过其未完成人数，已按未完成人数截断。")
    return {"zone": zone, "batch_cap": batch_cap, "flows": len(flows), "totals": totals,
            "interval": {"lower": lower_pp, "upper": upper_pp, "unit": "百分点"},
            "direction": direction, "endpoints": ends,
            "metrics": [{"label": "区间下界", "value": lower_pp, "unit": "百分点"}, {"label": "区间上界", "value": upper_pp, "unit": "百分点"}, {"label": "全批漏记上限", "value": batch_cap, "unit": "人"}, {"label": "登记客流", "value": len(flows), "unit": "条"}],
            "summary": f"{zone}：B−A 完成率差区间 [{lower_pp}, {upper_pp}] 个百分点，{text}。",
            "method": "漏记完成在每条客流登记上限与全批上限内任意分配；完成率差 B−A 关于补记量线性，下界把补记全部计入 A、上界全部计入 B；区间含 0 判方向不明，仅区间整体在零的同一侧才可批准。",
            "warnings": warnings}
