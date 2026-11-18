"""Exact-value quantitative SVG plots; no trend or result is invented."""
import csv
import math
from pathlib import Path
from xml.etree import ElementTree as ET
from figure_common import file_hash,schema_check,write
from figure_plan import figure_theme


def chart(path, out, x_column, y_column, title, kind='line', *, plan=None):
    path,out=Path(path),Path(out)
    if out.exists():raise ValueError('chart output exists')
    if plan is not None:
        schema_check('composition-plan.schema.json', plan)
    theme = figure_theme(plan if plan is not None else {'style_id':'cs-academic'})
    with path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if not 2<=len(rows)<=10000:raise ValueError('chart requires 2–10000 rows')
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
