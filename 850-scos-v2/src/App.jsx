import { useState, useEffect } from 'react'
import { LayoutDashboard, TrendingUp, AlertTriangle, Package, Clock4, BarChart3 } from 'lucide-react'

const fmt = n => (n || 0).toLocaleString()
const API = '/api'

function KpiCard({ label, value, sub, accent }) {
  const colors = {
    blue: { border: 'border-t-[#638fff]', bg: 'rgba(99,143,255,.06)', glow: 'rgba(99,143,255,.15)' },
    amber: { border: 'border-t-[#f5b842]', bg: 'rgba(245,184,66,.06)', glow: 'rgba(245,184,66,.15)' },
    green: { border: 'border-t-[#3dd68c]', bg: 'rgba(61,214,140,.06)', glow: 'rgba(61,214,140,.15)' },
    red: { border: 'border-t-[#e5484d]', bg: 'rgba(229,72,77,.06)', glow: 'rgba(229,72,77,.15)' },
  }
  const c = colors[accent] || colors.blue
  return (
    <div className={`rounded-2xl border-2 border-b-0 border-l-0 border-r-0 ${c.border} p-6 text-center transition-all hover:-translate-y-0.5`}
      style={{ background: `linear-gradient(180deg, ${c.glow} 0%, transparent 60%)`, backdropFilter: 'blur(8px)' }}>
      <p className="text-[10px] font-semibold uppercase tracking-[.12em] mb-3 opacity-40">{label}</p>
      <p className="text-[32px] font-extrabold tracking-[-.02em] leading-none">{value}</p>
      {sub ? <p className="text-[11px] mt-2 opacity-40">{sub}</p> : null}
    </div>
  )
}

function TypeBadge({ name, qty, max, color }) {
  return (
    <div className="rounded-xl p-4 text-center transition-all hover:-translate-y-0.5"
      style={{ background: 'rgba(255,255,255,.02)', border: '1px solid rgba(255,255,255,.06)' }}>
      <p className="text-[26px] font-bold tracking-tight leading-none" style={{ color }}>{fmt(qty)}</p>
      <p className="text-[10px] mt-1.5 opacity-40">{name}</p>
      <div className="h-1.5 rounded-full mt-2.5" style={{ background: 'rgba(255,255,255,.06)' }}>
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.max(Math.round(qty / Math.max(max, 1) * 100), 2)}%`, background: color }}></div>
      </div>
    </div>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [kpi, setKpi] = useState(null)
  const [loading, setLoading] = useState(true)
  const [time, setTime] = useState('')

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const [hRes, k1Res, kpiRes] = await Promise.all([
        fetch(`${API}/health`).then(r => r.json()),
        fetch(`${API}/k1-summary`).then(r => r.json()),
        fetch(`${API}/cache/kpi`).then(r => r.json())
      ])
      if (hRes.last_sync_time) setTime(hRes.last_sync_time.substring(11, 19))
      if (!k1Res.error) setData(k1Res)
      if (!kpiRes.error) setKpi(kpiRes)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="space-y-4 text-center">
        <div className="w-8 h-8 border-2 border-t-[#638fff] rounded-full animate-spin mx-auto" style={{ borderRightColor: 'transparent', borderBottomColor: 'transparent', borderLeftColor: 'transparent' }}></div>
        <p className="text-sm opacity-40">加载中...</p>
      </div>
    </div>
  )

  if (!data) return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-sm opacity-60">无法加载数据，请确认 Portal 在运行</p>
    </div>
  )

  const d = data
  const bx = d.backlog_xreg || {}
  const types = [
    { k: 'CTO_P1', n: 'CTO P1', c: '#638fff' },
    { k: 'FGA', n: 'FGA', c: '#f5b842' },
    { k: 'RTL', n: 'RTL', c: '#3dd68c' },
    { k: 'CTO', n: 'CTO P2', c: '#94a3be' }
  ]
  const tvs = types.map(t => ({ ...t, sum: Object.values(bx[t.k] || {}).reduce((a, b) => a + b, 0) }))
  const tMax = Math.max(...tvs.map(t => t.sum), 1)

  const cg = d.cto_p1_gpp || {}, og = d.others_gpp || {}
  const stbl = (cg.stbl || 0) + (og.stbl || 0), atb = (cg.atb || 0) + (og.atb || 0)
  const wip = (cg.wip || 0) + (og.wip || 0), fg = (cg.fg || 0) + (og.fg || 0)
  const pTotal = Math.max(stbl + atb + wip + fg, 1)
  const prod = [
    { l: 'STBL', v: stbl, c: '#475569' }, { l: 'ATB', v: atb, c: '#f5b842' },
    { l: 'WIP', v: wip, c: '#638fff' }, { l: 'FG', v: fg, c: '#3dd68c' }
  ]

  const cq = Math.max(d.cto_p1_qty || 1, 1), cs = d.cto_p1_shipped || 0
  const cr = Math.round(cs / cq * 100)
  const tl = d.cto_timeline || [], today = tl.find(x => x.today)
  const miss = today ? Math.max(0, (today.planned || 0) - (today.actual || 0)) : 0

  const wk = kpi?.weekly || {}, ws = kpi?.this_week_start || '', w = wk[ws] || {}

  const links = [
    { icon: LayoutDashboard, label: 'K1 PRD 看板', desc: '完整订单明细 · 下钻导出' },
    { icon: TrendingUp, label: 'CTO P1 KPI', desc: '周度统计 · 28H 达标分析' },
    { icon: AlertTriangle, label: 'E2E 站别分析', desc: '瓶颈识别 · 改善方向定位' },
  ]

  return (
    <div className="min-h-screen px-4 py-6 pb-24 md:px-8 md:py-10 max-w-6xl mx-auto">
      {/* Header */}
      <header className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-[22px] font-bold tracking-[-.01em] leading-none">850 SCOS</h1>
          <p className="text-xs opacity-30 mt-1">Supply Chain Operating System</p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2 justify-end">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: time ? '#3dd68c' : '#475569' }}></span>
            <span className="text-xs opacity-40">{time ? `实时 · ${time}` : '离线'}</span>
          </div>
        </div>
      </header>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="PRD 总台数" value={fmt(d.total_qty)} sub={`${d.total_pcs || 0} 条 PO`} accent="blue" />
        <KpiCard label="Backlog" value={fmt(d.unshipped)} sub={[
          d.asn_pending_qty > 0 && `ASN待S ${fmt(d.asn_pending_qty)}`,
          d.nack_count > 0 && `NACK ${d.nack_count}`
        ].filter(Boolean).join(' · ') || ''} accent="amber" />
        <KpiCard label="已出货" value={fmt(d.shipped)} sub={`出货率 ${Math.round(d.shipped / Math.max(d.total_qty, 1) * 100)}%`} accent="green" />
        <KpiCard label="CTO P1 未出" value={fmt(d.cto_p1_unshipped)} sub={`已出 ${fmt(cs)} / ${fmt(cq)}`} accent="red" />
      </div>

      {/* Two-column: Types + Production */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        {/* Backlog Types */}
        <section className="rounded-2xl p-6" style={{ background: 'rgba(255,255,255,.015)', border: '1px solid rgba(255,255,255,.05)' }}>
          <div className="flex items-center gap-2 mb-5">
            <Package size={14} style={{ color: '#638fff' }} />
            <h3 className="text-[11px] font-semibold uppercase tracking-[.1em] opacity-40">Backlog 类型分布</h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {tvs.map(t => <TypeBadge key={t.k} name={t.n} qty={t.sum} max={tMax} color={t.c} />)}
          </div>
        </section>

        {/* Production Status */}
        <section className="rounded-2xl p-6" style={{ background: 'rgba(255,255,255,.015)', border: '1px solid rgba(255,255,255,.05)' }}>
          <div className="flex items-center gap-2 mb-5">
            <BarChart3 size={14} style={{ color: '#638fff' }} />
            <h3 className="text-[11px] font-semibold uppercase tracking-[.1em] opacity-40">Backlog 生产状态</h3>
          </div>
          <div className="flex h-8 rounded-lg overflow-hidden mb-3">
            {prod.map(p => (
              <div key={p.l} className="transition-all duration-700 first:rounded-l-lg last:rounded-r-lg"
                style={{ width: `${Math.round(p.v / pTotal * 100)}%`, background: p.c }}></div>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-2 mt-4">
            {prod.map(p => (
              <div key={p.l} className="text-center">
                <p className="text-lg font-bold leading-none" style={{ color: p.c }}>{fmt(p.v)}</p>
                <p className="text-[10px] mt-0.5 opacity-40">{p.l}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* CTO P1 */}
      <section className="rounded-2xl p-6 mb-6" style={{ background: 'rgba(255,255,255,.015)', border: '1px solid rgba(255,255,255,.05)' }}>
        <div className="flex items-center gap-2 mb-5">
          <Clock4 size={14} style={{ color: '#638fff' }} />
          <h3 className="text-[11px] font-semibold uppercase tracking-[.1em] opacity-40">CTO P1 28H</h3>
          <span className="text-[10px] ml-auto opacity-30">本周 {ws} · {w.pct || 0}% {kpi?.target_75 ? '✅' : '❌'}</span>
        </div>
        <div className="grid grid-cols-3 gap-6 text-center">
          {[
            { v: `${cr}%`, l: '28H 累计达标率', c: cr >= 90 ? '#3dd68c' : cr >= 75 ? '#f5b842' : '#e5484d' },
            { v: fmt(cs), l: `已出货 / ${fmt(cq)} 总数`, c: '#f0f4ff' },
            { v: fmt(miss), l: '今日 Miss 风险', c: miss > 0 ? '#e5484d' : '#3dd68c' },
          ].map(item => (
            <div key={item.l}>
              <p className="text-[28px] font-bold tracking-tight leading-none" style={{ color: item.c }}>{item.v}</p>
              <p className="text-[10px] mt-1.5 opacity-40">{item.l}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick Links */}
      <section className="rounded-2xl p-6" style={{ background: 'rgba(255,255,255,.015)', border: '1px solid rgba(255,255,255,.05)' }}>
        <h3 className="text-[11px] font-semibold uppercase tracking-[.1em] opacity-40 mb-4">快捷入口</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {links.map(link => (
            <a key={link.label} href="#"
              className="flex items-center gap-3 rounded-xl p-4 transition-all hover:-translate-y-0.5"
              style={{ background: 'rgba(255,255,255,.02)', border: '1px solid rgba(255,255,255,.05)', color: '#f0f4ff', textDecoration: 'none' }}>
              <link.icon size={18} style={{ color: '#638fff', flexShrink: 0 }} />
              <div>
                <p className="text-[13px] font-semibold">{link.label}</p>
                <p className="text-[10px] mt-0.5 opacity-40">{link.desc}</p>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center mt-8 text-[10px] opacity-20">850 Supply Chain OS · V2</footer>
    </div>
  )
}
