"use client";

import { useEffect, useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
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
const STATUS = { UP: ["오름", "↑", "up"], FLAT: ["유지", "→", "flat"], DOWN: ["내림", "↓", "down"], NA: ["자료 없음", "·", "na"] };
const INTERVALS = {
  immediate: { label: "지정 직후", before: "P2", after: "P3", growth: "g23_pct", point: "delta23_pctp", status: "지정직후_판정_3pct" },
  second: { label: "2년차", before: "P3", after: "P4", growth: "g34_pct", point: "delta34_pctp", status: "2년차_판정_3pct" },
};
const COLORS = { 관심: "#8fa39a", 방문: "#3f6fa8", 숙박: "#c8932b", 체류: "#2f8f6b", 소비: "#8c5bb5" };

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

function SectionTitle({ number, title, subtitle }) {
  return <div className="section-title"><span>{number}</span><div><h2>{title}</h2><p>{subtitle}</p></div></div>;
}

function JeollaMap({ geo, sites, selected, onSelect }) {
  const width = 520, height = 380;
  const { paths, points } = useMemo(() => {
    if (!geo) return { paths: [], points: [] };
    const projection = geoMercator().fitExtent([[22, 20], [width - 22, height - 20]], geo);
    const path = geoPath(projection);
    return {
      paths: geo.features.map((feature, index) => ({ index, d: path(feature), name: feature.properties.NAME_2 })),
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
    {points.map(({ key, site, xy }) => xy && <g key={key} className={`marker ${key === selected ? "selected" : ""}`} transform={`translate(${xy[0]} ${xy[1]})`} onClick={() => onSelect(key)}>
      <circle r={key === selected ? 13 : 10} /><path d="M0,-7 C7,-4 8,3 0,8 C-8,3 -7,-4 0,-7Z" /><text y="-16">{site.region}</text>
    </g>)}
  </svg>;
}

function StageFlow({ data, selected, intervalKey }) {
  const interval = INTERVALS[intervalKey];
  const site = data.sites[selected];
  return <div className="stage-flow">
    {STAGES.map(([stage, metric, description, source], i) => {
      const row = data.growth.find(r => r.지역키 === selected && r.지표 === metric);
      const change = row?.[metric.endsWith("_pct") ? interval.point : interval.growth];
      const code = row?.[interval.status] || "NA";
      const [label, arrow, cls] = STATUS[code] || STATUS.NA;
      const isBottleneck = site.bottleneck.includes(stage);
      const before = data.kpi.find(r => r.지역키 === selected && r.기간 === interval.before)?.[metric];
      const after = data.kpi.find(r => r.지역키 === selected && r.기간 === interval.after)?.[metric];
      return <div className="stage-wrap" key={stage}>
        <div className={`stage-card ${cls} ${isBottleneck ? "bottleneck" : ""}`}>
          <div className="stage-top"><span>{stage}</span><em>{source}</em></div><strong>{arrow} {formatChange(change, metric)}</strong>
          <small>{description}</small><div className="stage-values">{formatLevel(before, metric)} → {formatLevel(after, metric)}</div>
          {isBottleneck && <b className="bottleneck-tag">핵심 병목</b>}
        </div>{i < STAGES.length - 1 && <span className="stage-arrow">›</span>}
      </div>;
    })}
  </div>;
}

function FlowChart({ data, selected }) {
  const rows = PERIODS.map(period => {
    const source = data.kpi.find(r => r.지역키 === selected && r.기간 === period);
    const base = data.kpi.find(r => r.지역키 === selected && r.기간 === "P1");
    const row = { period: PERIOD_LABEL[period] };
    STAGES.forEach(([stage, metric]) => { row[stage] = finite(source?.[metric]) && base?.[metric] ? source[metric] / base[metric] * 100 : null; });
    return row;
  });
  return <div className="chart-box"><ResponsiveContainer width="100%" height={330}><LineChart data={rows} margin={{ top: 12, right: 24, left: 0, bottom: 8 }}>
    <CartesianGrid stroke="#e4ece7" vertical={false} /><XAxis dataKey="period" tick={{ fill: "#61766b", fontSize: 12 }} /><YAxis tick={{ fill: "#61766b", fontSize: 12 }} domain={["auto", "auto"]} unit="" />
    <Tooltip formatter={(v) => `${Number(v).toFixed(1)}`} /><Legend />
    {STAGES.map(([stage]) => <Line key={stage} type="monotone" dataKey={stage} stroke={COLORS[stage]} strokeWidth={data.sites[selected].bottleneck.includes(stage) ? 4 : 2} dot={{ r: 4 }} />)}
  </LineChart></ResponsiveContainer></div>;
}

function MonthlyChart({ data, selected, metric }) {
  const rows = data.monthly.filter(r => r.지역키 === selected).map(r => ({ month: String(r.기준년월), value: r[metric] }));
  const intervention = String(data.its.find(r => r.지역키 === selected)?.개입시작월 || "");
  return <div className="chart-box"><ResponsiveContainer width="100%" height={330}><LineChart data={rows} margin={{ top: 12, right: 26, left: 2, bottom: 8 }}>
    <CartesianGrid stroke="#e4ece7" vertical={false} /><XAxis dataKey="month" interval={5} tickFormatter={v => `${String(v).slice(2, 4)}.${String(v).slice(4)}`} tick={{ fill: "#61766b", fontSize: 11 }} />
    <YAxis tick={{ fill: "#61766b", fontSize: 11 }} width={54} /><Tooltip labelFormatter={v => `${String(v).slice(0, 4)}.${String(v).slice(4)}`} formatter={v => formatLevel(Number(v), metric)} />
    <ReferenceLine x={intervention} stroke="#d2513a" strokeDasharray="5 5" label={{ value: "지정", fill: "#d2513a", fontSize: 11 }} />
    <Line type="monotone" dataKey="value" name={LABEL[metric]} stroke="#2f8f6b" strokeWidth={2.5} dot={false} />
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
  const tabs = [["flow", "흐름 추이"], ["its", "지정 시점 확인"], ["wellness", "웰니스 지표"], ["market", "방문 출발지·주변 환경"], ["table", "네 구간 값 표"], ["quality", "데이터 신뢰도"]];

  return <main>
    <header className="topbar"><div className="brand"><b>WELL-FLOW <span>Monitor</span></b><p>웰니스 관광지 성과 진단</p></div><div className="top-meta">{site.region} 분석기간 · {ym(period.P1.시작월)}–{ym(period.P4.종료월)} · 지정월 기준</div></header>
    <div className="map-label"><b>전라도 웰니스 관광지 위치</b><span>지도에서 지역을 선택하세요</span></div>
    <section className="hero-grid">
      <div className="panel map-panel"><JeollaMap geo={geo} sites={data.sites} selected={selected} onSelect={setSelected} /></div>
      <div className="panel site-panel"><img src={`/sites/${site.image}`} alt={site.site} /><div className="site-copy"><span className="eyebrow">SELECTED SITE</span><h1>{site.site}</h1><p className="location">{site.region} · {site.dong} · {site.year}년 선정</p><p className="address">{site.address}</p><div className="diagnosis"><small>{site.type}</small><strong>{site.headline}</strong></div></div></div>
    </section>

    <SectionTitle number="1" title="병목 진단" subtitle="지정 전후 다섯 단계의 변화와 핵심 병목을 한눈에 확인합니다" />
    <section className="panel diagnosis-panel"><div className="diagnosis-head"><div><span className="eyebrow">비교 구간</span><div className="segmented"><button className={intervalKey === "immediate" ? "active" : ""} onClick={() => setIntervalKey("immediate")}>지정 직후</button><button className={intervalKey === "second" ? "active" : ""} onClick={() => setIntervalKey("second")}>2년차</button></div></div><p><b>핵심 병목</b> · {site.bottleneckLabel}</p></div><StageFlow data={data} selected={selected} intervalKey={intervalKey} /><details><summary>핵심 병목 근거 자세히 보기</summary><p>{site.evidence}</p></details></section>

    <SectionTitle number="2" title="대응 방향" subtitle="핵심 병목에 맞춘 우선 검토 사항과 다음 점검 지표" />
    <section className="two-col">
      <div className="panel response"><div className="response-lead"><small>핵심 병목 · 확인 강도 {site.strength}</small><h3>{site.bottleneckLabel}</h3><p>{site.headline}</p></div><div className="response-grid"><div><h4>우선 검토</h4>{site.recommend.map(([title, desc], i) => <div className="action" key={title}><span>{i + 1}</span><p><b>{title}</b><small>{desc}</small></p></div>)}</div><div className="low"><h4>우선순위 낮음</h4><div className="action"><span>×</span><p><b>{site.avoid[0]}</b><small>{site.avoid[1]}</small></p></div></div></div><p className="good"><b>이미 괜찮은 칸</b> · {site.good}</p></div>
      <div className="panel check"><span className="eyebrow">다음 점검 지표</span><h3>{LABEL[site.checkMetric]}</h3><strong>{formatLevel(kpi("P4", site.checkMetric), site.checkMetric)}</strong><p>지정 2년차 현재 수준</p><div className="steps">{site.actions.map(([when, what], i) => <div className="step" key={when}><span>{i + 1}</span><p><small>{when}</small><b>{what}</b></p></div>)}</div></div>
    </section>

    <SectionTitle number="3" title="조기 경보 · 지역 비교" subtitle="1년차 하락 지표의 2년차 회복 여부와 네 지역 차이" />
    <section className="compare-grid">
      <div className="panel warning"><span className="eyebrow">1년차 하락 지표</span>{warningRows.length ? <table><thead><tr><th>단계</th><th>1년차</th><th>2년 누적</th><th>판정</th></tr></thead><tbody>{warningRows.map(r => <tr key={r.metric}><td><b>{r.stage}</b><small>{LABEL[r.metric]}</small></td><td className="negative">{r.y1 > 0 ? "+" : ""}{r.y1.toFixed(1)}%</td><td>{r.y2 > 0 ? "+" : ""}{r.y2.toFixed(1)}%</td><td><span className={`pill ${r.y2 >= -3 ? "up" : "down"}`}>{r.y2 >= -3 ? "회복" : "미회복"}</span></td></tr>)}</tbody></table> : <p className="empty">지정 1년차에 내려간 단계가 없습니다.</p>}<p className="note">2년차 누적이 지정 직전 대비 −3% 이내면 회복으로 봅니다.</p></div>
      <div className="panel matrix"><span className="eyebrow">4개 지역 비교 · {interval.label}</span><div className="table-scroll"><table><thead><tr><th>지역</th>{STAGES.map(([s]) => <th key={s}>{s}</th>)}<th>진단 유형</th></tr></thead><tbody>{Object.entries(data.sites).map(([key, s]) => <tr key={key} className={key === selected ? "selected-row" : ""} onClick={() => setSelected(key)}><td><b>{s.region}</b><small>{s.site}</small></td>{STAGES.map(([stage, m]) => { const code = status(key, m); return <td key={m} className={`signal ${STATUS[code][2]} ${s.bottleneck.includes(stage) ? "bottleneck" : ""}`}><b>{STATUS[code][1]}</b><small>{formatChange(change(key, m), m)}</small></td>; })}<td>{s.type}</td></tr>)}</tbody></table></div></div>
    </section>

    <SectionTitle number="4" title="상세 근거" subtitle="지표를 선택해 변화의 크기와 데이터 범위를 확인합니다" />
    <section className="panel evidence"><div className="tabs">{tabs.map(([key, title]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{title}</button>)}</div>
      {tab === "flow" && <><p className="tab-help">다섯 단계를 첫 구간=100으로 맞췄습니다. 굵은 선은 핵심 병목입니다.</p><FlowChart data={data} selected={selected} /></>}
      {tab === "its" && <><div className="metric-select"><label>지표</label><select value={metric} onChange={e => setMetric(e.target.value)}>{["숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "내국인관광소비_천원"].map(m => <option key={m} value={m}>{LABEL[m]}</option>)}</select></div><MonthlyChart data={data} selected={selected} metric={metric} /><div className="stats"><div><small>지정 시점 변화</small><b>{its ? formatChange(its.즉시변화_환산_pct ?? its.즉시수준변화_beta, metric) : "자료 없음"}</b></div><div><small>유의확률 p</small><b>{its ? Number(its.즉시수준변화_p).toFixed(3) : "–"}</b></div><div><small>보정 q</small><b>{its ? Number(its.즉시수준변화_q_BH).toFixed(3) : "–"}</b></div></div><p className="note">대조 지역이 없어 인과효과가 아닌 지정 전후 구조변화로 읽습니다.</p></>}
      {tab === "wellness" && <div className="wellness-grid">{["숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "DSI", "방문자대비관광소비_천원_proxy"].map(m => <div key={m}><small>{LABEL[m]}</small><b>{formatLevel(kpi("P3", m), m)}</b><em>{formatChange(m.endsWith("_pct") ? kpi("P3", m) - kpi("P2", m) : (kpi("P3", m) / kpi("P2", m) - 1) * 100, m)}</em></div>)}</div>}
      {tab === "market" && <div className="market-grid"><div><h3>방문자 출발지 상위 5 · 지정 2년차</h3>{data.origins[selected].map((r, i) => <div className="origin" key={`${r["거주지(시도)"]}-${r["거주지(시군구)"]}`}><span>{i + 1}</span><p>{r["거주지(시도)"]} {r["거주지(시군구)"]}<i style={{ width: `${r["비율(%)"] / data.origins[selected][0]["비율(%)"] * 100}%` }} /></p><b>{Number(r["비율(%)"]).toFixed(1)}%</b></div>)}</div><div><h3>시설 반경 5km 주변 환경</h3><div className="poi-grid">{["숙박", "음식점", "관광지", "문화시설"].map(k => <div key={k}><small>{k}</small><b>{data.environment[selected].poi[k] || 0}</b></div>)}</div><p className="note">최근접 숙박 {data.environment[selected].nearest?.distanceKm.toFixed(2)}km · {data.environment[selected].nearest?.name}</p></div></div>}
      {tab === "table" && <div className="table-scroll"><table className="period-table"><thead><tr><th>지표</th>{PERIODS.map(p => <th key={p}>{PERIOD_LABEL[p]}</th>)}<th>지정 직후</th><th>2년차</th></tr></thead><tbody>{TABLE_METRICS.map(m => { const row = data.growth.find(r => r.지역키 === selected && r.지표 === m); return <tr key={m} className={STAGES.some(([s, mm]) => mm === m && site.bottleneck.includes(s)) ? "bottleneck-row" : ""}><td><b>{LABEL[m]}</b></td>{PERIODS.map(p => <td key={p}>{formatLevel(kpi(p, m), m)}</td>)}<td>{formatChange(row?.[m.endsWith("_pct") ? "delta23_pctp" : "g23_pct"], m)}</td><td>{formatChange(row?.[m.endsWith("_pct") ? "delta34_pctp" : "g34_pct"], m)}</td></tr>; })}</tbody></table></div>}
      {tab === "quality" && <div className="quality-grid"><div><h3>지표별 확보 수준</h3>{[["관심·방문", "시군구 월별", "확보"], ["숙박 전환·체류", "시군구 월별", "확보"], ["소비", "시군구 월별", "확보"], ["방문 대비 소비", "시군구", "대리지표"], ["시설지 소비 집중도", "읍면동", "참고"], ["시설 자체 성과", "시설", "추후 과제"]].map(([a, b, c]) => <div className="quality-row" key={a}><b>{a}</b><span>{b}</span><em className={c === "확보" ? "ok" : "partial"}>{c}</em></div>)}</div><div><h3>원인을 확정하려면 필요한 자료</h3><div className="steps">{site.needs.map(([title, desc], i) => <div className="step" key={title}><span>{i + 1}</span><p><small>{title}</small><b>{desc}</b></p></div>)}</div><p className="note">추가 자료 전에는 병목 위치까지만 말하고 원인은 확정하지 않습니다.</p></div></div>}
    </section>
    <footer>WELL-FLOW · 한국관광 데이터랩 공개 자료 · 시설 소재 시군구 관광시장 · ±3% 실무용 방향 판정</footer>
  </main>;
}
