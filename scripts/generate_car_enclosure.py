#!/usr/bin/env python3
"""Reproducible, parametric BMW bench-enclosure prototype in millimetres.

Run with local/enclosure-venv/bin/python scripts/generate_car_enclosure.py.
Dependencies: manifold3d, trimesh, numpy, matplotlib, pillow, networkx.
This is native constructive-solid CAD, not a generated image or converted mesh.
"""
from pathlib import Path
import argparse
import json
import math
import zipfile

import manifold3d as md
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT if Path(__file__).parent.name == "source" else ROOT / "outputs/car_enclosure_v1"
DEFAULTS = {
    "units": "mm",
    "outer_length": 165.0,
    "outer_width": 125.0,
    "base_height": 70.0,
    "wall": 3.0,
    "floor": 3.0,
    "corner_radius": 5.0,
    "lid_thickness": 2.8,
    "lid_skirt_depth": 5.0,
    "slip_clearance_per_side": 0.4,
    "pi_case_assumed_length": 110.0,
    "pi_case_assumed_width": 85.0,
    "pi_case_assumed_height": 45.0,
    "pi_xy_allowance_total": 2.0,
    "pi_x": 8.0,
    "pi_y": 8.0,
    "pi_support_z": 7.0,
    "splitter_allowance_length": 38.0,
    "splitter_allowance_width": 48.0,
    "splitter_allowance_height": 8.0,
    "splitter_x": 119.0,
    "splitter_y": 34.0,
    "splitter_tray_outer_length": 43.0,
    "splitter_tray_outer_width": 54.0,
    "splitter_tray_height": 15.0,
    "cable_exit_centers_x": [30.0, 79.0, 145.0],
    "cable_exit_slot_width": 14.6,
    "cable_exit_bottom_z": 10.0,
    "cable_insert_diameters": [4.0, 5.0, 6.0, 8.0],
    "assumptions": [
        "Vilros case 110 x 85 x 45 is a conservative assumed bounding box, not a measurement.",
        "Splitter 38 x 48 x 8 is a design allowance, not manufacturer or measured geometry.",
        "Console clearance, plugs, cable diameters, bend radii and printer fit are unmeasured.",
        "Only the existing cased Pi, bare no-barrel splitter and loose cable slack go inside.",
        "PLA prototype for supervised fit/desk/parked testing; remove from hot parked car."
    ]
}


def box(x, y, z, dx, dy, dz):
    return md.Manifold.cube((dx, dy, dz)).translate((x, y, z))


def rr(x, y, z, dx, dy, dz, r=2):
    c = md.CrossSection.square((dx-2*r, dy-2*r)).offset(r, circular_segments=32)
    return md.Manifold.extrude(c, dz).translate((x+r, y+r, z))


def cyl(x, y, z, r, h):
    return md.Manifold.cylinder(h, r, circular_segments=32).translate((x, y, z))


def poly_xz(points, depth, y=0):
    # Extrude an XZ profile in +Y; reflection gives the required handedness.
    p = md.Manifold.extrude(md.CrossSection([points]), depth)
    return p.rotate((90, 0, 0)).translate((0, y+depth, 0))


def union(items):
    return md.Manifold.batch_boolean(items, md.OpType.Add)


def subtract(a, items):
    return a - union(items) if items else a


def mesh_of(solid):
    m = solid.to_mesh()
    return trimesh.Trimesh(vertices=np.array(m.vert_properties)[:, :3],
                           faces=np.array(m.tri_verts), process=True)


def on_bed(solid):
    b = solid.bounding_box()
    return solid.translate((-b[0], -b[1], -b[2]))


def create_geometry(p):
    L, W, H = p["outer_length"], p["outer_width"], p["base_height"]
    t, f, r = p["wall"], p["floor"], p["corner_radius"]
    px, py, pz = p["pi_x"], p["pi_y"], p["pi_support_z"]
    pl, pw, ph = (p["pi_case_assumed_"+q] for q in ("length", "width", "height"))
    sx, sy = p["splitter_x"], p["splitter_y"]
    sl, sw, sh = (p["splitter_tray_"+q] for q in ("outer_length", "outer_width", "height"))
    assert px+pl+2 < sx+3, "Pi bay and splitter bay collide"
    assert sx+sl <= L-t+0.05 and sy+sw < W-t, "Splitter bay exceeds base"
    assert px+pl < L-t and py+pw < W-t and pz+ph+3 < H, "Pi envelope exceeds base"

    base = rr(0, 0, 0, L, W, H, r) - rr(t, t, f, L-2*t, W-2*t, H+2, 2)
    # Vent slots in the floor; ribs remain underneath the assumed case.
    cuts = []
    for yy in np.arange(18, 88, 8):
        cuts.append(rr(18, yy, -1, 86, 4, f+2, 1.8))
    for yy in (15, 24, 99, 108):
        cuts.append(rr(124, yy, -1, 29, 4, f+2, 1.8))
    # Support-free side windows with 45-degree roofs; 12 mm span.
    for yy in range(14, 111, 20):
        profile = [(0, 0), (12, 0), (12, 17), (6, 23), (0, 17)]
        v = poly_xz(profile, t+2).rotate((0, 0, 90))
        cuts.extend([v.translate((t+1, yy, 21)), v.translate((L+1, yy, 21))])
    for xx in range(18, 110, 22):
        cuts.append(poly_xz([(0,0),(12,0),(12,16),(6,22),(0,16)], t+2, -1).translate((xx,0,23)))
    # Open top entries admit already attached plugs; removable inserts close them.
    for xx in p["cable_exit_centers_x"]:
        cuts.append(box(xx-p["cable_exit_slot_width"]/2, W-t-1, p["cable_exit_bottom_z"],
                        p["cable_exit_slot_width"], t+2, H))
    # Four lid-clip windows, two on each long wall. 14 mm bridges print without supports.
    for xx in (6, 109):
        for yy in (-1, W-t-1):
            cuts.append(box(xx, yy, H-7.4, 14.8, t+2, 2.6))
    base = subtract(base, cuts)
    # Raised Pi support rails; 4 mm free air under the retained existing case.
    additions = []
    for yy in (py, py+pw-8):
        additions.append(rr(px, yy, f-0.1, pl, 8, pz-f+0.1, 2))
    # Low corner stops keep the assumed case laterally located without blocking ports.
    for xx in (px-2.6, px+pl+1.0):
        for yy in (py, py+pw-7):
            additions.append(box(xx, yy, f-0.1, 1.6, 7, 7.1))
    for xx in (px, px+pl-9):
        for yy in (py-2.6, py+pw+1.0):
            additions.append(box(xx, yy, f-0.1, 9, 1.6, 7.1))
    # Side fences capture the removable splitter tray while keeping its cable ends open.
    for yy in (sy-2.0, sy+sw+0.4):
        additions.append(box(sx+3, yy, f-0.1, sl-6, 1.6, 4.6))
    # Individual integral pillars under keeper legs avoid unsupported corner feet.
    bridge_ys = (py+6, py+pw-4)
    left_leg_x, right_leg_x = px-3.1, px+pl+0.7
    for yy in bridge_ys:
        for xx in (left_leg_x, right_leg_x):
            additions.append(box(xx-0.6, yy-0.6, 0, 3.6, 9.2, 7))
    base += union(additions)
    # Keeper slots start at the floor; legs remain trapped by the installed outer lid.
    slots=[]
    for yy in bridge_ys:
        for xx in (left_leg_x, right_leg_x):
            slots.append(box(xx-0.2, yy-0.2, -1, 2.8, 8.4, H+2))
    slots.append(box(sx-0.2,sy-0.2,f,sl+0.4,sw+0.4,sh+3))
    base = subtract(base, slots)

    # Lid prints exterior-face-down. Its skirt points UP in the STL, DOWN assembled.
    lt = p["lid_thickness"]
    lid = rr(0, 0, 0, L, W, lt, r)
    vents=[]
    for xx in np.arange(16, 108, 8):
        for yy, length in ((20,27), (51,27), (82,24)):
            vents.append(rr(xx, yy, -1, 4, length, lt+2, 1.8))
    for yy in np.arange(20, 108, 9):
        vents.append(rr(126, yy, -1, 25, 4, lt+2, 1.8))
    lid = subtract(lid, vents)
    c = p["slip_clearance_per_side"]
    # Discontinuous skirt leaves cable exits, clips and keeper seats clear.
    skirt=[]
    for xx in (t+c, L-t-c-1.8):
        skirt.append(box(xx, 40, lt-0.1, 1.8, 36, p["lid_skirt_depth"]+0.1))
    for xx, length in ((35,25),(85,19),(130,22)):
        skirt.append(box(xx, W-t-c-1.8, lt-0.1, length, 1.8, p["lid_skirt_depth"]+0.1))
    lid += union(skirt)

    # Pi keeper prints on its broad flat side. Two copies are required.
    # Tall ears contact the cover so the legs cannot lift out of their sockets.
    span = right_leg_x-left_leg_x+2.4
    keep_top = H-0.35
    keeper = union([
        box(0,0,0,2.4,8,keep_top),
        box(span-2.4,0,0,2.4,8,keep_top),
        box(0,0,pz+ph+1.6,span,8,2.4),
    ])
    keeper_print = on_bed(keeper.rotate((90,0,0)))

    # Splitter carrier has no electrical fasteners, guessed posts or component clamps.
    # Open ends accept all three plugs. An air-spaced removable cap cages the PCB.
    tray = rr(0,0,0,sl,sw,2.4,2)
    tray += box(0,0,0,1.8,sw,sh)
    tray += box(sl-1.8,0,0,1.8,sw,sh)
    # Broad recessed bottom never presses on the board; loose edge spacers are optional.
    for xx in (1.8, sl-4.4):
        tray += box(xx,4,2.3,2.6,sw-8,1.5)
    # Low rounded end lips prevent sliding while allowing the receptacles to overhang.
    for yy in (0,sw-1.8):
        tray += rr(4,yy,2.3,sl-8,1.8,1.6,0.7)
    cap = rr(0,0,0,sl,sw,2.2,2)
    cap = subtract(cap,[rr(xx,9,-1,4,sw-18,4,1.8) for xx in (8,16,24,32)])
    # Friction skirt on the two long sides; broad open plug exits remain 11 mm tall.
    for xx in (2.15, sl-3.55):
        cap += box(xx,6,2.1,1.4,sw-12,4.1)
    # Small detents; optional fit-sanding, never load the PCB or connector bodies.
    for xx in (1.85, sl-3.55):
        cap += box(xx,22,4.8,1.7,10,0.55)
    # Floor key: tray sits between fences, on floor, leaving the power/host leads aligned.

    # Removable C-clips print on side. Their lower jaw enters the 14.8 mm wall window.
    gap = lt+4.8+0.4
    clip_profile=[(0,0),(8,0),(8,2.2),(2.2,2.2),
                  (2.2,2.2+gap),(8,2.2+gap),(8,4.4+gap),(0,4.4+gap)]
    clip=md.Manifold.extrude(md.CrossSection([clip_profile]),14.0)

    # Replaceable cable inserts. Sizing is by actual cable jacket, not USB connector.
    # Both halves print with cable axis vertical, so bores require no support.
    gates={}
    gate_assembled={}
    gate_width=14.0
    z0=p["cable_exit_bottom_z"]
    bore_z=z0+7
    for d in p["cable_insert_diameters"]:
        # 0.4 mm total clearance makes a gentle cable guide; never claim a certified clamp.
        rad=(d+0.4)/2
        def gate_blank(z,height):
            core=box(-gate_width/2,-0.2,z,gate_width,t+0.4,height)
            # 45 degree lips in section make the neck and outer flanges support-free.
            profile=[(-8.2,-2), (8.2,-2), (8.2,-1.4), (7.0,-0.2),
                     (7.0,t+0.2),(8.2,t+1.4),(8.2,t+2),(-8.2,t+2),
                     (-8.2,t+1.4),(-7.0,t+0.2),(-7.0,-0.2),(-8.2,-1.4)]
            return md.Manifold.extrude(md.CrossSection([profile]),height).translate((0,0,z))
        bore=md.Manifold.cylinder(t+6,rad,circular_segments=40).rotate((90,0,0)).translate((0,t+3,bore_z))
        lower=gate_blank(z0,7)-bore
        upper=gate_blank(bore_z,H-bore_z-0.25)-bore
        k=f"{d:g}mm"
        gates[f"cable_insert_{k}_lower"]=on_bed(lower.rotate((90,0,0)))
        gates[f"cable_insert_{k}_upper"]=on_bed(upper.rotate((90,0,0)))
        gate_assembled[k]=(lower,upper)

    # Two low-cost gauges: entire footprint and actual Pi bay opening, plus height stick.
    gauge = rr(0,0,0,L,W,2.0,r)-rr(3,3,-1,L-6,W-6,4,2)
    inner=rr(px-3,py-3,0,pl+6,pw+6,2,2)-box(px-1,py-1,-1,pl+2,pw+2,4)
    gauge += inner
    gauge += box(3,py+pw/2,0,px-3,3,2)
    gauge += box(px+pl+3,py+pw/2,0,L-3-(px+pl+3),3,2)
    gauge += box(px+pl/2,py+pw+3,0,3,W-3-(py+pw+3),2)
    height_gauge=box(0,0,0,12,75.4,2.4)
    # Printed shims can take up excess slack around a smaller case/PCB, without adhesive.
    shim_parts={f"shim_{n:g}mm":box(0,0,0,12,18,n) for n in (1,2,4,8)}

    parts={"base":base,"lid":lid,"pi_keeper_print_2":keeper_print,
           "splitter_tray":tray,"splitter_cap":cap,
           "lid_clip_print_4":clip,"fit_gauge_footprint_and_pi":gauge,
           "fit_gauge_height":height_gauge,**gates,**shim_parts}
    # Display-only assumed envelopes never go into STL or 3MF print packages.
    pi_dummy=rr(px,py,pz,pl,pw,ph,3)
    fan_cut=cyl(px+pl/2,py+pw/2,pz+ph-1,20,2)
    pi_dummy -= fan_cut
    splitter_dummy=rr(sx+3,sy+3,f+4,sl-6,sw-6,1.6,1)
    assembled={
        "base":base,
        "lid":lid.rotate((180,0,0)).translate((0,W,H+lt)),
        "keeper_front":keeper.translate((left_leg_x,bridge_ys[0],0)),
        "keeper_rear":keeper.translate((left_leg_x,bridge_ys[1],0)),
        "splitter_tray":tray.translate((sx,sy,f)),
        "splitter_cap":cap.rotate((180,0,0)).translate((sx,sy+sw,f+sh+2.2)),
        "pi_case_assumed":pi_dummy,
        "splitter_assumed":splitter_dummy,
    }
    # Select 6 mm cable guides only for illustration; actual printed size is user's choice.
    for n,xx in enumerate(p["cable_exit_centers_x"]):
        for side,solid in zip(("lower","upper"),gate_assembled["6mm"]):
            assembled[f"entry_{n}_{side}"]=solid.translate((xx,W-t,0))
    for n,xx in enumerate((6.4,109.4)):
        cfront=clip.rotate((90,0,90)).translate((xx,-2.2,H-7))
        assembled[f"clip_front_{n}"]=cfront
        assembled[f"clip_rear_{n}"]=cfront.rotate((0,0,180)).translate((2*xx+14,W,0))
    return parts, assembled


def check_export(parts, out):
    path=out/"STL"
    path.mkdir(exist_ok=True)
    report={}
    for name,solid in parts.items():
        s=on_bed(solid)
        mesh=mesh_of(s)
        components=len(mesh.split(only_watertight=False))
        ext=np.array(mesh.extents)
        record={"watertight":bool(mesh.is_watertight),"consistent_winding":bool(mesh.is_winding_consistent),
                "connected_components":components,"positive_volume_mm3":float(mesh.volume),
                "bounds_mm":mesh.bounds.round(4).tolist(),"size_mm":ext.round(3).tolist(),
                "triangles":len(mesh.faces),"fits_180mm_cube":bool(np.all(ext<=180.0))}
        assert record["watertight"] and record["consistent_winding"] and components==1 and mesh.volume>0, (name,record)
        assert record["fits_180mm_cube"], (name,ext)
        mesh.export(path/(name+".stl"))
        # Re-import exported binary STL, checking the deliverable, not just source solids.
        rt=trimesh.load_mesh(path/(name+".stl"),process=True)
        assert rt.is_watertight and rt.is_winding_consistent and len(rt.split())==1 and rt.volume>0, name
        report[name]=record
    (out/"mesh_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def draw_mesh(ax,solid,color,alpha=1):
    m=mesh_of(solid)
    if not hasattr(ax,"cad_triangles"):
        ax.cad_triangles=[];ax.cad_colors=[]
    light=np.array([-.4,-.5,1]);light/=np.linalg.norm(light)
    intensity=.57+.43*np.maximum(0,m.face_normals@light)
    colors=np.tile(matplotlib.colors.to_rgba(color),(len(m.faces),1))
    colors[:,:3]*=intensity[:,None]
    # Opaque, globally depth-sorted faces avoid misleading transparent triangle artifacts.
    ax.cad_triangles.extend(m.vertices[m.faces]);ax.cad_colors.extend(colors)


def raster_scene(items, width=1080, height=640, azimuth=-60, elevation=28):
    """Orthographic z-buffer rendering of actual exported-style mesh triangles."""
    from PIL import Image
    az,el=np.radians([azimuth,elevation])
    n=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    right=np.array([-np.sin(az),np.cos(az),0.0]);up=np.cross(n,right)
    vlist=[];flist=[];clist=[];offset=0
    light=np.array([-.3,-.6,1.0]);light/=np.linalg.norm(light)
    for solid,color in items:
        m=mesh_of(solid);vlist.append(m.vertices);flist.append(m.faces+offset);offset+=len(m.vertices)
        shade=.54+.46*np.maximum(0,m.face_normals@light)
        col=np.array(matplotlib.colors.to_rgb(color))*255
        clist.extend(np.clip(shade[:,None]*col,0,255).astype(np.uint8))
    vertices=np.vstack(vlist);faces=np.vstack(flist);colors=np.array(clist)
    proj=np.column_stack((vertices@right,vertices@up,vertices@n))
    bounds=np.array([proj[:,:2].min(axis=0),proj[:,:2].max(axis=0)])
    scale=min((width-54)/(bounds[1,0]-bounds[0,0]),(height-44)/(bounds[1,1]-bounds[0,1]))
    center=bounds.mean(axis=0)
    proj[:,0]=(proj[:,0]-center[0])*scale+width/2
    proj[:,1]=height/2-(proj[:,1]-center[1])*scale
    depth=np.full((height,width),-np.inf);pixels=np.empty((height,width,3),dtype=np.uint8);pixels[:]=[238,242,244]
    for indices,color in zip(faces,colors):
        tri=proj[indices];x0,y0,z0=tri[0];x1,y1,z1=tri[1];x2,y2,z2=tri[2]
        den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(den)<1e-8:continue
        xmin=max(0,int(np.floor(tri[:,0].min())));xmax=min(width-1,int(np.ceil(tri[:,0].max())))
        ymin=max(0,int(np.floor(tri[:,1].min())));ymax=min(height-1,int(np.ceil(tri[:,1].max())))
        if xmin>xmax or ymin>ymax:continue
        yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1];xx=xx+.5;yy=yy+.5
        aa=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
        bb=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den;cc=1-aa-bb
        zz=aa*z0+bb*z1+cc*z2
        zd=depth[ymin:ymax+1,xmin:xmax+1]
        mask=(aa>=-1e-7)&(bb>=-1e-7)&(cc>=-1e-7)&(zz>zd)
        zd[mask]=zz[mask];pixels[ymin:ymax+1,xmin:xmax+1][mask]=color
    return Image.fromarray(pixels)


def preview(parts,a,p,out):
    from PIL import Image,ImageDraw,ImageFont
    from matplotlib.font_manager import findfont
    font=lambda size,bold=False:ImageFont.truetype(findfont("DejaVu Sans" if not bold else matplotlib.font_manager.FontProperties(family="DejaVu Sans",weight="bold")),size)
    canvas=Image.new("RGB",(2400,1700),(238,242,244));d=ImageDraw.Draw(canvas)
    ink="#172535"
    d.text((60,40),"BMW Pi enclosure · printable fit prototype",fill=ink,font=font(46,True))
    d.text((60,110),"Actual CAD geometry · millimetres · assumed hardware fit · PLA for supervised testing only",fill=ink,font=font(23))
    cut=a["base"]-box(-1,-1,17,p["outer_length"]+2,4.1,p["base_height"])-box(p["outer_length"]-3.1,-1,17,4.1,p["outer_width"]+2,p["base_height"])
    colors=lambda name: "#dca33d" if ("keeper" in name or "clip_" in name or "entry_" in name) else "#59aa90" if "splitter" in name else "#8b9298" if name=="pi_case_assumed" else "#3b5361"
    open_items=[(cut,"#3b5361")]+[(s,colors(name)) for name,s in a.items() if name not in ("base","lid")]
    exploded=[(a["base"],"#3b5361"),(a["lid"].translate((0,0,35)),"#8eb8c7"),
              (a["splitter_tray"].translate((0,0,20)),"#59aa90"),(a["splitter_cap"].translate((0,0,39)),"#9ad7bc")]
    exploded += [(a[key].translate((0,0,10)),"#dca33d") for key in ("keeper_front","keeper_rear")]
    top=[(a[name],colors(name)) for name in ("base","pi_case_assumed","splitter_tray","splitter_assumed","keeper_front","keeper_rear")]
    closed=[(a["base"],"#3b5361"),(a["lid"],"#8eb8c7")]+[(s,"#dca33d") for name,s in a.items() if name.startswith("entry_") or name.startswith("clip_")]
    scenes=[(open_items,"CUTAWAY · existing cased Pi + protected splitter",-60,28),
            (exploded,"SERVICEABLE · removable cover and printed clips",-60,28),
            (top,"LAYOUT · 165 × 125 mm body",-90,90),
            (closed,"CLOSED · nominal envelope below 170 × 130 × 76 mm",-60,28)]
    for i,(items,title,az,el) in enumerate(scenes):
        x=60+(i%2)*1160;y=195+(i//2)*715
        d.text((x,y),title,fill=ink,font=font(25,True))
        canvas.paste(raster_scene(items,1080,625,az,el),(x,y+50))
    d.text((60,1620),"Print the fit gauges first. Both chargers stay outside. No console-fit, heat-rating or roadworthiness guarantee.",fill=ink,font=font(24))
    canvas.save(out/"preview.png")


def simple_3mf(parts,out):
    # One part per file, model-only 3MF. Deliberately no printer/filament/G-code presets.
    import xml.etree.ElementTree as ET
    ns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("",ns)
    d=out/"3MF_model_only";d.mkdir(exist_ok=True)
    for name,solid in parts.items():
        if name.startswith("shim_") or name.startswith("cable_insert_"):continue
        mesh=mesh_of(on_bed(solid))
        model=ET.Element(f"{{{ns}}}model",{"unit":"millimeter","{http://www.w3.org/XML/1998/namespace}lang":"en-US"})
        resources=ET.SubElement(model,f"{{{ns}}}resources")
        obj=ET.SubElement(resources,f"{{{ns}}}object",{"id":"1","type":"model","name":name})
        xm=ET.SubElement(obj,f"{{{ns}}}mesh"); vs=ET.SubElement(xm,f"{{{ns}}}vertices")
        for v in mesh.vertices:
            ET.SubElement(vs,f"{{{ns}}}vertex",dict(zip(("x","y","z"),(f"{x:.6f}" for x in v))))
        fs=ET.SubElement(xm,f"{{{ns}}}triangles")
        for tri in mesh.faces:
            ET.SubElement(fs,f"{{{ns}}}triangle",dict(zip(("v1","v2","v3"),(str(int(x)) for x in tri))))
        build=ET.SubElement(model,f"{{{ns}}}build");ET.SubElement(build,f"{{{ns}}}item",{"objectid":"1"})
        with zipfile.ZipFile(d/(name+".3mf"),"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml",'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
            z.writestr("_rels/.rels",'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
            z.writestr("3D/3dmodel.model",ET.tostring(model,encoding="utf-8",xml_declaration=True))


def instructions(p,report,out):
    text="""# BMW Pi enclosure v1 — printable PLA fit prototype

This contains real, separate, flat-oriented STL parts and model-only 3MF files for the Bambu A1 mini. It encloses the Pi **inside its existing Vilros case**, the bare 8086 no-barrel USB-C/PWR splitter and modest loose cable slack. The wall adapter and Anker 12 V car charger stay outside.

**PLA is a supervised fit/desk/parked-test prototype only. Remove it from a hot parked car.** No automotive temperature rating, crash retention, unattended power use or console fit is claimed. A fan does not make PLA heat resistant.

## Assumed dimensions — print the gauges before the enclosure

- Body: **165 × 125 × 70 mm**. Lid: 2.8 mm. Installed clips/guides keep the nominal overall envelope below **170 × 130 × 76 mm**.
- Existing Pi case: assumed **110 × 85 × 45 mm**, with 2 mm total XY allowance. It sits 4 mm above the base floor; the keepers allow about 1.6 mm above its top.
- Splitter: a **38 × 48 × 8 mm design allowance**, not a measured or maker dimension. Tray opening approximately **39.4 × 54 mm**, open at both cable ends, with an insulated bottom and removable raised cap. Check solder and components clear the carrier and cap.
- Case, splitter, cable and console dimensions were deliberately guessed at your request. Do not force a mismatched part or drill around a live board.

Print `fit_gauge_footprint_and_pi.stl` first. Its outside checks the enclosure body footprint; its inner opening checks the assumed Pi case. Allow an additional 2.5 mm at front/rear for clips/cable guides. Print `fit_gauge_height.stl` and stand its 75.4 mm dimension upright to check console-lid clearance. The gauge is a fit check, not a template to cut the console. If the case does not enter easily, change the JSON/source and regenerate; do not scale all STLs because clip clearances would change.

## Print list

| Part | Quantity | Purpose |
| --- | ---: | --- |
| `base.stl` | 1 | Vented body, Pi supports and keeper sockets |
| `lid.stl` | 1 | Vented lift-off cover; print as supplied, exterior face on bed |
| `pi_keeper_print_2.stl` | 2 | Tall-eared bridges hold the existing case near its ends |
| `splitter_tray.stl` | 1 | Electrically insulating removable carrier; no metal fasteners |
| `splitter_cap.stl` | 1 | Raised, vented friction-fit board cover |
| `lid_clip_print_4.stl` | 4 | Reusable C clips on the front/rear rim windows |
| `cable_insert_*_lower/upper.stl` | 3 matched pairs | Choose 4, 5, 6 or 8 mm jacket guide sizes; print only needed sizes |
| `shim_1/2/4/8mm.stl` | As needed | Optional loose fit spacers; do not block vents or contact components |

**A1 mini starting settings:** 0.4 mm nozzle, 0.20 mm layers, 4 wall loops, 5 top/bottom layers, 15–20% gyroid infill, your filament's PLA preset, supports off. Use a small brim only if needed; the 165 mm base leaves 7.5 mm per side on a 180 mm bed, so a 3 mm brim fits. Keep skirt/prime/calibration features clear. Print base and lid on separate plates. All files are oriented on the bed and fit inside 180 × 180 × 180 mm. Do not auto-orient the keepers/clips/guides back upright. Small vent bridges and 45° side-window roofs are intentional.

STL and model-only 3MF files contain **no printer commands**. Select your own A1 mini and PLA preset. Nothing has been sent to a printer. Physical print strength and fit remain untested.

## Assembly

1. Finish the two fit checks. Deburr all cable-contact edges and elephant's foot. Dry-fit the outer lid, four C clips and two keepers with no electronics. A clip should slide by hand; stop if it turns white or needs force. PLA clips are service clips, not repeated-flex hinges.
2. Shut down and unplug the Pi. Keep the Vilros case, fan and heatsinks installed. Set the case on the two raised support rails with its useful connector side toward the open rear cable space/right lane. The raised case clears the floor vents. Reorient if needed, without pinching plugs.
3. Insert the two keeper bridges into their four floor sockets near the case ends. The bars sit just above the case; tall ears are trapped by the outer lid. Keep the central fan inlet/exhaust open. A smaller case can use loose shims against solid exterior surfaces; never shim over vents, under unstable feet, or against circuit boards. If the keepers press on the case, remove them and revise the assumed case height.
4. Place the unplugged bare splitter in the separate tray, component side up. It rests on insulating printed surfaces, not screw posts. Check underside solder joints have room and the thin carrier cap does not contact components. Both short ends are broadly open for plugs. Use the actual printed port labels to route **POWER → existing supply**, **DATA POWER → Pi USB-C**, **USB2 DATA → BMW host/Mac**; do not infer port identity from the CAD illustration. Do not enclose a barrel-jack variant in this design.
5. Seat the splitter cap by hand, then put the carrier between its low floor fences in the right-hand lane. The generous pocket is a protective cage, not a precision clamp. Optional small loose shims may touch clear PCB edges only, never solder/components. If it rattles or a plug is side-loaded, revise the insert before vehicle use.
6. Route three external leads (power, host data, AUX) out the rear entry slots. Place the lower and upper matched guide halves around each cable jacket, then slide the pair into its wall slot. Sizes refer to jacket diameter with 0.4 mm nominal diametral clearance. Choose the smallest guide that closes freely without pinching. These rounded guides protect edges; **they are not rated strain-relief clamps**. Keep a relaxed internal service loop and support external leads so pulling them cannot load the splitter sockets. Reuse existing ties only if available; they are optional, not a required purchase.
7. Use only modest slack inside. Make broad bends in the rear/right/upper perimeter space and leave the center fan path clear. Do not pack an entire long cable coil into the case. If your cable plugs need more bend room, let a relaxed loop remain outside rather than forcing it under the lid.
8. Lower the lid with its short locating skirt inside the base. Tall keeper ears retain the Pi bridges. Slide four C clips over the lid rim; each lower jaw goes into a matching 14.8 mm wall window, with its upper jaw above the lid. Release clips before lifting the lid. The cover does not require screws, glue or magnets.
9. Run a supervised desk playback test with the lid fitted, check case/connector clearance and compare temperatures with your open setup. This does not certify hot-car operation. A loose enclosure must not obstruct controls or move into a pedal area. Remove it after testing; permanent vehicle retention and thermal validation remain separate work.

## Files, regeneration and evidence

- `parameters.json`: editable design assumptions. `source/generate_car_enclosure.py`: reproducible CAD source; authoritative project script is `scripts/generate_car_enclosure.py`.
- `mesh_validation.json`: exported-STL round-trip checks: watertight, consistent winding, exactly one connected component, positive volume and 180 mm limit for every part.
- `preview.png`: render of the actual CAD, with explicitly assumed hardware envelopes. Equipment envelopes are not printable parts.
- `3MF_model_only/`: individual model-only files for major parts, without material/machine/G-code settings. STL is the universal fallback.
- `slicer_validation.md`: records the actual Bambu Studio import/slice checks separately from geometric checks.

Run from the repository: `local/enclosure-venv/bin/python scripts/generate_car_enclosure.py --parameters outputs/car_enclosure_v1/parameters.json`. Dependencies: manifold3d, trimesh, numpy, matplotlib, pillow. Dimensions are millimetres. The source uses solid booleans; parameters are not merely annotations. Layout assertions stop incompatible case/tray dimensions, and every output must pass mesh checks.

Sources checked 2026-10-13: maker product https://lectronz.com/products/usb-c_pwr-splitter confirms connector roles and variants but supplies no mechanical drawing; actual user board photos IMG_3787–3789 show the no-barrel variant. A1 mini official specification https://store.bblcdn.com/6cddc28fcb5a4a34975cfc7a23c83491.pdf confirms the 180 mm build volume and PLA support. Neither source establishes this enclosure's fit, retention or thermal safety.
"""
    text=text.replace("Dependencies: manifold3d, trimesh, numpy, matplotlib, pillow.", "Dependencies: manifold3d, trimesh, numpy, matplotlib, pillow, networkx.")
    text=text.replace("STL and model-only 3MF files contain", "The preview colors identify parts; everything can be printed in the same PLA.\n\nSTL and model-only 3MF files contain")
    text=text.replace("- `preview.png`:", "- `assembly_validation.json`: nominal pairwise solid-intersection checks, including the assumed equipment; no positive-volume clashes.\n- `preview.png`:")
    (out/"ASSEMBLY.md").write_text(text)


def package(out):
    archive=out/"BMW_Pi_enclosure_v1_print_pack.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for file in sorted(out.rglob("*")):
            if not file.is_file() or file==archive or "slicer_work" in file.parts:continue
            z.write(file,file.relative_to(out))


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--parameters",type=Path)
    args=parser.parse_args()
    p=DEFAULTS.copy()
    if args.parameters:p.update(json.loads(args.parameters.read_text()))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"parameters.json").write_text(json.dumps(p,indent=2)+"\n")
    parts,assembly=create_geometry(p)
    from itertools import combinations
    collisions=[]
    for (name,a),(other,b) in combinations(assembly.items(),2):
        volume=(a^b).volume()
        if volume>0.02:collisions.append({"parts":[name,other],"overlap_mm3":volume})
    assert not collisions, collisions
    (OUT/"assembly_validation.json").write_text(json.dumps({"positive_volume_overlaps":collisions,"tolerance_mm3":0.02,"assumed_equipment_included":True,"note":"Checks nominal CAD only, not real-world fit."},indent=2)+"\n")
    report=check_export(parts,OUT)
    simple_3mf(parts,OUT)
    instructions(p,report,OUT)
    preview(parts,assembly,p,OUT)
    source=OUT/"source";source.mkdir(exist_ok=True)
    (source/Path(__file__).name).write_text(Path(__file__).read_text())
    package(OUT)
    print(json.dumps({"parts":len(parts),"all_mesh_checks_passed":True,"output":str(OUT)},indent=2))


if __name__=="__main__":main()
