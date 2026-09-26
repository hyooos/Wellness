"use client";

import { useEffect, useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const PERIODS = ["P1", "P2", "P3", "P4"];
const PERIOD_LABEL = { P1: "지정 2년 전", P2: "지정 직전", P3: "지정 1년차", P4: "지정 2년차" };
const STAGES = [
  ["관심", "숙박검색건수", "숙박 목적지 검색", "티맵"],
  ["방문", "외지인방문자수", "외지인 방문자", "KT"],
  ["숙박", "숙박자비율_pct", "숙박자 비율", "KT"],
  ["체류", "평균체류시간_분", "평균 체류시간", "KT"],
  ["소비", "방문자대비관광소비_천원_proxy", "방문자 대비 소비", "신한카드·KT"],
];
const LABEL = {
  숙박검색건수: "숙박 검색", 외지인방문자수: "외지인 방문", 숙박자비율_pct: "숙박자 비율",
  평균체류시간_분: "평균 체류시간", 평균숙박일수: "평균 숙박일수", 내국인관광소비_천원: "내국인 관광소비",
  방문자대비관광소비_천원_proxy: "방문자 대비 소비", 숙박자중_3박이상_pct: "숙박객 중 3박+",
  전체순방문자중_3박이상_pct: "장기체류 비율", DSI: "사계절 수요",
};
const TABLE_METRICS = ["숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "평균숙박일수", "내국인관광소비_천원", "방문자대비관광소비_천원_proxy", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "DSI"];
const LOG_METRICS = new Set(["숙박검색건수", "외지인방문자수", "내국인관광소비_천원"]);
const STATUS = { UP: ["오름", "↑", "up"], FLAT: ["유지", "→", "flat"], DOWN: ["내림", "↓", "down"], NA: ["자료 없음", "·", "na"] };
const INTERVALS = {
  immediate: { label: "지정 직후", before: "P2", after: "P3", growth: "g23_pct", point: "delta23_pctp", status: "지정직후_판정_3pct" },
  second: { label: "2년차", before: "P3", after: "P4", growth: "g34_pct", point: "delta34_pctp", status: "2년차_판정_3pct" },
};
const COLORS = { 관심: "#789184", 방문: "#4f7f91", 숙박: "#bd8a45", 체류: "#2f8f6b", 소비: "#916f83" };

function finite(value) { return typeof value === "number" && Number.isFinite(value); }
function formatLevel(value, metric) {
  if (!finite(value)) return "자료 없음";
  if (metric.endsWith("_pct")) return `${value < 10 ? value.toFixed(2) : value.toFixed(1)}%`;
  if (metric === "평균체류시간_분") return `${(value / 60).toFixed(1)}시간`;
  if (metric === "평균숙박일수") return `${value.toFixed(2)}일`;
  if (metric === "내국인관광소비_천원") return `${(value / 100000).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}억 원`;
  if (metric === "방문자대비관광소비_천원_proxy") return `${value.toFixed(2)}천 원`;
  if (metric === "외지인방문자수") return `${(value / 10000).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}만 명`;
  if (metric === "숙박검색건수") return `${Math.round(value).toLocaleString("ko-KR")}건`;
  if (metric === "DSI") return value.toFixed(3);
  return value.toLocaleString("ko-KR", { maximumFractionDigits: 1 });
}
function formatChange(value, metric) {
  if (!finite(value)) return "–";
  const sign = value > 0 ? "+" : "";
  return metric.endsWith("_pct") ? `${sign}${value.toFixed(2)}%p` : `${sign}${value.toFixed(1)}%`;
}
function ym(value) { const s = String(Math.trunc(value)); return `${s.slice(0, 4)}.${s.slice(4)}`; }
function strengthClass(value) { return ({ 강함: "strong", 중간: "medium", 약함: "weak" })[value] || "none"; }

function itsStrength(data, selected, metric, effect = "즉시수준변화") {
  const row = data.its.find(r => r.지역키 === selected && r.지표 === metric);
  if (!row) return "자료 없음";
  const q = effect === "즉시수준변화" ? row.즉시수준변화_q_BH : row.지정후_기울기변화_q_BH;
  const p = effect === "즉시수준변화" ? row.즉시수준변화_p : row.지정후_기울기변화_p;
  const n = data.robustness.filter(r => r.지역키 === selected && r.지표 === metric && r.계수 === effect).reduce((sum, r) => sum + (Number(r.p05_유의_lag수) || 0), 0);
  if (finite(q) && q < .05 && n >= 8) return "강함";
  if (n >= 6) return "중간";
  if (finite(p) && p < .1) return "약함";
  return "신호 없음";
}

function robustnessCount(data, selected, metric, effect) {
  return data.robustness.filter(r => r.지역키 === selected && r.지표 === metric && r.계수 === effect).reduce((sum, r) => sum + (Number(r.p05_유의_lag수) || 0), 0);
}

function periodChange(row, metric, interval) {
  if (!row) return null;
  return row[metric.endsWith("_pct") ? `delta${interval}_pctp` : `g${interval}_pct`];
}
function itsEffectText(row, metric, effect) {
  const immediate = effect === "즉시수준변화";
  const beta = immediate ? row?.즉시수준변화_beta : row?.지정후_기울기변화_beta;
  const converted = immediate ? row?.즉시변화_환산_pct : row?.기울기변화_월환산_pct;
  if (!finite(beta)) return "자료 없음";
  const suffix = immediate ? "" : "/월";
  if (LOG_METRICS.has(metric)) return `${converted > 0 ? "+" : ""}${Number(converted).toFixed(1)}%${suffix}`;
  if (metric.endsWith("_pct")) return `${beta > 0 ? "+" : ""}${Number(beta).toFixed(2)}%p${suffix}`;
  if (metric === "평균체류시간_분") return `${beta > 0 ? "+" : ""}${Number(beta).toFixed(1)}분${suffix}`;
  if (metric === "평균숙박일수") return `${beta > 0 ? "+" : ""}${Number(beta).toFixed(3)}일${suffix}`;
  return `${beta > 0 ? "+" : ""}${Number(beta).toFixed(3)}${suffix}`;
}

function plainItsResult(row, metric, effect, strength) {
  const immediate = effect === "즉시수준변화";
  if (!row) return { text: "자료 없음", strength: "" };
  if (strength === "신호 없음") return { text: `${immediate ? "지정 직후" : "지정 이후 흐름"} · ${itsEffectText(row, metric, effect)}`, strength: "뚜렷하지 않음" };
  const beta = immediate ? row.즉시수준변화_beta : row.지정후_기울기변화_beta;
  const direction = immediate
    ? (beta >= 0 ? "지정 직후 상승" : "지정 직후 하락")
    : (beta >= 0 ? "지정 이후 흐름 개선" : "지정 이후 흐름 둔화");
  const easyStrength = strength === "강함" ? "뚜렷함" : strength === "중간" ? "반복 확인" : "일부 신호";
  return { text: `${direction} · ${itsEffectText(row, metric, effect)}`, strength: easyStrength };
}

function SectionTitle({ number, title, subtitle }) {
  return <div className="section-title"><span>{number}</span><div><h2>{title}</h2><p>{subtitle}</p></div></div>;
}

function JeollaMap({ geo, sites, selected, onSelect }) {
  const width = 520, height = 380;
  const labelPosition = {
    전북완주: { x: -25, y: 5, anchor: "end" },
    전북무주: { x: 0, y: 35, anchor: "middle" },
    전북순창: { x: 0, y: 35, anchor: "middle" },
    전남완도: { x: 0, y: 35, anchor: "middle" },
  };
  const { paths, provincePaths, points } = useMemo(() => {
    if (!geo) return { paths: [], provincePaths: [], points: [] };
    const projection = geoMercator().fitExtent([[22, 20], [width - 22, height - 20]], geo);
    const path = geoPath(projection);
    return {
      paths: geo.features.map((feature, index) => ({ index, d: path(feature), name: feature.properties.NAME_2 })),
      provincePaths: (geo.provinceFeatures || []).map((feature, index) => ({ index, d: path(feature) })),
      points: Object.entries(sites).map(([key, site]) => ({ key, site, xy: projection([site.longitude, site.latitude]) })),
    };
  }, [geo, sites]);
  const siteByCounty = Object.fromEntries(Object.entries(sites).map(([key, site]) => [site.geoName, key]));
  return <svg className="map-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="전라도 웰니스 관광지 지도">
    <defs><filter id="shadow"><feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity=".18" /></filter></defs>
    {paths.map(item => {
      const key = siteByCounty[item.name];
      return <path key={item.index} d={item.d} className={`county ${key ? "target" : ""} ${key === selected ? "selected" : ""}`} onClick={() => key && onSelect(key)} />;
    })}
    {provincePaths.map(item => <path key={`province-${item.index}`} d={item.d} className="province-outline" />)}
    {points.map(({ key, site, xy }) => {
      if (!xy) return null;
      const label = labelPosition[key];
      return <g key={key} className={`marker ${key === selected ? "selected" : ""}`} transform={`translate(${xy[0]} ${xy[1]})`} onClick={() => onSelect(key)}>
        <circle className="marker-halo" r={key === selected ? 24 : 19} />
        <text className="marker-leaf" y="7">🌿</text>
        <text className="marker-label" x={label.x} y={label.y} textAnchor={label.anchor}>{site.region}</text>
      </g>;
    })}
  </svg>;
}

function StageFlow({ data, selected, intervalKey }) {
  const interval = INTERVALS[intervalKey];
  const site = data.sites[selected];
  return <div className="stage-flow has-bottleneck">
    {STAGES.map(([stage, metric, description, source], i) => {
      const row = data.growth.find(r => r.지역키 === selected && r.지표 === metric);
      const change = row?.[metric.endsWith("_pct") ? interval.point : interval.growth];
      const code = row?.[interval.status] || "NA";
      const [label, arrow, cls] = STATUS[code] || STATUS.NA;
      const isBottleneck = site.bottleneck.includes(stage);
      const before = data.kpi.find(r => r.지역키 === selected && r.기간 === interval.before)?.[metric];
      const after = data.kpi.find(r => r.지역키 === selected && r.기간 === interval.after)?.[metric];
      return <div className={`stage-wrap ${isBottleneck ? "bottleneck-wrap" : ""}`} key={stage}>
        <div className={`stage-card ${cls} ${isBottleneck ? "bottleneck" : ""}`} tabIndex={0} aria-describedby={`stage-tip-${metric}`}>
          {isBottleneck && <div className="bneck-band">핵심 병목</div>}
          <div className="stage-top"><span>{stage}</span><em>{source}</em></div><div className="stage-change-row"><strong>{arrow} {formatChange(change, metric)}</strong><span className={`status-chip ${cls}`}>{label}</span></div>
          <small>{description}</small><div className="stage-values">{formatLevel(before, metric)} → {formatLevel(after, metric)}</div>
          <StageTooltip data={data} selected={selected} stage={stage} metric={metric} description={description} source={source} />
        </div>{i < STAGES.length - 1 && <span className="stage-arrow">›</span>}
      </div>;
    })}
  </div>;
}

function StageTooltip({ data, selected, stage, metric, description, source }) {
  const its = data.its.find(r => r.지역키 === selected && r.지표 === metric);
  const levelStrength = itsStrength(data, selected, metric, "즉시수준변화");
  const slopeStrength = itsStrength(data, selected, metric, "지정후기울기변화");
  const levelResult = plainItsResult(its, metric, "즉시수준변화", levelStrength);
  const slopeResult = plainItsResult(its, metric, "지정후기울기변화", slopeStrength);
  return <div className="stage-tooltip" id={`stage-tip-${metric}`} role="tooltip"><div className="tooltip-title">{stage} · {description}<span>{source}</span></div><table><tbody>{PERIODS.map(period => <tr key={period}><td>{PERIOD_LABEL[period]}</td><td>{formatLevel(data.kpi.find(r => r.지역키 === selected && r.기간 === period)?.[metric], metric)}</td></tr>)}</tbody></table>{its ? <><div className="tooltip-subtitle">월별 흐름 확인</div><div className="plain-results"><p><span>{levelResult.text}</span>{levelResult.strength && <b>{levelResult.strength}</b>}</p><p><span>{slopeResult.text}</span>{slopeResult.strength && <b>{slopeResult.strength}</b>}</p></div></> : <><div className="tooltip-subtitle">월별 흐름 확인</div><div className="tooltip-empty">같은 지표의 월별 검정 없음<br />총소비 흐름은 상세 탭에서 확인</div></>}<div className="tooltip-note">상세 통계는 ‘지정 시점 확인’ 탭에서 볼 수 있습니다.</div></div>;
}

function BottleneckEvidence({ data, selected, intervalKey }) {
  const site = data.sites[selected];
  const interval = INTERVALS[intervalKey];
  const rows = STAGES.filter(([stage]) => site.bottleneck.includes(stage)).map(([stage, metric, description]) => {
    const growth = data.growth.find(r => r.지역키 === selected && r.지표 === metric);
    const value = growth?.[metric.endsWith("_pct") ? interval.point : interval.growth];
    const code = growth?.[interval.status] || "NA";
    return { stage, metric, description, value, code, strength: itsStrength(data, selected, metric) };
  });
  const spread = data.spread.find(r => r.지역키 === selected && r.영역 === "소비" && r.변화구간 === (intervalKey === "immediate" ? "g23" : "g34"));
  return <div className="detail-body"><div className="table-scroll"><table className="detail-table"><thead><tr><th>핵심 병목</th><th>지정 직전</th><th>1년차</th><th>2년차</th><th>{interval.label}</th><th>지정 시점 확인</th></tr></thead><tbody>{rows.map(r => <tr key={r.metric}><td><b>{r.stage}</b><small>{r.description}</small></td><td>{formatLevel(data.kpi.find(k => k.지역키 === selected && k.기간 === "P2")?.[r.metric], r.metric)}</td><td>{formatLevel(data.kpi.find(k => k.지역키 === selected && k.기간 === "P3")?.[r.metric], r.metric)}</td><td>{formatLevel(data.kpi.find(k => k.지역키 === selected && k.기간 === "P4")?.[r.metric], r.metric)}</td><td className={`change-cell ${STATUS[r.code]?.[2] || "na"}`}>{formatChange(r.value, r.metric)}</td><td><span className={`strength strength-${strengthClass(r.strength)}`}>{r.strength}</span></td></tr>)}</tbody></table></div><p className="evidence-note">{site.evidence}</p>{spread && <p className="spread-note"><b>보조 정보 · 시설지 소비 집중도</b> · {spread.시설소재_읍면동}의 군 소비 비중이 {Number(spread.시설동_점유율_before_pct).toFixed(1)}%에서 {Number(spread.시설동_점유율_after_pct).toFixed(1)}%로 변했습니다. 성과 단계가 아닌 소비 위치를 설명하는 참고 정보입니다.</p>}</div>;
}

function CheckPanel({ data, selected }) {
  const site = data.sites[selected];
  const metric = site.checkMetric;
  const value = period => data.kpi.find(r => r.지역키 === selected && r.기간 === period)?.[metric];
  const target = value("P2"), current = value("P4");
  const values = PERIODS.map(value).filter(finite);
  const low = Math.min(...values), high = Math.max(target, current), span = high - low || 1;
  const lo = low - span * .35, hi = high + span * .15;
  const position = v => Math.max(0, Math.min(100, (v - lo) / (hi - lo) * 100));
  const recovered = current >= target * .97;
  const gap = metric.endsWith("_pct") ? `${current - target >= 0 ? "+" : ""}${(current - target).toFixed(2)}%p` : `${current / target - 1 >= 0 ? "+" : ""}${((current / target - 1) * 100).toFixed(1)}%`;
  return <div className="panel check"><span className="eyebrow">다음 점검 지표</span><div className="check-box" tabIndex={0}><div className="check-row"><h3>{LABEL[metric]}</h3><span className={`check-state ${recovered ? "recovered" : "pending"}`}>{recovered ? "회복" : "아직 미회복"}</span></div><p>목표: 지정 직전 수준 회복 · 지금 목표 대비 <b className={recovered ? "positive" : "negative"}>{gap}</b></p><div className="bar-track"><i className={recovered ? "recovered" : "pending"} style={{ width: `${position(current)}%` }} /><b style={{ left: `${position(target)}%` }} /></div><div className="bar-labels"><span>지금(2년차) <b>{formatLevel(current, metric)}</b></span><span>목표(지정 직전) <b>{formatLevel(target, metric)}</b></span></div><div className="check-tooltip" role="tooltip"><div className="tooltip-title">{LABEL[metric]} · 네 구간</div><table><tbody>{PERIODS.map(period => <tr key={period}><td>{PERIOD_LABEL[period]}</td><td>{formatLevel(value(period), metric)}</td></tr>)}</tbody></table><div className="tooltip-note">검은 세로선이 목표인 지정 직전 값입니다.</div></div></div><h4 className="check-order">점검 순서</h4><div className="steps">{site.actions.map(([when, what], i) => <div className={`step ${i === 0 ? "now" : ""}`} key={when}><span>{i + 1}</span><p><small>{when}</small><b>{what}</b></p></div>)}</div></div>;
}

function MatrixTooltip({ data, regionKey, stage, metric, intervalKey, bottleneck }) {
  const interval = INTERVALS[intervalKey];
  const before = data.kpi.find(r => r.지역키 === regionKey && r.기간 === interval.before)?.[metric];
  const after = data.kpi.find(r => r.지역키 === regionKey && r.기간 === interval.after)?.[metric];
  const code = data.growth.find(r => r.지역키 === regionKey && r.지표 === metric)?.[interval.status] || "NA";
  return <div className="matrix-tooltip" role="tooltip"><div className="tooltip-title">{data.sites[regionKey].region} · {stage}{bottleneck ? " · 핵심 병목" : ""}</div><p>{LABEL[metric]}: <b>{formatLevel(before, metric)} → {formatLevel(after, metric)}</b> ({STATUS[code]?.[0] || "자료 없음"})</p></div>;
}

function formatEok(value, signed = true) {
  if (!finite(Number(value))) return "–";
  const eok = Number(value) / 100000;
  const sign = signed && eok > 0 ? "+" : "";
  return `${sign}${eok.toLocaleString("ko-KR", { maximumFractionDigits: 1 })}억 원`;
}

function SpendingCategories({ data, selected, intervalKey, onIntervalChange }) {
  const intervalName = intervalKey === "immediate" ? "P2→P3" : "P3→P4";
  const rows = data.categoryChange.filter(r => r.지역키 === selected && r.변화구간 === intervalName && finite(Number(r.실제변화_천원)));
  const decreases = [...rows].filter(r => Number(r.실제변화_천원) < 0).sort((a, b) => Number(a.실제변화_천원) - Number(b.실제변화_천원)).slice(0, 3);
  const increases = [...rows].filter(r => Number(r.실제변화_천원) > 0).sort((a, b) => Number(b.실제변화_천원) - Number(a.실제변화_천원)).slice(0, 3);
  const total = rows.reduce((sum, row) => sum + Number(row.실제변화_천원), 0);
  const maxAbs = Math.max(1, ...decreases.concat(increases).map(r => Math.abs(Number(r.실제변화_천원))));
  const dominant = total < 0 ? decreases[0] : increases[0];
  const renderRows = (items, direction) => <div className="category-list">{items.map(row => {
    const value = Number(row.실제변화_천원);
    return <div className={`category-row ${direction}`} key={row.중분류} tabIndex={0}>
      <div className="category-name"><b>{row.중분류}</b><span>{Number(row.성장률_pct) > 0 ? "+" : ""}{Number(row.성장률_pct).toFixed(1)}%</span></div>
      <div className="category-track"><i style={{ width: `${Math.abs(value) / maxAbs * 100}%` }} /></div>
      <strong>{formatEok(value)}</strong>
      <div className="category-tooltip" role="tooltip"><b>{row.중분류}</b><span>{formatEok(row.before_천원, false)} → {formatEok(row.after_천원, false)}</span><em>증감 {formatEok(value)} · {Number(row.성장률_pct) > 0 ? "+" : ""}{Number(row.성장률_pct).toFixed(1)}%</em></div>
    </div>;
  })}</div>;
  return <div className="spending-detail">
    <div className="detail-heading"><div><span className="eyebrow">시군구 내국인 관광소비</span><h3>소비 변화는 어디서 발생했나</h3></div><div className="spending-controls"><div className="segmented compact"><button className={intervalKey === "immediate" ? "active" : ""} onClick={() => onIntervalChange("immediate")}>지정 직후</button><button className={intervalKey === "second" ? "active" : ""} onClick={() => onIntervalChange("second")}>2년차</button></div><div className={`total-change ${total >= 0 ? "positive" : "negative"}`}><small>업종 합계</small><b>{formatEok(total)}</b></div></div></div>
    {dominant && <p className="insight-line"><b>{dominant.중분류}</b>이(가) 가장 큰 {total < 0 ? "감소" : "증가"} 요인입니다. 업종 전체가 같은 방향으로 움직였는지 함께 확인하세요.</p>}
    <div className="category-columns"><div><h4>감소 기여 상위</h4>{decreases.length ? renderRows(decreases, "decrease") : <p className="empty compact">감소 업종이 없습니다.</p>}</div><div><h4>증가 기여 상위</h4>{increases.length ? renderRows(increases, "increase") : <p className="empty compact">증가 업종이 없습니다.</p>}</div></div>
    <p className="note"><b>읽는 법</b> · 막대는 증감률이 아니라 실제 증감액입니다. 마우스를 올리면 이전·이후 금액과 증감률을 볼 수 있습니다. 시설 결제액이 아닌 시설 소재 시군구의 내국인 관광소비입니다.</p>
  </div>;
}

function LodgingSupply({ data, selected }) {
  const supply = data.lodging[selected];
  const byRadius = radius => supply.current.find(r => Number(r.반경_km) === radius);
  const own = byRadius(5); const r2 = byRadius(2); const r5 = byRadius(5);
  const ownUnit = selected === "전북순창" ? "개 숙박 단위" : "실";
  const ownRooms = Number(own?.시설자체_예약가능객실수 || 0);
  const insight = {
    전북완주: "자체 숙박은 가능하지만 주변 외부 숙소가 매우 적습니다.",
    전북순창: "자체 숙박은 갖췄지만 주변 연계 숙소는 거의 없습니다.",
    전남완도: "주변 객실은 충분해 공급 부족만으로 숙박 전환을 설명하기 어렵습니다.",
    전북무주: "시설 내부 숙박 공급이 크고 주변 외부 숙소는 보조 역할을 합니다.",
  }[selected];
  const maxPeriod = Math.max(1, ...supply.periods.map(r => Number(r.주변외부_평균객실수) || 0));
  const external = supply.inventory.filter(r => r.시설자체여부 === "주변 외부").slice(0, 5);
  const sensitivity = supply.sensitivity;
  return <div className="lodging-detail">
    <div className="detail-heading"><div><span className="eyebrow">숙박 수요를 뒷받침하는 공급</span><h3>시설 안과 주변에 얼마나 머물 수 있나</h3></div><p className="supply-insight">{insight}</p></div>
    <div className="supply-cards">
      <div className="supply-card own"><small>시설 자체</small><b>{ownRooms ? `${ownRooms}${ownUnit}` : "자체 숙박 없음"}</b><span>{own?.시설자체_수용인원설명 !== "확인 안 됨" ? own?.시설자체_수용인원설명 : own?.시설자체_원자료상태}</span><em>{own?.시설자체_객실유형}</em></div>
      <div className="supply-card"><small>주변 외부 · 2km</small><b>{Number(r2?.주변외부_업체수 || 0)}곳 · {Number(r2?.주변외부_총객실수 || 0)}실</b><span>시설 대표지점 기준</span></div>
      <div className="supply-card"><small>주변 외부 · 5km</small><b>{Number(r5?.주변외부_업체수 || 0)}곳 · {Number(r5?.주변외부_총객실수 || 0)}실</b><span>{r5?.주변외부_업태별}</span></div>
    </div>
    {sensitivity && <div className={`boundary-note ${sensitivity.판정 === "안정" ? "stable" : "review"}`}><b>{sensitivity.판정 === "안정" ? "대형 부지 확인" : "부지 경계 확인 필요"}</b><span>{sensitivity.판정 === "안정" ? `부지 면적을 고려해도 5km 공급은 ${Number(sensitivity.대표점5km_외부객실수)}실로 같습니다.` : `대표점 기준 0실이지만 경계 인접 후보 ${Number(sensitivity["5km밖_최근접객실수"])}실이 있습니다.`}</span></div>}
    <div className="supply-lower"><div><h4>지정 전후 주변 외부 객실</h4><div className="supply-periods">{PERIODS.map(period => { const row = supply.periods.find(r => r.기간 === period); const value = Number(row?.주변외부_평균객실수 || 0); return <div key={period}><span>{PERIOD_LABEL[period]}{Number(row?.관측개월수) < Number(row?.필요개월수) ? ` · ${row.관측개월수}개월` : ""}</span><div><i style={{ width: `${value / maxPeriod * 100}%` }} /></div><b>{value.toFixed(1)}실</b></div>; })}</div></div>
      <div><h4>가까운 외부 숙박</h4>{external.length ? <div className="nearby-list">{external.map(row => <div key={`${row.사업장명}-${row.거리_km}`}><p><b>{row.사업장명}</b><span>{row.업태구분명}</span></p><strong>{Number(row.거리_km).toFixed(2)}km · {Number(row.총객실수)}실</strong></div>)}</div> : <p className="empty compact">대표지점 5km 안에 외부 숙박이 없습니다.</p>}</div></div>
    <p className="note"><b>자료 기준</b> · 시설 자체는 시설 안내자료, 주변 외부는 숙박업 인허가 자료입니다. 주변 공급은 시설 대표지점의 직선거리이며 성과 점수에는 넣지 않습니다.</p>
  </div>;
}

function DataQuality({ data, selected }) {
  const hasOrigin = (data.origins[selected] || []).length > 0;
  const hasSpread = data.spread.some(r => r.지역키 === selected);
  const rows = [
    ["관심 · 방문", "시군구 월별", "확보", "ok", "티맵 숙박 검색, KT 외지인 방문"],
    ["숙박 전환 · 체류", "시군구 월별", "확보", "ok", "KT 숙박자 비율·체류시간, 방문객 수 가중평균"],
    ["소비", "시군구 월별", "확보", "ok", "신한카드 내국인 관광소비, 업종별 포함"],
    ["소비 업종별 변화", "시군구 연간", "확보", "ok", "증감액을 중심으로 원인을 살피며 시설 결제액을 뜻하지 않음"],
    ["주변 숙박 공급", "시설 대표점 반경", "보조자료", "partial", "시설 안내자료와 숙박업 인허가 자료를 분리해 표시"],
    ["방문자 대비 소비", "시군구", "대리지표", "partial", "카드 이용자와 방문자가 달라 1인당 소비가 아님"],
    ["시설지 소비 집중도", "읍면동", hasSpread ? "참고" : "자료 없음", hasSpread ? "partial" : "missing", hasSpread ? "시설 소재 읍면의 소비 비중이며 성과 판정에는 사용하지 않음" : "지정 전후 구간과 맞는 읍면동 자료 없음"],
    ["방문 출발지", "시군구", hasOrigin ? "확보" : "자료 없음", hasOrigin ? "ok" : "missing", "검색 출발지는 광역별 조건부 분포라 광역마다 따로 비교"],
    ["지정 시점 확인", "시군구 월별 48개월", "구조변화 근거", "partial", "비교 지역이 없어 인과효과가 아닌 지정 전후 구조변화"],
    ["시설 자체 성과", "시설", "추후 과제", "missing", "시설 이용 실적은 별도 확보 필요"],
  ];
  return <div className="quality-grid"><div><h3>지표별 공간 단위와 확보 수준</h3><div className="table-scroll"><table className="quality-table"><thead><tr><th>지표</th><th>공간 단위</th><th>확보 수준</th><th>주의할 점</th></tr></thead><tbody>{rows.map(([metric, unit, level, cls, note]) => <tr key={metric}><td><b>{metric}</b></td><td>{unit}</td><td><span className={`quality-badge ${cls}`}>{level}</span></td><td>{note}</td></tr>)}</tbody></table></div></div><div><h3>핵심 병목의 원인을 확정하려면 필요한 자료</h3><div className="steps">{data.sites[selected].needs.map(([title, desc], i) => <div className="step" key={title}><span>{i + 1}</span><p><small>{title}</small><b>{desc}</b></p></div>)}</div><p className="note">추가 자료를 확보하기 전에는 핵심 병목의 <b>위치</b>까지만 말하고 <b>원인</b>은 확정하지 않습니다.</p></div></div>;
}

function FlowChart({ data, selected }) {
  const rows = PERIODS.map(period => {
    const source = data.kpi.find(r => r.지역키 === selected && r.기간 === period);
    const base = data.kpi.find(r => r.지역키 === selected && r.기간 === "P1");
    const row = { period: PERIOD_LABEL[period] };
    STAGES.forEach(([stage, metric]) => {
      row[stage] = finite(source?.[metric]) && base?.[metric] ? source[metric] / base[metric] * 100 : null;
      row[`${stage}Actual`] = source?.[metric];
    });
    return row;
  });
  return <div className="chart-box"><ResponsiveContainer width="100%" height={330}><LineChart data={rows} margin={{ top: 18, right: 24, left: 0, bottom: 8 }}>
    <CartesianGrid stroke="#e4ece7" vertical={false} /><XAxis dataKey="period" tick={{ fill: "#61766b", fontSize: 12 }} /><YAxis tick={{ fill: "#61766b", fontSize: 12 }} domain={["auto", "auto"]} unit="" />
    <ReferenceArea x1="지정 1년차" x2="지정 2년차" fill="#2f8f6b" fillOpacity={.055} />
    <ReferenceLine y={100} stroke="#aebdb5" strokeDasharray="4 5" />
    <Tooltip content={<FlowTooltip />} /><Legend iconType="circle" />
    {STAGES.map(([stage]) => { const bottleneck = data.sites[selected].bottleneck.includes(stage); return <Line key={stage} type="monotone" dataKey={stage} stroke={bottleneck ? "#d2513a" : COLORS[stage]} strokeWidth={bottleneck ? 4.5 : 2.2} strokeOpacity={bottleneck ? 1 : .78} dot={{ r: bottleneck ? 5 : 3.5, fill: bottleneck ? "#d2513a" : COLORS[stage], strokeWidth: 0 }} activeDot={{ r: 6 }} />; })}
  </LineChart></ResponsiveContainer></div>;
}

function FlowTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><b>{label}</b>{payload.filter(item => finite(item.value)).map(item => {
    const metric = STAGES.find(([stage]) => stage === item.dataKey)?.[1];
    return <div key={item.dataKey}><i style={{ background: item.color }} /><span>{item.dataKey}</span><strong>지수 {Number(item.value).toFixed(1)}</strong><em>실제 {formatLevel(item.payload[`${item.dataKey}Actual`], metric)}</em></div>;
  })}<small>지수는 지정 2년 전을 100으로 환산한 값입니다.</small></div>;
}

function solveLinear(matrix, vector) {
  const n = vector.length;
  const a = matrix.map((row, i) => [...row, vector[i]]);
  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
    if (Math.abs(a[pivot][col]) < 1e-10) return null;
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const divisor = a[col][col];
    for (let j = col; j <= n; j += 1) a[col][j] /= divisor;
    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = a[row][col];
      for (let j = col; j <= n; j += 1) a[row][j] -= factor * a[col][j];
    }
  }
  return a.map(row => row[n]);
}

function seasonalItsRows(data, selected, metric, intervention) {
  const raw = data.monthly.filter(r => r.지역키 === selected).map(r => ({ month: String(r.기준년월), actual: Number(r[metric]) }));
  const valid = raw.map((r, i) => ({ ...r, i })).filter(r => finite(r.actual));
  if (valid.length < 24) return raw;
  const startIndex = raw.findIndex(r => r.month >= intervention);
  if (startIndex < 0) return raw;
  const design = valid.map(r => {
    const post = r.i >= startIndex ? 1 : 0;
    const monthNumber = Number(r.month.slice(4));
    return [1, r.i, post, post ? r.i - startIndex : 0, ...Array.from({ length: 11 }, (_, j) => monthNumber === j + 2 ? 1 : 0)];
  });
  const target = valid.map(r => LOG_METRICS.has(metric) ? Math.log1p(r.actual) : r.actual);
  const size = design[0].length;
  const xtx = Array.from({ length: size }, () => Array(size).fill(0));
  const xty = Array(size).fill(0);
  design.forEach((x, row) => x.forEach((xj, j) => {
    xty[j] += xj * target[row];
    x.forEach((xk, k) => { xtx[j][k] += xj * xk; });
  }));
  const beta = solveLinear(xtx, xty);
  if (!beta) return raw;
  const predict = x => {
    const value = x.reduce((sum, term, i) => sum + term * beta[i], 0);
    return LOG_METRICS.has(metric) ? Math.expm1(value) : value;
  };
  return raw.map((row, i) => {
    const post = i >= startIndex ? 1 : 0;
    const monthNumber = Number(row.month.slice(4));
    const seasonal = Array.from({ length: 11 }, (_, j) => monthNumber === j + 2 ? 1 : 0);
    const fitted = predict([1, i, post, post ? i - startIndex : 0, ...seasonal]);
    const counter = post ? predict([1, i, 0, 0, ...seasonal]) : null;
    return { ...row, fitted, counter };
  });
}

function DesignationLabel({ viewBox }) {
  if (!viewBox) return null;
  const x = (viewBox.x || 0) + 7, y = (viewBox.y || 0) + 7;
  return <g pointerEvents="none"><rect x={x} y={y} width="58" height="23" rx="7" fill="#14261e" /><text x={x + 29} y={y + 15} fill="#fff" fontSize="11" fontWeight="750" textAnchor="middle">지정 시점</text></g>;
}

function MonthlyChart({ data, selected, metric }) {
  const intervention = String(data.its.find(r => r.지역키 === selected)?.개입시작월 || "");
  const rows = seasonalItsRows(data, selected, metric, intervention);
  return <div className="chart-box"><ResponsiveContainer width="100%" height={330}><LineChart data={rows} margin={{ top: 28, right: 82, left: 2, bottom: 8 }}>
    <CartesianGrid stroke="#e4ece7" vertical={false} /><XAxis dataKey="month" interval={5} tickFormatter={v => `${String(v).slice(2, 4)}.${String(v).slice(4)}`} tick={{ fill: "#61766b", fontSize: 11 }} />
    <YAxis tick={{ fill: "#61766b", fontSize: 11 }} width={54} /><Tooltip labelFormatter={v => `${String(v).slice(0, 4)}.${String(v).slice(4)}`} formatter={(v, name) => [formatLevel(Number(v), metric), name]} />
    <ReferenceLine x={intervention} stroke="#d2513a" strokeWidth={1.5} strokeDasharray="5 5" label={<DesignationLabel />} />
    <Line type="linear" dataKey="fitted" name="계절 반영 추정선" stroke="#2f8f6b" strokeWidth={2.5} dot={false} connectNulls />
    <Line type="linear" dataKey="counter" name="지정 전 흐름이 이어졌다면" stroke="#d2513a" strokeWidth={2} strokeDasharray="6 5" dot={false} connectNulls />
    <Line type="linear" dataKey="actual" name="실제 값" stroke="#8fa39a" strokeOpacity={0} strokeWidth={1} dot={{ r: 3.2, fill: "#8fa39a", strokeWidth: 0 }} activeDot={{ r: 5, fill: "#61766b" }} />
    <Legend iconType="circle" />
  </LineChart></ResponsiveContainer></div>;
}

export default function Dashboard() {
  const [data, setData] = useState(null); const [geo, setGeo] = useState(null);
  const [selected, setSelected] = useState("전북완주"); const [intervalKey, setIntervalKey] = useState("immediate");
  const [tab, setTab] = useState("flow"); const [metric, setMetric] = useState("숙박자비율_pct");
  useEffect(() => { Promise.all([fetch("/data/dashboard.json").then(r => r.json()), fetch("/data/jeolla.geojson").then(r => r.json())]).then(([d, g]) => { setData(d); setGeo(g); }); }, []);
  useEffect(() => { if (data) setMetric(data.sites[selected].checkMetric); }, [selected, data]);
  if (!data) return <main className="loading">WELL-FLOW 데이터를 불러오는 중입니다.</main>;
  const site = data.sites[selected]; const periods = data.periods.filter(r => r.지역키 === selected);
  const period = Object.fromEntries(periods.map(r => [r.기간, r])); const interval = INTERVALS[intervalKey];
  const kpi = (periodName, m) => data.kpi.find(r => r.지역키 === selected && r.기간 === periodName)?.[m];
  const change = (key, m) => { const row = data.growth.find(r => r.지역키 === key && r.지표 === m); return row?.[m.endsWith("_pct") ? interval.point : interval.growth]; };
  const status = (key, m) => data.growth.find(r => r.지역키 === key && r.지표 === m)?.[interval.status] || "NA";
  const warningRows = STAGES.map(([stage, m]) => {
    const row = data.growth.find(r => r.지역키 === selected && r.지표 === m);
    return { stage, metric: m, y1: row?.g23_pct, y2: kpi("P2", m) && kpi("P4", m) ? (kpi("P4", m) / kpi("P2", m) - 1) * 100 : null, isDown: row?.지정직후_판정_3pct === "DOWN" };
  }).filter(r => r.isDown && finite(r.y1));
  const its = data.its.find(r => r.지역키 === selected && r.지표 === metric);
  const levelStrength = itsStrength(data, selected, metric, "즉시수준변화");
  const slopeStrength = itsStrength(data, selected, metric, "지정후기울기변화");
  const levelRobustness = robustnessCount(data, selected, metric, "즉시수준변화");
  const slopeRobustness = robustnessCount(data, selected, metric, "지정후기울기변화");
  const tabs = [["flow", "흐름 추이"], ["its", "지정 시점 확인"], ["wellness", "웰니스 지표"], ["lodging", "숙박 공급"], ["spending", "소비 업종"], ["market", "방문 출발지·주변 환경"], ["table", "기간별 수치 비교"], ["quality", "데이터 신뢰도"]];

  return <main>
    <header className="topbar"><div className="brand"><b>WELL-FLOW <span>Monitor</span></b><p>웰니스 관광지 성과 진단</p></div><div className="top-meta">{site.region} 분석기간 · {ym(period.P1.시작월)}–{ym(period.P4.종료월)} · 지정월 기준</div></header>
    <div className="map-label"><b>전라도 웰니스 관광지 위치</b><span>진한 초록 · 현재 선택</span></div>
    <section className="hero-grid">
      <div className="panel map-panel"><JeollaMap geo={geo} sites={data.sites} selected={selected} onSelect={setSelected} /></div>
      <div className="panel site-panel">
        <div className="site-main"><img src={`/sites/${site.image}`} alt={site.site} /><div className="site-copy"><span className="card-label">선택 관광지</span><h1>{site.site}</h1><p className="location">{site.region} {site.dong} · {site.year}년 지정 · {site.theme} 테마</p><p className="address">{site.address}</p><div className="site-pills"><span className="site-pill type">{site.type}</span>{site.caseNote && <span className="site-pill case-note">{site.caseNote}</span>}<span className="site-pill bottleneck">핵심 병목 · {site.bottleneckLabel}</span></div></div></div>
        <p className="site-headline">{site.headline}</p>
        <div className="site-chips"><div><small>핵심 병목</small><b>{site.bottleneckLabel}</b></div><div><small>확인 강도</small><b><span className={`strength strength-${strengthClass(site.strength)}`}>{site.strength}</span></b></div><div><small>다음 점검 지표</small><b>{LABEL[site.checkMetric]}</b></div></div>
      </div>
    </section>

    <SectionTitle number="1" title="병목 진단" subtitle="지정 전후 다섯 단계의 변화 · 카드에 마우스를 올리면 네 구간 값과 통계 근거를 볼 수 있습니다" />
    <section className="panel diagnosis-panel"><div className="diagnosis-head"><div><span className="eyebrow">비교 구간</span><div className="segmented"><button className={intervalKey === "immediate" ? "active" : ""} onClick={() => setIntervalKey("immediate")}>지정 직후</button><button className={intervalKey === "second" ? "active" : ""} onClick={() => setIntervalKey("second")}>2년차</button></div></div></div><div className="flow-banner"><p>핵심 병목은 <em>{site.bottleneckLabel}</em>입니다.</p><div className="stage-legend"><span><i className="up" />오름 (+3% 초과)</span><span><i className="flat" />유지</span><span><i className="down" />내림 (−3% 미만)</span><span><i className="na" />자료 없음</span><span><i className="bottleneck" />핵심 병목</span></div></div><StageFlow data={data} selected={selected} intervalKey={intervalKey} /><details><summary>핵심 병목 근거 자세히 보기</summary><BottleneckEvidence data={data} selected={selected} intervalKey={intervalKey} /></details></section>

    <SectionTitle number="2" title="검토 방향" subtitle="핵심 병목을 더 확인하기 위한 검토 사항과 다음 점검 지표" />
    <section className="two-col">
      <div className="panel response"><div className="response-lead"><small>핵심 병목 · 확인 강도 {site.strength}</small><h3>{site.bottleneckLabel}</h3><p>{site.headline}</p></div><div className="response-grid"><div><h4>우선 확인</h4>{site.recommend.map(([title, desc], i) => <div className="action" key={title}><span>{i + 1}</span><p><b>{title}</b><small>{desc}</small></p></div>)}</div><div className="low"><h4>현재 후순위 검토</h4><div className="action"><span>×</span><p><b>{site.avoid[0]}</b><small>{site.avoid[1]}</small></p></div></div></div><p className="good"><b>이미 괜찮은 칸</b> · {site.good}</p></div>
      <CheckPanel data={data} selected={selected} />
    </section>

    <SectionTitle number="3" title="조기 경보 · 지역 비교" subtitle="1년차 하락 지표의 2년차 회복 여부와 네 지역 차이" />
    <section className="compare-grid">
      <div className="panel warning"><span className="eyebrow">1년차 하락 지표</span>{warningRows.length ? <table><thead><tr><th>단계</th><th>1년차</th><th>2년 누적</th><th>판정</th></tr></thead><tbody>{warningRows.map(r => <tr key={r.metric}><td><b>{r.stage}</b><small>{LABEL[r.metric]}</small></td><td className="negative">{r.y1 > 0 ? "+" : ""}{r.y1.toFixed(1)}%</td><td>{r.y2 > 0 ? "+" : ""}{r.y2.toFixed(1)}%</td><td><span className={`pill ${r.y2 >= -3 ? "up" : "down"}`}>{r.y2 >= -3 ? "회복" : "미회복"}</span></td></tr>)}</tbody></table> : <p className="empty">지정 1년차에 내려간 단계가 없습니다.</p>}<p className="note">2년차 누적이 지정 직전 대비 −3% 이내면 회복으로 봅니다.</p></div>
      <div className="panel matrix"><span className="eyebrow">4개 지역 비교 · {interval.label}</span><div className="table-scroll"><table><thead><tr><th>지역</th>{STAGES.map(([s]) => <th key={s}>{s}</th>)}<th>진단 유형</th></tr></thead><tbody>{Object.entries(data.sites).map(([key, s]) => <tr key={key} className={key === selected ? "selected-row" : ""} onClick={() => setSelected(key)}><td><b>{s.region}</b><small>{s.site}</small>{s.caseNote && <em className="case-inline">{s.caseNote}</em>}</td>{STAGES.map(([stage, m]) => { const code = status(key, m); const bottleneck = s.bottleneck.includes(stage); return <td key={m} tabIndex={0} className={`signal ${STATUS[code][2]} ${bottleneck ? "bottleneck" : ""}`}><b>{STATUS[code][1]}</b><small>{formatChange(change(key, m), m)}</small><MatrixTooltip data={data} regionKey={key} stage={stage} metric={m} intervalKey={intervalKey} bottleneck={bottleneck} /></td>; })}<td>{s.type}</td></tr>)}</tbody></table></div></div>
    </section>

    <SectionTitle number="4" title="상세 근거" subtitle="지표를 선택해 변화의 크기와 데이터 범위를 확인합니다" />
    <section className="panel evidence"><div className="tabs">{tabs.map(([key, title]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{title}</button>)}</div>
      {tab === "flow" && <><p className="tab-help">다섯 단계를 첫 구간=100으로 맞췄습니다. 굵은 선은 핵심 병목입니다.</p><FlowChart data={data} selected={selected} /></>}
      {tab === "its" && <><div className="metric-select"><label>지표</label><select value={metric} onChange={e => setMetric(e.target.value)}>{["숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "평균숙박일수", "내국인관광소비_천원"].map(m => <option key={m} value={m}>{LABEL[m]}</option>)}</select></div><MonthlyChart data={data} selected={selected} metric={metric} /><div className="its-summary"><p><b>지정 시점 변화</b> {its ? itsEffectText(its, metric, "즉시수준변화") : "자료 없음"} · {levelStrength}<small>p {finite(its?.즉시수준변화_p) ? Number(its.즉시수준변화_p).toFixed(3) : "–"} · 보정 q {finite(its?.즉시수준변화_q_BH) ? Number(its.즉시수준변화_q_BH).toFixed(3) : "–"} · 조건 {levelRobustness}/8</small></p><p><b>지정 후 변화 속도</b> {its ? itsEffectText(its, metric, "지정후기울기변화") : "자료 없음"} · {slopeStrength}<small>p {finite(its?.지정후_기울기변화_p) ? Number(its.지정후_기울기변화_p).toFixed(3) : "–"} · 보정 q {finite(its?.지정후_기울기변화_q_BH) ? Number(its.지정후_기울기변화_q_BH).toFixed(3) : "–"} · 조건 {slopeRobustness}/8</small></p></div><p className="note"><b>세 선을 나눈 이유</b> · 실제 값은 월별 관측치, 계절 반영 추정선은 계절·기존 추세·지정 시점 변화를 함께 반영한 모델값입니다. ‘지정 전 흐름이 이어졌다면’은 지정 시점 변화만 빼고 계산한 비교선입니다. 두 추정선의 차이는 지정 시점과 함께 나타난 구조변화를 뜻하며, 비교 지역이 없어 지정의 인과효과로 단정하지 않습니다.</p></>}
      {tab === "wellness" && <><div className="wellness-grid">{["숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "DSI", "방문자대비관광소비_천원_proxy"].map(m => { const row = data.growth.find(r => r.지역키 === selected && r.지표 === m); return <div key={m}><small>{LABEL[m]}</small><b>{formatLevel(kpi("P3", m), m)}</b><em>지정 직후 {formatChange(periodChange(row, m, "23"), m)}</em><div className="wellness-periods"><span>직전 <b>{formatLevel(kpi("P2", m), m)}</b></span><span>1년차 <b>{formatLevel(kpi("P3", m), m)}</b></span><span>2년차 <b>{formatLevel(kpi("P4", m), m)}</b></span></div></div>; })}</div><p className="note"><b>지표 안내</b> · 장기체류 비율은 전체 방문자 중 3박 이상 숙박객의 비중입니다. 사계절 수요는 월별 방문 편차가 작을수록 1에 가까우며, 방문자 대비 소비는 서로 다른 자료를 결합한 대리지표입니다.</p></>}
      {tab === "lodging" && <LodgingSupply data={data} selected={selected} />}
      {tab === "spending" && <SpendingCategories data={data} selected={selected} intervalKey={intervalKey} onIntervalChange={setIntervalKey} />}
      {tab === "market" && <><div className="market-grid"><div><h3>방문자 출발지 상위 5 · 지정 2년차</h3>{data.origins[selected].map((r, i) => <div className="origin" key={`${r["거주지(시도)"]}-${r["거주지(시군구)"]}`}><span>{i + 1}</span><p>{r["거주지(시도)"]} {r["거주지(시군구)"]}<i style={{ width: `${r["비율(%)"] / data.origins[selected][0]["비율(%)"] * 100}%` }} /></p><b>{Number(r["비율(%)"]).toFixed(1)}%</b></div>)}</div><div><h3>시설 반경 5km 주변 환경</h3><div className="poi-grid">{["음식점", "관광지", "문화시설", "레포츠"].map(k => <div key={k}><small>{k}</small><b>{data.environment[selected].poi[k] || 0}</b></div>)}</div></div></div><p className="note"><b>읽는 법</b> · 출발지는 지정 2년차 방문자의 거주지 분포입니다. 주변 환경은 TourAPI 등록 지점 수이며, 숙박시설은 별도 ‘숙박 공급’ 탭에서 인허가 객실 기준으로 확인합니다.</p></>}
      {tab === "table" && <div className="table-scroll"><table className="period-table"><thead><tr><th>지표</th>{PERIODS.map(p => <th key={p}>{PERIOD_LABEL[p]}</th>)}<th>지정 직후</th><th>2년차</th></tr></thead><tbody>{TABLE_METRICS.map(m => { const row = data.growth.find(r => r.지역키 === selected && r.지표 === m); return <tr key={m} className={STAGES.some(([s, mm]) => mm === m && site.bottleneck.includes(s)) ? "bottleneck-row" : ""}><td><b>{LABEL[m]}</b></td>{PERIODS.map(p => <td key={p}>{formatLevel(kpi(p, m), m)}</td>)}<td>{formatChange(row?.[m.endsWith("_pct") ? "delta23_pctp" : "g23_pct"], m)}</td><td>{formatChange(row?.[m.endsWith("_pct") ? "delta34_pctp" : "g34_pct"], m)}</td></tr>; })}</tbody></table></div>}
      {tab === "quality" && <DataQuality data={data} selected={selected} />}
    </section>
    <footer>WELL-FLOW · 관광·시설 공개자료 기반</footer>
  </main>;
}
