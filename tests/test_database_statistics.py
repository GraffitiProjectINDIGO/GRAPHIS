import json
import unittest

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QToolButton, QWidget

from graphis.app.popups.database_statistics_popup import DatabaseStatisticsPopup
from graphis.interface.imgregion_adapter import boundary_from_pixel_coordinates
from graphis.main import MainWindow


class StatisticsHarness:
    _empty_image_region_summary = MainWindow._empty_image_region_summary
    _image_region_summary_from_rows = MainWindow._image_region_summary_from_rows
    _validation_findings = MainWindow._validation_findings
    _apply_preview_summary_totals = MainWindow._apply_preview_summary_totals


class DatabaseStatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.parent = QWidget()
        self.parent.resize(800, 800)
        self.anchor = QToolButton(self.parent)
        self.popup = DatabaseStatisticsPopup(self.parent, self.anchor)
        self.harness = StatisticsHarness()
        self.harness.database_statistics_popup = self.popup

    def tearDown(self):
        self.parent.close()

    def test_multi_regions_are_counted_once_without_increasing_single_counts(self):
        ring1 = [[10, 10], [30, 10], [30, 30], [10, 10]]
        ring2 = [[60, 10], [80, 10], [80, 30], [60, 10]]
        shapes = (
            ("multipoint", [[10, 10], [60, 20]]),
            ("multilinestring", [[[10, 10], [30, 30]], [[60, 10], [80, 30]]]),
            ("multipolygon", [[ring1], [ring2]]),
        )
        rows = [
            {"object_type": shape, "data": json.dumps({"regionBoundary": boundary_from_pixel_coordinates(shape, coords)})}
            for shape, coords in shapes
        ]
        summary = self.harness._image_region_summary_from_rows(rows, [])
        for shape in ("point", "linestring", "polygon"):
            self.assertEqual(summary[shape], 0)
            self.assertEqual(summary[f"multi{shape}"], 1)
        self.harness._apply_preview_summary_totals({1: summary})
        for shape in ("point", "linestring", "polygon"):
            self.assertEqual(self.popup.count_labels[shape].text(), "0")
            self.assertEqual(self.popup.count_labels[f"multi{shape}"].text(), "1")
        single = {"object_type": "point", "data": json.dumps({
            "regionBoundary": boundary_from_pixel_coordinates("point", [10, 10])
        })}
        summary2 = self.harness._image_region_summary_from_rows([single], [])
        self.harness._apply_preview_summary_totals({1: summary, 2: summary2})
        self.assertEqual(self.popup.count_labels["point"].text(), "1")
        self.assertEqual(self.popup.count_labels["multipoint"].text(), "1")
        self.harness._apply_preview_summary_totals({})
        self.assertTrue(all(label.text() == "0" for label in self.popup.count_labels.values()))

    def test_popup_fits_rows_and_multigeometry_colours_follow_base_colours(self):
        self.parent.show()
        self.popup.show_popup()
        self.app.processEvents()
        names = sorted(self.popup.name_labels.values(), key=lambda label: label.y())
        for previous, current in zip(names[:-1], names[1:], strict=True):
            self.assertLess(previous.geometry().bottom(), current.geometry().top())
        for label in (*self.popup.name_labels.values(), *self.popup.count_labels.values()):
            self.assertTrue(self.popup.rect().contains(label.geometry()))
            self.assertGreaterEqual(label.height(), label.sizeHint().height())
        self.popup.set_color("point", QColor("cyan"))
        self.assertEqual(self.popup.name_labels["point"].styleSheet(), self.popup.name_labels["multipoint"].styleSheet())
