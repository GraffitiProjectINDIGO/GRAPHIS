![ ](app/icons/INDIGO_logoGRAPHIS_text.png)
# Graphis  

## Table of contents
* [General info](#general-info)
* [Creating binaries with PyInstaller](#create_binary)


## General info
This project is a little tool written in Python and QT to change and view IPTC image region tags from images. The tool should work with all images supported py pyside2 and rawpy. Once images are imported, all changes made are directly and immediately stored to the project's SQLite file. Thus image IPTC information is only updated if chosen so in the menu. All data manipulation happens solely on the SQLite while working on a project and external changes at the same time in the original IPTC region of images will not be tracked and can be lost once the IPTC image region is written to the images via GRAPHIS
		
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
