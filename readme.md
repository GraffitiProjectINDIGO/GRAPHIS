![ ](app/icons/INDIGO_logoGRAPHIS_text.png)
# Graphis  

## Table of contents
* [General info](#general-info)
* [Creating binaries with PyInstaller](#create_binary)


## General info
This project is a little tool written in python and QT to change and view IPTC image region tag from images. The tool should work with all images supported py pyside2 and rawpy. Once images are imported all changes made are directly and immediately stored to the project's sqlite file. Thus image IPTC information is only updated if choosen so in by the menue. All data manipulation happens solely on the sqlite while working on a project and external changes at the same time in the original IPTC region of images will not be tracked and can be lost once the iptc region is written to the images via graphis
		
## Creating binaries with PyInstaller
run ```pyinstaller Graphis_pyinstaller.spec``` to create an executable software package graphis_XX.
