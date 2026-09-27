SUPERSEDED 2026-09-19 -- kept, not deleted, because it records what was tried.

These are the fusion/ meshes decimated to a face count Fusion's Convert Mesh was
expected to cope with (4-8k). The premise was wrong: what defeats Convert Mesh in a
marching-cubes mesh is that it has no recognisable structure -- a flat face is a few
hundred not-quite-coplanar triangles, a bore is a facet ring -- and decimating lowers
the count without adding any. Fewer triangles, same problem.

Use instead:
  ../step/*.step            post, axle, cap_minus, ball_plus, ball_minus
                            -- real solids, no Convert Mesh step at all
  ../fusion-solid/*_blank.obj   fork and roots, the only genuinely organic parts,
                            with the small features stripped out for ../features.md

See ../step/README.md.
