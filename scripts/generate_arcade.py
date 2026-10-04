"""Render public GitHub activity as a self-contained animated SVG.

No tokens, dependencies, or invented contribution data are needed.
"""
import argparse
import calendar
from datetime import date, datetime, timezone, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#182337', '#164e63', '#0e7490', '#22d3ee', '#a5f3fc']


class ContributionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.labels = {}
        self.target = None
        self.label = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('data-date') and attrs.get('data-level') is not None:
            self.days[attrs['data-date']] = {
                'level': int(attrs['data-level']), 'id': attrs.get('id', '')}
        if tag == 'tool-tip':
            self.target = attrs.get('for')
            self.label = []

    def handle_data(self, value):
        if self.target:
            self.label.append(value)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.target:
            self.labels[self.target] = ''.join(self.label).strip()
            self.target = None

    def result(self):
        rows = []
        for day, item in sorted(self.days.items()):
            label = self.labels.get(item['id'], '')
            match = re.search(r'([\d,]+) contributions?\b', label)
            if match:
                count = int(match.group(1).replace(',', ''))
            elif 'No contributions' in label:
                count = 0
            else:
                raise ValueError(f'Missing contribution count for {day}')
            if not 0 <= item['level'] <= 4:
                raise ValueError('Unexpected contribution level')
            rows.append({'date': day, 'level': item['level'], 'count': count})
        if len(rows) < 350:
            raise ValueError(f'Incomplete GitHub calendar: {len(rows)} days')
        return rows


def fetch_calendar(login):
    url = f'https://github.com/users/{login}/contributions'
    for attempt in range(3):
        try:
            req = Request(url, headers={'User-Agent': 'Contribution-Invaders/1.0'})
            with urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def sprite(x, y, color='#22d3ee', size=3, kind='alien'):
    patterns = {
        'alien': ['001000100', '000101000', '001111100', '011010110', '111111111', '101111101', '101000101'],
        'ship': ['000010000', '000111000', '000111000', '011111110', '111111111', '110111011', '100000001'],
    }
    cells = ''.join(f'<rect x="{c*size}" y="{r*size}" width="{size}" height="{size}"/>'
                    for r, line in enumerate(patterns[kind]) for c, value in enumerate(line) if value == '1')
    return f'<g transform="translate({x} {y})" fill="{color}">{cells}</g>'


def render(rows, login):
    total = sum(day['count'] for day in rows)
    active = sum(day['count'] > 0 for day in rows)
    start = date.fromisoformat(rows[0]['date'])
    base = start - timedelta(days=(start.weekday() + 1) % 7)
    end = date.fromisoformat(rows[-1]['date'])
    columns = (end - base).days // 7 + 1
    pitch = min(18, 972 / columns)
    x0, y0 = 76, 151
    cells, months = [], []
    last_month = None
    for item in rows:
        day = date.fromisoformat(item['date'])
        offset = (day - base).days
        col, row = divmod(offset, 7)
        x, y = x0 + col * pitch, y0 + row * 19
        if day.month != last_month:
            if col < columns - 1:
                months.append(f'<text x="{x:.1f}" y="136">{calendar.month_abbr[day.month]}</text>')
            last_month = day.month
        tooltip = escape(f"{day.isoformat()}: {item['count']} contributions")
        cells.append(f'<rect x="{x:.1f}" y="{y}" width="14" height="14" rx="3" fill="{COLORS[item["level"]]}" stroke="#28354b" stroke-width=".6"><title>{tooltip}</title></rect>')
    aliens = ''.join(f'<g class="alien a{i}">{sprite(88+i*108, 86, "#a78bfa", 2)}</g>' for i in range(9))
    beams = ''.join(f'<rect class="beam b{i}" x="{104+i*108}" y="308" width="3" height="15" rx="1" fill="#67e8f9"/>' for i in range(9))
    legend = ''.join(f'<rect x="{876+i*23}" y="380" width="14" height="14" rx="3" fill="{color}"/>' for i, color in enumerate(COLORS))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="420" viewBox="0 0 1120 420" role="img" aria-labelledby="title description">
<title id="title">Contribution Invaders — {escape(login)}'s public GitHub activity</title>
<desc id="description">{total} public contributions across {active} active days, {start} to {end}. Each square is one real day. Ships, aliens and lasers are decorative animation; they do not change the data.</desc>
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#10192c"/><stop offset="1" stop-color="#080d18"/></linearGradient>
<linearGradient id="scan"><stop stop-color="#22d3ee" stop-opacity="0"/><stop offset="1" stop-color="#22d3ee" stop-opacity=".15"/></linearGradient>
<clipPath id="field"><rect x="72" y="147" width="980" height="136" rx="5"/></clipPath></defs>
<style>
text{{font-family:Arial,Helvetica,sans-serif}} .mono{{font-family:Consolas,monospace}}
@keyframes patrol{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(930px)}}}}
@keyframes invade{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(20px,7px)}}}}
@keyframes beam{{0%,20%,100%{{opacity:0;transform:translateY(0)}}22%{{opacity:1;transform:translateY(0)}}50%{{opacity:1;transform:translateY(-212px)}}51%{{opacity:0;transform:translateY(-212px)}}}}
@keyframes scan{{from{{transform:translateX(-100px)}}to{{transform:translateX(1060px)}}}}
.ship{{animation:patrol 16s ease-in-out infinite}} .alien{{animation:invade 3s ease-in-out infinite}}
.beam{{opacity:0;animation:beam 4s linear infinite}} {''.join(f'.b{i}{{animation-delay:{i*.43}s}}' for i in range(9))}
.scan{{animation:scan 9s linear infinite}}
@media(prefers-reduced-motion:reduce){{.ship,.alien,.beam,.scan{{animation:none}}.beam,.scan{{display:none}}}}
</style>
<rect width="1120" height="420" rx="20" fill="url(#bg)"/>
<rect x=".5" y=".5" width="1119" height="419" rx="20" fill="none" stroke="#28354b"/>
<path d="M32 66H1088M32 357H1088" stroke="#263247"/>
<circle cx="38" cy="35" r="4" fill="#22d3ee"/>
<text x="54" y="41" fill="#f1f5f9" font-size="21" font-weight="700" letter-spacing="2">CONTRIBUTION INVADERS</text>
<text x="1086" y="40" text-anchor="end" fill="#94a3b8" font-size="13" class="mono">PLAYER 01 / @{escape(login)}</text>
{aliens}
<g font-size="11" fill="#94a3b8" class="mono">{''.join(months)}
<text x="37" y="180">MON</text><text x="37" y="218">WED</text><text x="37" y="256">FRI</text></g>
{''.join(cells)}
<g clip-path="url(#field)"><rect class="scan" x="0" y="147" width="90" height="136" fill="url(#scan)"/></g>
{beams}
<g class="ship">{sprite(76,310,'#67e8f9',3,'ship')}<path d="M86 336l4 10 4-10" fill="#a78bfa"/></g>
<text x="76" y="299" font-size="10" fill="#64748b" class="mono">PUBLIC ACTIVITY / {start} — {end}</text>
<text x="34" y="389" font-size="14" fill="#e2e8f0" class="mono">{total:,} CONTRIBUTIONS <tspan fill="#475569"> / </tspan>{active} ACTIVE DAYS</text>
<text x="34" y="408" font-size="10" fill="#64748b">REAL DATA. DAILY REFRESH. KEEP BUILDING.</text>
<text x="832" y="391" fill="#94a3b8" font-size="11">Less</text>{legend}<text x="999" y="391" fill="#94a3b8" font-size="11">More</text>
</svg>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='muhameho')
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', args.user):
        parser.error('Invalid GitHub username')
    source = args.input.read_text(encoding='utf-8') if args.input else fetch_calendar(args.user)
    calendar_parser = ContributionParser()
    calendar_parser.feed(source)
    rows = calendar_parser.result()
    svg = render(rows, args.user)
    assets = ROOT / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    (assets / 'contribution-invaders.svg').write_text(svg, encoding='utf-8')
    print(f'Rendered {len(rows)} real days / {sum(x["count"] for x in rows)} contributions')


if __name__ == '__main__':
    main()
