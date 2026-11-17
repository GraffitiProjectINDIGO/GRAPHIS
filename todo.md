# common

- configure if using abs or rel path
- change image paths?

# write data

- unsafe write for image regions which are malformed
- implement exiv2 writes in IPTC-IRIS
- write single-ring polygons as rbVertices (2025.1): after removing the last hole or reducing a multipolygon to one
  part, `remove_multigeometry_part` / `detach_multigeometry_part` in `imgregion_adapter.py` keep `rbCoordinates`

# external import

- import geometries from csv and JSON (e.g. from AI)

# image size

- Once I saw a Fuji GFXII image where image shape was wrongly in exif, or at least one of the standard tags showed the thumbnail size. Maybe use max on all image dimension tags
- check for problematic image sizes
- option to state image size by hand (for strange raw shapes)
