# GRAFFIlabel  ![ ](icon.ico)

## Table of contents
* [General info](#general-info)
* [Creating binaries with PyInstaller](#create_binary)


## General info
This project is a little tool written in python and QT to change and view IPTC image region tag from images.
		
## Creating binaries with PyInstaller
run ```pyinstaller --nowindowed --icon=icon.ico --noconsole -n GRAFFIlabel_XXX graffilabel.py``` to create a package/folder GRAFFIlabel_1_3 and copy the folder "./app/bin" and "./app/icon" into a folder "app" and the files "graffilabel.config" into the distribution folder.