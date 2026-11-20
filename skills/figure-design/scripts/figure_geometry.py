"""Orthogonal obstacle routing with explicit failure instead of hidden crossed objects."""
from __future__ import annotations
import heapq


def intersects(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def route(source, target, rectangles, canvas):
    if source == target:
        raise ValueError('self-loop needs explicit scene routing; split the owner or provide a custom composition')
    pad = 12
    def ports(r, other):
        x, y, w, h = r
        ox, oy, ow, oh = other
        cx, cy = ox + ow/2, oy + oh/2
        aligned = []
        if y + pad < cy < y + h - pad and cy != y+h/2:
            aligned.extend([((x, cy), (x-pad, cy)), ((x+w, cy), (x+w+pad, cy))])
        if x + pad < cx < x + w - pad and cx != x+w/2:
            aligned.extend([((cx, y), (cx, y-pad)), ((cx, y+h), (cx, y+h+pad))])
        return aligned + [((x+w/2, y), (x+w/2, y-pad)), ((x+w, y+h/2), (x+w+pad, y+h/2)),
                ((x+w/2, y+h), (x+w/2, y+h+pad)), ((x, y+h/2), (x-pad, y+h/2))]
    starts, ends = ports(source, target), ports(target, source)
    expanded = [[x-pad+1, y-pad+1, w+2*pad-2, h+2*pad-2] for x,y,w,h in rectangles]
    xs = sorted({24., canvas[0]-24., *[v for x,y,w,h in rectangles for v in (x-pad, x+w/2, x+w+pad)]})
    ys = sorted({24., canvas[1]-24., *[v for x,y,w,h in rectangles for v in (y-pad, y+h/2, y+h+pad)]})
    def blocked(point):
        x,y = point
        return not (0 <= x <= canvas[0] and 0 <= y <= canvas[1]) or any(a < x < a+w and b < y < b+h for a,b,w,h in expanded)
    def clear(a,b):
        if a[0] == b[0]:
            return not any(x < a[0] < x+w and max(min(a[1],b[1]),y) < min(max(a[1],b[1]),y+h) for x,y,w,h in expanded)
        return not any(y < a[1] < y+h and max(min(a[0],b[0]),x) < min(max(a[0],b[0]),x+w) for x,y,w,h in expanded)
    destinations = {point: anchor for anchor,point in ends if not blocked(point)}
    queue, best, previous, origins = [], {}, {}, {}
    for anchor,point in starts:
        if blocked(point):continue
        key = (xs.index(point[0]),ys.index(point[1]),0)
        best[key],origins[key] = 0,anchor
        heapq.heappush(queue,(0,key))
    final = None
    while queue:
        cost,key = heapq.heappop(queue)
        if cost != best[key]:continue
        ix,iy,direction = key
        a = (xs[ix],ys[iy])
        if a in destinations:
            final = key;break
        for dx,dy,axis in [(1,0,1),(-1,0,1),(0,1,2),(0,-1,2)]:
            nx,ny = ix+dx,iy+dy
            if not (0 <= nx < len(xs) and 0 <= ny < len(ys)):continue
            b = (xs[nx],ys[ny])
            if blocked(b) or not clear(a,b):continue
            score = cost+abs(a[0]-b[0])+abs(a[1]-b[1])+(24 if direction and axis != direction else 0)
            next_key = (nx,ny,axis)
            if score < best.get(next_key,float('inf')):
                best[next_key],previous[next_key],origins[next_key] = score,key,origins[key]
                heapq.heappush(queue,(score,next_key))
    if final is None:
        raise ValueError('no obstacle-free route; recompose with more space')
    end = destinations[(xs[final[0]],ys[final[1]])]
    points = [end]
    key = final
    while True:
        points.append((xs[key[0]],ys[key[1]]))
        if key not in previous:break
        key = previous[key]
    points.append(origins[final]);points.reverse()
    compact = [points[0]]
    for i in range(1,len(points)-1):
        a,b,c = compact[-1],points[i],points[i+1]
        if (a[0]==b[0]==c[0]) or (a[1]==b[1]==c[1]):continue
        compact.append(b)
    compact.append(points[-1])
    return [list(p) for p in compact]
