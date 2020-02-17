from __future__ import division
import pcbnew
import math

import FootprintWizardBase

#board = pcbnew.GetBoard()

class SpiralFootprintWizard(FootprintWizardBase.FootprintWizard):

    def GetName(self):
        return "Spiral"

    def GetDescription(self):
        return "Spiral Footprint Wizard"

    def GetValue(self):
        rounds = self.parameters["Spiral"]["loops_count"]
        return "Spiral%d" % rounds

    def GenerateParameterList(self):
        self.AddParam( "Spiral", "loops_count", self.uInteger, 2 )
        self.AddParam( "Spiral", "inner_diameter", self.uMM, 10.0 )
        self.AddParam( "Spiral", "outer_diameter", self.uMM, 25.0 )
        self.AddParam( "Spiral", "track_thickness", self.uMM, 0.25)
        self.AddParam( "Pads", "enable_outer", self.uBool, True)
        self.AddParam( "Pads", "enable_inner", self.uBool, True)
        self.AddParam( "Pads", "diameter", self.uMM, 1.0)
        self.AddParam( "Pads", "drill_diameter", self.uMM, 0.6)
        self.AddParam( "Segments", "enable_bezier", self.uBool, True)
        self.AddParam( "Segments", "target_length", self.uMM, 2.0)        # "optimal" curve length, trading off precision and overhead
        self.AddParam( "Segments", "min_per_circle", self.uInteger, 4 )   # need at least 4 curves per circle for a reasonable accuracy
        self.AddParam( "Segments", "max_per_circle", self.uInteger, 16 )  # do not create more than 16 curves per circles

    # build a circular pad
    def standardCirclePad(self,module,diameter,drill,pos,name):
        pad = pcbnew.D_PAD(module)
        pad.SetSize(pcbnew.wxSize(diameter,diameter))
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_STANDARD)
        pad.SetLayerSet(pad.StandardMask())
        pad.SetDrillSize(pcbnew.wxSize(drill, drill))
        pad.SetPos0(pos)
        pad.SetPosition(pos)
        pad.SetPadName(name)
        return pad

    def CheckParameters(self):
        p = self.parameters

    def BuildThisFootprint(self):
        p = self.parameters
        spiral_count          = int(p["Spiral"]["loops_count"])
        spiral_outer_diameter = p["Spiral"]["outer_diameter"]
        spiral_inner_diameter = p["Spiral"]["inner_diameter"]
        track_thickness       = p["Spiral"]["track_thickness"]
        pad_enable_inner      = bool(p["Pads"]["enable_inner"])
        pad_enable_outer      = bool(p["Pads"]["enable_outer"])
        pad_diameter          = p["Pads"]["diameter"]
        pad_drill_diameter    = p["Pads"]["drill_diameter"]
        enable_bezier         = bool(p["Segments"]["enable_bezier"])
        target_length         = p["Segments"]["target_length"]
        min_per_circle        = int(p["Segments"]["min_per_circle"])
        max_per_circle        = int(p["Segments"]["max_per_circle"])

        size_text = self.GetTextSize()  # IPC nominal

        # Gives a position and size to ref and value texts

        textposy = spiral_inner_diameter/4 + (size_text + self.GetTextThickness())/2
        self.draw.Reference( 0, textposy, size_text )

        textposy = -spiral_inner_diameter/4 + (size_text + self.GetTextThickness())/2
        self.draw.Value( 0, textposy, size_text )

        # Place outer and inner pads
        if pad_enable_outer:
            pad_outer_pos = pcbnew.wxPoint(-spiral_outer_diameter/2.0 + track_thickness/2 - pad_diameter/2.0, 0)
            pad_outer = self.standardCirclePad(self.module, pad_diameter, pad_drill_diameter, pad_outer_pos, "1")
            self.module.Add(pad_outer)

        if pad_enable_inner:
            pad_inner_pos = pcbnew.wxPoint(-spiral_inner_diameter/2.0 - track_thickness/2 + pad_diameter/2.0, 0)
            pad_inner = self.standardCirclePad(self.module, pad_diameter, pad_drill_diameter, pad_inner_pos, "2")
            self.module.Add(pad_inner)

        # Add spiral as "0" pad

        begin_radius = spiral_inner_diameter/2 + track_thickness/2
        end_radius = spiral_outer_diameter/2 - track_thickness/2
        # we put the spiral "pad" in the center between inner and outer
        # this point becomes an offset when computing the relative position of the points of the spiral
        offset_x = - (begin_radius + (end_radius-begin_radius)*float(int(spiral_count/2))/spiral_count)
        offset_y = 0
        pad_spiral_pos = pcbnew.wxPoint(offset_x, offset_y)
        
        pad_spiral = pcbnew.D_PAD(self.module)
        pad_spiral.SetSize(pcbnew.wxSize(track_thickness,track_thickness))
        pad_spiral.SetShape(pcbnew.PAD_SHAPE_CUSTOM)
        pad_spiral.SetAttribute(pcbnew.PAD_ATTRIB_CONN)
        pad_spiral.SetLayerSet(pad_spiral.ConnSMDMask())
        pad_spiral.SetPos0(pad_spiral_pos)
        pad_spiral.SetPosition(pad_spiral_pos)
        pad_spiral.SetPadName("0")
        # cubic bezier circle approximation
        # see http://spencermortensen.com/articles/bezier-circle/
        c = 0.551915024494
        primitives = []
        for circle_index in range(spiral_count):
            line_count = max(min_per_circle, min(max_per_circle, math.ceil(2*math.pi*(begin_radius + (end_radius-begin_radius)*float(circle_index)/spiral_count)/target_length)))
            # for besize curves: scale c by 4 divided by the line_count
            c_scaled = c * 4.0 / line_count
            for line_index in range(line_count):

                # polar coordinates of the two end points
                p0_angle = 2 * math.pi * float(line_index) / line_count
                p0_radius =  begin_radius + (end_radius-begin_radius)*(circle_index + float(line_index) / line_count) / spiral_count
                p1_angle = 2 * math.pi * float(line_index + 1) / line_count
                p1_radius =  begin_radius + (end_radius-begin_radius)*(circle_index + float(line_index + 1) / line_count) / spiral_count

                # transform to Cartesian coordinates
                p0_pos = pcbnew.wxPoint(-p0_radius*math.cos(p0_angle) - offset_x, p0_radius*math.sin(p0_angle) - offset_y)
                p1_pos = pcbnew.wxPoint(-p1_radius*math.cos(p1_angle) - offset_x, p1_radius*math.sin(p1_angle) - offset_y)

                # adding primitives one by one is slow, as it recreated the merged polygon everytime the method is called.
                # instead, we accumulate them in a list and call AddPrimitives at the end

                if not enable_bezier:
                    # Line version
                    #pad_spiral.AddPrimitive(p0_pos, p1_pos, track_thickness)
                    curve = pcbnew.PAD_CS_PRIMITIVE(pcbnew.S_SEGMENT)
                    curve.m_Start = p0_pos
                    curve.m_End = p1_pos
                    curve.m_Thickness = track_thickness
                    primitives.append(curve)
                else:
                    # Bezier version
                    #pad_spiral.AddPrimitive(p0_pos, p1_pos, ctrl0_pos, ctrl1_pos, track_thickness)
                    ctrl0_pos = pcbnew.wxPoint(-p0_radius*(math.cos(p0_angle) - c_scaled*math.sin(p0_angle)) - offset_x, p0_radius*(math.sin(p0_angle) + c_scaled*math.cos(p0_angle)) - offset_y)
                    ctrl1_pos = pcbnew.wxPoint(-p1_radius*(math.cos(p1_angle) + c_scaled*math.sin(p1_angle)) - offset_x, p1_radius*(math.sin(p1_angle) - c_scaled*math.cos(p1_angle)) - offset_y)
                    curve = pcbnew.PAD_CS_PRIMITIVE(pcbnew.S_CURVE)
                    curve.m_Start = p0_pos
                    curve.m_End = p1_pos
                    curve.m_Ctrl1 = ctrl0_pos
                    curve.m_Ctrl2 = ctrl1_pos
                    curve.m_Thickness = track_thickness
                    primitives.append(curve)
        pad_spiral.AddPrimitives(primitives)
        self.module.Add(pad_spiral)

# register into pcbnew
SpiralFootprintWizard().register()
