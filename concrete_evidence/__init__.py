"""Concrete Evidence: check every rebar before the concrete is poured.

Modules
    markers   ArUco markers: detect them, turn their size into mm per pixel, print a sheet
    frames    pick sharp, non-duplicate frames from site videos for labelling
    convert   LabelMe / COCO segmentation labels -> YOLO-seg
    capture   stillness check and detection records for the live view

Heavy libraries (torch, ultralytics) are imported only where they are used,
so the package and its tests run with numpy and OpenCV alone.
"""

__version__ = "0.1.0"
