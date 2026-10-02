"""Pictures for the rev-2 hand-off (2026-09-27), into head-v2/out/print-rev2/:
  rev2_front.png       from the front: outside; the front shell cut away at X 16; the same from the post side
  rev2_ir_cutout.png   the IR cutout: his; the 80 mm3 the extension removes (red); as it prints
Posts orange, the real board green, placed where the pins put it. Run after export_campost_rev2.py.
    python head-v2/fixes/figure_rev2.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from PIL import Image, ImageDraw
from vox import load_stl
from zr import zrender
from export import rd, write_stl
from kit import common
from occ_load import load
import campost_rev2 as R
import ball_plus_rev2 as IR

OUT = os.path.dirname(config.out('print-rev2', 'x'))
TMP = os.path.dirname(config.out('rev2', 'x'))
GREY, MINUS, CAM, POST, RED = (215, 215, 210), (190, 190, 185), (45, 125, 75), (240, 140, 40), (215, 60, 50)


def tris(shape, name, lin=0.03):
    p = os.path.join(TMP, '_fig_' + name + '.stl'); write_stl(shape, p, lin=lin, ang=0.1); return load_stl(p)


def before_x(T, x):
    return T[T[:, :, 0].mean(1) < x]


def sheet(views, name, **kw):
    imgs = [zrender(m, *yp, **kw) for _, yp, m in views]
    out = Image.new('RGB', (sum(i.width for i in imgs), imgs[0].height + 30), 'white'); d = ImageDraw.Draw(out); x = 0
    for im, (t, _, _) in zip(imgs, views):
        out.paste(im, (x, 30)); d.text((x + 10, 8), t, fill=(30, 30, 30)); x += im.width
    out.save(os.path.join(OUT, name)); print('wrote', name)


if __name__ == '__main__':
    his = load_stl(R.BALL_PLUS)
    new = tris(rd(config.out('rev2', 'ball_plus_rev2.brep')), 'ball_plus')
    bm = load_stl(R.BALL_MINUS)
    removed = tris(common(IR.tools()['CUT_plus_ir_extend'], load(R.BALL_PLUS)[0]), 'ir_removed')
    cam = load_stl(os.path.join(config.CAMERA, 'camera_dummy_centred.stl')) + np.array([2.5, R.LENS_DY, R.LENS_DZ])
    posts = [(tris(rd(config.out('rev2', 'camera_post_%s_medium.brep' % tb)), 'post_' + tb, 0.02), POST) for tb in ('upper', 'lower')]
    cut16 = [(before_x(new, 16.0), GREY), (before_x(bm, 16.0), MINUS), (cam, CAM)] + posts
    sheet([('From the front', (-90, 0), [(new, GREY), (bm, MINUS), (cam, CAM)] + posts),
           ('Front shell cut away at X 16', (-90, 0), cut16),
           ('Same, from the post side', (-125, 15), cut16)], 'rev2_front.png', size=620, center=(0, 0, 52), ext=36)
    camb = cam[cam[:, :, 0].mean(1) < 14.0]            # the board behind the plate, so the plate's edge shows
    sheet([('Yours (rev 2), from the front, cut at X 16', (-90, 0), [(before_x(his, 16.2), GREY), (camb, CAM)] + posts),
           ('Red: the 80 mm3 the extension removes', (-90, 0), [(before_x(new, 16.2), GREY), (removed, RED), (camb, CAM)] + posts),
           ('Extended, as it prints', (-90, 0), [(before_x(new, 16.2), GREY), (camb, CAM)] + posts)],
          'rev2_ir_cutout.png', size=560, center=(0, 8, 52), ext=26)
