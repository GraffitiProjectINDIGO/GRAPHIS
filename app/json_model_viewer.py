from __future__ import annotations
from typing import Any, List, Dict, Union
from PySide6.QtCore import QAbstractItemModel, QModelIndex, QObject, Qt


class TreeItem:
    """Each tree item will be one line"""

    def __init__(self, parent: TreeItem = None):
        self._parent = parent
        self._key = ""
        self._value = ""
        self._value_type = None
        self._children = []

    def append_child(self, item: TreeItem):
        self._children.append(item)

    def child(self, row: int) -> TreeItem:
        return self._children[row]

    def parent(self) -> TreeItem:
        return self._parent

    def child_count(self) -> int:
        return len(self._children)

    def row(self) -> int:
        return self._parent._children.index(self) if self._parent else 0

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, key: str):
        self._key = key

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str):
        self._value = value

    @property
    def value_type(self):
        return self._value_type

    @value_type.setter
    def value_type(self, value):
        """Set the python type of the item's value."""
        self._value_type = value

    @classmethod
    def load(cls, value: Union[List, Dict], parent: TreeItem = None, sort=True) -> TreeItem:
        root_item = TreeItem(parent)
        root_item.key = "root"

        if isinstance(value, dict):
            items = sorted(value.items()) if sort else value.items()

            for key, value in items:
                child = cls.load(value, root_item)
                child.key = key
                child.value_type = type(value)
                root_item.append_child(child)

        elif isinstance(value, list):
            for index, value in enumerate(value):
                child = cls.load(value, root_item)
                child.key = value['Name']
                child.value = value['License']
                child.value_type = type(value)
                root_item.append_child(child)

        else:
            root_item.value = value
            root_item.value_type = type(value)

        return root_item


class JsonModel(QAbstractItemModel):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self._rootItem = TreeItem()
        self._headers = ("key", "value")

    def clear(self):
        self.load({})

    def load(self, document: dict | list[dict]):

        self.beginResetModel()

        self._rootItem = TreeItem.load(document)
        self._rootItem.value_type = type(document)

        self.endResetModel()

        return True

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> Any:

        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return item.key

            if index.column() == 1:
                return item.value

        elif role == Qt.EditRole:
            if index.column() == 1:
                return item.value

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole):
        if role == Qt.EditRole:
            if index.column() == 1:
                item = index.internalPointer()
                item.value = str(value)

                self.dataChanged.emit(index, index)

                return True

        return False

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self._headers[section]

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self._rootItem
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:

        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item == self._rootItem:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self._rootItem
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()

    def columnCount(self, parent=QModelIndex()):
        return 2

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super(JsonModel, self).flags(index)

        if index.column() == 1:
            return Qt.ItemIsEditable | flags
        else:
            return flags

    def to_json(self, item=None):

        if item is None:
            item = self._rootItem

        nr_child = item.child_count()

        if item.value_type is dict:
            document = {}
            for i in range(nr_child):
                ch = item.child(i)
                document[ch.key] = self.to_json(ch)
            return document

        elif item.value_type == list:
            document = []
            for i in range(nr_child):
                ch = item.child(i)
                document.append(self.to_json(ch))
            return document

        else:
            return item.value
