# Random placement helpers because I'm tired of using spreadsheets for doing this
#
# Kevin Cuzner

import math
from pcbnew import *

def place_circle(refdes, start_angle, center, radius, component_offset=0, hide_ref=True, lock=False):
    """
    Places components in a circle
    refdes: List of component references
    start_angle: Starting angle
    center: Tuple of (x, y) mils of circle center
    radius: Radius of the circle in mils
    component_offset: Offset in degrees for each component to add to angle
    hide_ref: Hides the reference if true, leaves it be if None
    lock: Locks the footprint if true
    """
    pcb = GetBoard()
    deg_per_idx = 360 / len(refdes)
    for idx, rd in enumerate(refdes):
        part = pcb.FindModuleByReference(rd)
        angle = (deg_per_idx * idx + start_angle) % 360;
        print "{0}: {1}".format(rd, angle)
        xmils = center[0] + math.cos(math.radians(angle)) * radius
        ymils = center[1] + math.sin(math.radians(angle)) * radius
        part.SetPosition(wxPoint(FromMils(xmils), FromMils(ymils)))
        part.SetOrientation(angle * -10)
        if hide_ref is not None:
            part.Reference().SetVisible(not hide_ref)
    print "Placement finished. Press F11 to refresh."

def drawSpiral(ID=5, w=0.25, s=0.25, n=1, x = 100, y = 100, ccw = False, layer=0):
    pcb = GetBoard()

    angle = 0
    count = 1
    while True:
        # Starting Point
        x1, y1 = getSpiralPoint(ID, w, s, x, y, angle)
        
        angle = getNewAngle(angle, ID, w, s, ccw)

        # End Point
        x2, y2 = getSpiralPoint(ID, w, s, x, y, angle)

        track = TRACK(pcb)
        track.SetStart(wxPointMM(x1,y1))
        track.SetEnd(wxPointMM(x2,y2))
        track.SetLayer(layer)
        track.SetNetCode(0)
        track.SetWidth(int(w*1000000))

        pcb.Add(track)
        
        #print track.GetStart()
        #print track.GetEnd()
        #print track.GetWidth()
        #print "Drew track from: (" + str(x1) + ", " + str(y1) + ") to ("  + str(x2) + ", " + str(y2) + ")"

        if math.fabs((angle / (2*math.pi))) >= n:
            OD = math.sqrt((x2-x)**2 + (y2-y)**2)*2 + 2*w
            r = (OD/2)/25.4
            A = (ID/25.4 + n*(w/25.4+s/25.4))/2
            #L = ((r**2)*(A**2))/(30*A-11*ID/25.4) #Unit conversion issues. Revise later.
            print "Drew spiral with " + str(count) + " segments."
            print "ID = " + str(ID) + "mm, OD = " + str(OD) + "mm"
            #print "L = " + str(L) + "uH"
            break
        else:
            count += 1

def getSpiralPoint(ID, w, s, x, y, angle):
    radius = ID / 2 + 0.5*w + math.fabs(angle/(2*math.pi))*(s+w)
    x1 = x + radius*math.cos(angle)
    y1 = y + radius*math.sin(angle)

    return x1,y1

def getNewAngle(angle, ID, w, s, ccw):
    finalAngle = math.ceil(angle/(2*math.pi))*2*math.pi  # The final angle for this loop.
    segments = 4

    x, y = getSpiralPoint(ID, w, s, 0, 0, finalAngle)
    radius = max([math.fabs(x),math.fabs(y)])
    circumference = 2*radius*math.pi
    segments = math.ceil(circumference / (2*w))
   
    if(ccw):
        return angle - 2*math.pi/segments
    else:
        return angle + 2*math.pi/segments


def deleteAll():
    pcb = GetBoard()

    tracks = pcb.GetTracks()
    for track in tracks:
        #print track.GetNetCode()
        #print track.GetWidth()
        #print track.GetStart()
        #print track.GetEnd()
        pcb.Delete(track)
