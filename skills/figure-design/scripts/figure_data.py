"""Exact-value quantitative SVG plots; no trend or result is invented."""
import csv
import math
from pathlib import Path
from xml.etree import ElementTree as ET
from figure_common import file_hash,schema_check,write
from figure_plan import figure_theme


def chart(path, out, x_column, y_column, title, kind='line', *, plan=None, condition=None, unit=None, baseline=None, scope=None, value_kind='level'):
    path,out=Path(path),Path(out)
    if out.exists():raise ValueError('chart output exists')
    if plan is not None:
        schema_check('composition-plan.schema.json', plan)
    theme = figure_theme(plan if plan is not None else {'style_id':'cs-academic'})
    with path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if not 2<=len(rows)<=10000:raise ValueError('chart requires 2–10000 rows')
    if kind in ('paired-dot', 'horizontal-bar'):
        if not all((unit, baseline, scope)) or (kind == 'paired-dot' and not condition):
            raise ValueError('categorical comparisons require --unit, --baseline, --scope and paired-dot also --condition')
        values = []
        for row in rows:
            if x_column not in row or y_column not in row or (condition and condition not in row):
                raise ValueError('comparison CSV column missing')
            if row.get('unit', unit) != unit:
                raise ValueError('mixed units in comparison')
            values.append({'category': row[x_column], 'condition': row[condition] if condition else '',
                           'value': float(row[y_column])})
        display = {'display':kind, 'metric':title, 'unit':unit, 'baseline':baseline, 'scope':scope,
                   'value_kind':value_kind, 'rows':values}
        svg = comparison_svg(display, theme)
        out.mkdir(parents=True)
        (out/'chart.svg').write_bytes(svg)
        metadata = {**display, 'source_sha256':file_hash(path), 'status':'review_required'}
        write(out/'data-provenance.json', metadata)
        return metadata
    points=[(float(row[x_column]),float(row[y_column])) for row in rows]
    if any(not math.isfinite(v) for point in points for v in point):raise ValueError('non-finite values are not permitted')
    if any(a[0]>=b[0] for a,b in zip(points,points[1:])):raise ValueError('x values must be strictly increasing; choose/aggregate ordering explicitly')
    xmin,xmax=min(p[0] for p in points),max(p[0] for p in points)
    ymin,ymax=min(0,min(p[1] for p in points)),max(0,max(p[1] for p in points))
    if ymin==ymax:ymax=ymin+1
    def xy(point):return (100+(point[0]-xmin)/(xmax-xmin)*600,400-(point[1]-ymin)/(ymax-ymin)*300)
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','width':'800','height':'500','viewBox':'0 0 800 500'})
    ET.SubElement(svg,'rect',{'width':'800','height':'500','fill':theme['surface']})
    def text(x,y,value,size=16):ET.SubElement(svg,'text',{'x':str(x),'y':str(y),'font-size':str(size),'fill':theme['ink']}).text=str(value)
    text(100,40,title,24);text(340,480,x_column);text(12,80,y_column)
    ET.SubElement(svg,'path',{'d':'M100 100 V400 H700','fill':'none','stroke':theme['ink']})
    for i in range(5):
        y=ymin+(ymax-ymin)*i/4;py=xy((xmin,y))[1];text(15,py+5,format(y,'.6g'))
        ET.SubElement(svg,'line',{'x1':'100','x2':'700','y1':str(py),'y2':str(py),'stroke':theme['border']})
        x=xmin+(xmax-xmin)*i/4;text(xy((x,ymin))[0]-10,430,format(x,'.6g'))
    if kind=='line':
        ET.SubElement(svg,'polyline',{'points':' '.join(f'{x},{y}' for x,y in map(xy,points)),'fill':'none','stroke':theme['accent'],'stroke-width':'3'})
    elif kind=='bar':
        bw=min(32,500/len(points));zero=xy((xmin,0))[1]
        for point in points:
            x,y=xy(point);ET.SubElement(svg,'rect',{'x':str(x-bw/2),'y':str(min(y,zero)),'width':str(bw),'height':str(abs(zero-y)),'fill':theme['accent']})
    else:raise ValueError('chart kind must be line or bar')
    out.mkdir(parents=True)
    (out/'chart.svg').write_text(ET.tostring(svg,encoding='unicode'),encoding='utf-8')
    metadata={'source_sha256':file_hash(path),'x_column':x_column,'y_column':y_column,'points':points,'kind':kind,'title':title,'theme':theme,
              'status':'review_required','notice':'Axis units, context and scientific interpretation require review.'}
    write(out/'data-provenance.json',metadata)
    return metadata


def comparison_svg(display, theme):
    """Draw a common zero-based scale. The same records supply marks and labels."""
    from collections import defaultdict
    from unicodedata import east_asian_width

    def extent(text):
        return sum(19 if east_asian_width(ch) in ('W', 'F') else 12 for ch in text)

    kind = display['display']
    rows = display['rows']
    if kind not in ('paired-dot', 'horizontal-bar') or len(rows) < 2:
        raise ValueError('comparison needs paired-dot or horizontal-bar and at least two values')
    groups = defaultdict(dict)
    conditions = []
    for row in rows:
        name = row['category']
        cond = row.get('condition', '')
        value = row['value']
        if not isinstance(name, str) or not name.strip() or type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError('comparison requires named categories and finite numeric values')
        if cond in groups[name] or (kind == 'horizontal-bar' and groups[name]):
            raise ValueError('duplicate category/condition in comparison')
        groups[name][cond] = value
        if cond not in conditions:
            conditions.append(cond)
    if kind == 'paired-dot' and (len(conditions) != 2 or '' in conditions or
                                 any(set(g) != set(conditions) for g in groups.values())):
        raise ValueError('paired-dot needs the same two named conditions for every category')
    if kind == 'horizontal-bar' and len(conditions) != 1:
        raise ValueError('horizontal-bar uses one series; use category for the compared conditions')
    value_kind = display.get('value_kind', 'level')
    if value_kind not in ('level', 'delta'):
        raise ValueError('value_kind must be level or delta')
    summary = display['metric'] + '（' + display['unit'] + '）'
    qualifier = ('变化量' if value_kind == 'delta' else '读数') + ' · 基准 ' + display['baseline']
    scope = display['scope']
    left = max(extent(key) for key in groups) + 23
    span = 256
    low = min(0, min(row['value'] for row in rows))
    high = max(0, max(row['value'] for row in rows))
    def x(value):
        return left + (value - low) / (high - low or 1) * span

    def numbers(values):
        return ' / '.join(str(values[c]) for c in conditions)

    legend = '○ ' + conditions[0] + '    ● ' + conditions[1] if kind == 'paired-dot' else conditions[0]
    width = max(left + span + 30 + max(extent(numbers(g)) for g in groups.values()),
                *(extent(t) + 24 for t in (summary, qualifier, scope, legend)))
    height = 132 + 34 * len(groups)
    svg = ET.Element('svg', {'xmlns':'http://www.w3.org/2000/svg', 'width':str(width),
                             'height':str(height), 'viewBox':f'0 0 {width} {height}'})
    def mark(tag, **attrs):
        return ET.SubElement(svg, tag, {k.replace('_','-'):str(v) for k,v in attrs.items()})
    def label(px, py, value):
        mark('text', x=px, y=py, font_size=18, fill=theme['ink']).text = value

    label(8, 21, summary)
    label(8, 44, qualifier)
    label(8, 67, scope)
    label(8, 91, legend)
    mark('line', x1=x(0), x2=x(0), y1=102, y2=height-24, stroke=theme['border'])
    for index, (name, values) in enumerate(groups.items()):
        y = 115 + index * 34
        label(8, y+6, name)
        p = x(values[conditions[0]])
        if kind == 'paired-dot':
            q = x(values[conditions[1]])
            mark('line', x1=p, x2=q, y1=y, y2=y, stroke=theme['accent'], stroke_width=3)
            mark('circle', cx=p, cy=y, r=6, fill=theme['surface'], stroke=theme['accent'], stroke_width=2)
            mark('circle', cx=q, cy=y, r=4, fill=theme['accent'])
        else:
            mark('rect', x=min(x(0),p), y=y-7, width=abs(x(0)-p), height=14, fill=theme['accent'])
        label(left+span+14, y+6, numbers(values))
    label(left, height-4, str(low))
    if high != low:
        label(left+span-10, height-4, str(high))
    return ET.tostring(svg, encoding='utf-8')
