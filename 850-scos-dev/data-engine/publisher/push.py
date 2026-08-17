"""
Publisher — incremental push to Yumin Portal with ack tracking.

Integrity guarantees:
1. Local DB always keeps full data (nothing lost).
2. Only records with updated_at > last_confirmed_push are sent.
3. last_confirmed_push advances ONLY after remote confirms (no gaps).
4. Push is idempotent (upsert) — retries never duplicate.
5. First run / long-disconnected → full push automatically.
"""
import os, json, time, requests
from datetime import datetime

YUMIN_URL = os.environ.get('YUMIN_URL', '')
YUMIN_LOCAL = 'http://localhost:5050/sync'
YUMIN_REMOTE = 'https://yumin.taila2a2ad.ts.net/sync'

# Max records per request — split large pushes into chunks
CHUNK_SIZE = 2000


def push(conn, records_all, k1_summary, daily_summary, risks, kpi, e2e_kpi=None):
    """Push CHANGED records + all summaries to Yumin.

    Args:
        conn: engine DB connection
        records_all: all merged records (for full-push fallback)
        summaries: pre-computed summaries

    Returns:
        (pushed_to, sent_count) or (None, 0) on failure
    """
    from storage.db import get_push_state, set_push_state, get_changed_rows

    targets = [YUMIN_LOCAL]
    if YUMIN_URL and YUMIN_URL not in targets:
        targets.append(YUMIN_URL)
    elif not YUMIN_URL and YUMIN_REMOTE not in targets:
        targets.append(YUMIN_REMOTE)

    # ── Determine what to send ─────────────────────────────
    now = datetime.now().isoformat()
    last_ok = get_push_state(conn, 'last_confirmed_push')
    changed = get_changed_rows(conn, last_ok)
    is_full = last_ok is None

    if is_full:
        print(f'[publisher] No confirmed push yet — FULL push ({len(changed):,} records)')
    elif changed:
        print(f'[publisher] Incremental push — {len(changed):,} changed records since {last_ok[:19]}')
    else:
        print('[publisher] No changes since last push — summaries only')

    payload_base = {
        'k1_summary': k1_summary,
        'daily_summary': daily_summary,
        'risks': risks,
        'risk_summary': _summarize_risks(risks) if risks else {},
        'kpi': kpi,
        'e2e_kpi': e2e_kpi or {},
    }

    # ── Push to all targets ────────────────────────────────
    all_confirmed = True
    any_sent = False

    for target_url in targets:
        confirmed = False
        # Push records in chunks
        if changed:
            chunks = [changed[i:i + CHUNK_SIZE] for i in range(0, len(changed), CHUNK_SIZE)]
        else:
            chunks = [[]]  # summaries-only push

        for idx, chunk in enumerate(chunks):
            payload = dict(payload_base)
            payload['records'] = chunk
            payload['chunk'] = f'{idx + 1}/{len(chunks)}'
            payload['final'] = idx == len(chunks) - 1

            for attempt in range(3):
                try:
                    r = requests.post(target_url, json=payload,
                                      timeout=(30, 300), verify=target_url.startswith('https'))
                    if r.ok:
                        print(f'[publisher] OK {target_url} chunk {idx+1}/{len(chunks)} ({len(chunk)} records)')
                        any_sent = True
                        break
                    print(f'[publisher] HTTP {r.status_code} from {target_url}')
                except Exception as e:
                    print(f'[publisher] Attempt {attempt+1} failed ({target_url}): {str(e)[:100]}')
                    if attempt < 2:
                        time.sleep(5)
            else:
                all_confirmed = False
                break  # this target failed, stop chunking

        if all_confirmed or target_url == YUMIN_LOCAL:
            # Remote confirmed (or only local exists). If remote exists and failed, don't advance.
            if target_url != YUMIN_LOCAL or YUMIN_LOCAL not in targets:
                confirmed = all_confirmed
        if target_url == YUMIN_LOCAL and len(targets) == 1:
            confirmed = True  # local-only setup

    # ── Advance ack marker only if REMOTE confirmed ────────
    # Local portal on same machine doesn't need ack tracking for integrity —
    # remote Yumin does. If remote failed, keep marker so next cycle retries.
    remote_ok = True
    remote_urls = [t for t in targets if t != YUMIN_LOCAL]
    if remote_urls:
        remote_ok = all_confirmed  # remote confirmed only if no target failed

    if remote_ok and any_sent:
        set_push_state(conn, 'last_confirmed_push', now)
        print(f'[publisher] Confirmed — marker advanced to {now[:19]}')
    elif changed:
        print('[publisher] Remote NOT confirmed — will retry same records next cycle')

    return (targets[-1] if any_sent else None, len(changed) if any_sent else 0)


def _summarize_risks(risks):
    s = {}
    for r in risks:
        k = r['type']
        s.setdefault(k, {'count': 0, 'qty': 0})
        s[k]['count'] += 1
        s[k]['qty'] += r['qty']
    return s
