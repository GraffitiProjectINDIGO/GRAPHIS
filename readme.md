![ ](app/icons/INDIGO_logoGRAPHIS_text.png)
# Graphis  

## Table of contents
* [General info](#general-info)
* [Creating binaries with PyInstaller](#create_binary)


## General info
Since its [2019.1 version](https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata-2019.1.html), the IPTC Photo Metadata Standard has facilitated the creation of image regions: groupings of image pixels—defined by a circle, rectangle, or any other polygonal shape—which can be annotated with region-specific metadata. GRAPHIS (<ins>G</ins>enerate <ins>R</ins>egions and <ins>A</ins>nnotations for <ins>PH</ins>otos using the <ins>I</ins>PTC <ins>S</ins>tandard) is an open-source and freely available Windows-based software to create or change IPTC image regions, annotate them with graffiti descriptions or transcriptions, and visualise them. The backend of GRAPHIS is programmed in [Python 3](https://www.python.org), while PySide—also known as [Qt for Python](https://wiki.qt.io/Qt_for_Python)—was used for the Graphical User Interface (GUI). In addition, GRAPHIS relies on many other pieces of software, of which the most prominent ones function as interfaces for data handling: [ExifTool](https://exiftool.org) to read and write photo metadata, the Python wrapper [rawpy](https://pypi.org/project/rawpy) for [LibRaw](https://www.libraw.org) to read the primary image pixels of RAW photo files, and the database engine [SQLite] (https://www.sqlite.org) for intermediate data storage. Luckily, thanks to GRAPHIS' GUI, one does not need to know and understand how these separate software components operate. Finally, the [GRAPHIS Image Region vocabulary](https://vocabs.acdh.oeaw.ac.at/graphis-imgreg) provides GRAPHIS with a controlled list of concepts defined explicitly for graffiti image regions.
GRAPHIS supports the most common raster image file formats that store IPTC metadata: JPEG, TIFF, PNG, and many RAW formats. The metadata of all imported images are read and written into a local SQLite database; this database also stores each operation on the image regions. GRAPHIS can store the (newly created or altered) image regions and their annotations back into the original images at any time, but only if chosen so in the menu. Altering image regions outside of GRAPHIS while the SQLite database still holds image region metadata that are not written back into the image file will lead to errors.
		
## Creating binaries with PyInstaller
run ```pyinstaller Graphis_pyinstaller.spec``` to create an executable software package graphis_XX.

## Usage
The tool aims to add or manipulate IPTC image regions. Defined geometries within the IPTC image regions are
Circles/Rectangles/Polygons. These geometries can be created/moved/changed. Only geometries within
the image area are allowed as well polygons have to be valid to be saved. Additional extra meta information
can be stored for each image region. 

While currently only fixed meta fields of the image region can be edited, all meta information within the
image regions can be shown with the tabs on the right side called "View region info" to show the region info of the currently selected geometry
and "All region info" which shows all image regions within the current image.

Currently, all images supported by "PySide6" and "rawpy" can be imported. For importing and saving metadata 
"exiftool (https://exiftool.org/)" is used.

Right-Click:    Create new image region. Polygon is finished by a left click.
                Moving geometries. Change geometry by a right click on the nearest vertices or the circle border

Changes are submitted to the project's SQLite file. Geometry creation/changes are submitted to the database immediately,
while metadata changes on the right have to be submitted by the save button
To update the image metadata use the menu on top "save image regions to file"


![ ](doc/images/main_window.jpg)
