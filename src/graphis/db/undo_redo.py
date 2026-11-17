# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from sqlite3 import Connection

OBJECT_COLUMNS = ("id", "image", "user", "object_type", "orig_img_region", "changed", "data")
IMAGE_COLUMNS = ("id", "deleted_orig_tag")


def _row_to_dict(row, columns):
    if row is None:
        return None
    return {column: row[column] for column in columns}


@dataclass(frozen=True)
class ObjectSnapshot:
    values: dict

    @classmethod
    def from_row(cls, row):
        values = _row_to_dict(row, OBJECT_COLUMNS)
        if values is None:
            return None
        return cls(values)

    @property
    def object_id(self):
        return self.values["id"]


@dataclass(frozen=True)
class ImageSnapshot:
    values: dict

    @classmethod
    def from_row(cls, row):
        values = _row_to_dict(row, IMAGE_COLUMNS)
        if values is None:
            return None
        return cls(values)

    @property
    def image_id(self):
        return self.values["id"]


def _insert_object(con: Connection, snapshot: ObjectSnapshot):
    con.execute(
        """
        INSERT INTO objects
            (id, image, user, object_type, orig_img_region, changed, data)
        VALUES
            (:id, :image, :user, :object_type, :orig_img_region, :changed, :data)
        """,
        snapshot.values,
    )


def _update_object(con: Connection, snapshot: ObjectSnapshot):
    con.execute(
        """
        UPDATE objects
        SET image = :image,
            user = :user,
            object_type = :object_type,
            orig_img_region = :orig_img_region,
            changed = :changed,
            data = :data
        WHERE id = :id
        """,
        snapshot.values,
    )


def _delete_object(con: Connection, object_id: int):
    con.execute("DELETE FROM objects WHERE id = :id", {"id": object_id})


def _restore_image(con: Connection, snapshot: ImageSnapshot | None):
    if snapshot is None:
        return
    con.execute(
        """
        UPDATE images
        SET deleted_orig_tag = :deleted_orig_tag
        WHERE id = :id
        """,
        snapshot.values,
    )


@dataclass
class UndoCommand:
    label: str

    def undo(self, con: Connection):
        raise NotImplementedError

    def redo(self, con: Connection):
        raise NotImplementedError

    def image_ids(self):
        return set()

    def is_noop(self):
        return False


@dataclass
class ObjectInsertCommand(UndoCommand):
    snapshot: ObjectSnapshot

    def undo(self, con: Connection):
        _delete_object(con, self.snapshot.object_id)

    def redo(self, con: Connection):
        _insert_object(con, self.snapshot)

    def image_ids(self):
        return {self.snapshot.values["image"]}


@dataclass
class ObjectUpdateCommand(UndoCommand):
    before: ObjectSnapshot | None
    after: ObjectSnapshot | None

    def undo(self, con: Connection):
        if self.before is not None:
            _update_object(con, self.before)

    def redo(self, con: Connection):
        if self.after is not None:
            _update_object(con, self.after)

    def image_ids(self):
        image_ids = set()
        if self.before is not None:
            image_ids.add(self.before.values["image"])
        if self.after is not None:
            image_ids.add(self.after.values["image"])
        return image_ids

    def is_noop(self):
        return self.before == self.after or self.before is None or self.after is None


@dataclass
class ObjectDeleteCommand(UndoCommand):
    snapshot: ObjectSnapshot
    image_before: ImageSnapshot | None = None
    image_after: ImageSnapshot | None = None

    def undo(self, con: Connection):
        _insert_object(con, self.snapshot)
        _restore_image(con, self.image_before)

    def redo(self, con: Connection):
        _delete_object(con, self.snapshot.object_id)
        _restore_image(con, self.image_after)

    def image_ids(self):
        return {self.snapshot.values["image"]}


@dataclass
class CompositeCommand(UndoCommand):
    commands: list[UndoCommand] = field(default_factory=list)

    def add(self, command: UndoCommand):
        if not command.is_noop():
            self.commands.append(command)

    def undo(self, con: Connection):
        for command in reversed(self.commands):
            command.undo(con)

    def redo(self, con: Connection):
        for command in self.commands:
            command.redo(con)

    def image_ids(self):
        image_ids = set()
        for command in self.commands:
            image_ids.update(command.image_ids())
        return image_ids

    def is_noop(self):
        return not self.commands


class UndoRedoManager:
    def __init__(self):
        self._undo_stack: list[UndoCommand] = []
        self._redo_stack: list[UndoCommand] = []
        self._groups: list[CompositeCommand] = []
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, listener: Callable[[], None]):
        self._listeners.append(listener)

    def clear_listeners(self):
        self._listeners.clear()

    def _notify(self):
        for listener in self._listeners:
            listener()

    def notify_changed(self):
        self._notify()

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._groups.clear()
        self._notify()

    def forget_image(self, image_id: int):
        self._undo_stack = [command for command in self._undo_stack if image_id not in command.image_ids()]
        self._redo_stack = [command for command in self._redo_stack if image_id not in command.image_ids()]
        self._notify()

    def can_undo(self, image_id: int | None = None):
        return self._find_stack_index(self._undo_stack, image_id) is not None

    def can_redo(self, image_id: int | None = None):
        return self._find_stack_index(self._redo_stack, image_id) is not None

    def undo_label(self, image_id: int | None = None):
        command = self._find_stack_command(self._undo_stack, image_id)
        if command is None:
            return ""
        return command.label

    def redo_label(self, image_id: int | None = None):
        command = self._find_stack_command(self._redo_stack, image_id)
        return command.label if command is not None else ""

    def record(self, command: UndoCommand):
        if command.is_noop():
            return
        if self._groups:
            self._groups[-1].add(command)
            return
        self._record_completed(command)

    def begin_group(self, label: str):
        self._groups.append(CompositeCommand(label=label))

    def end_group(self):
        if not self._groups:
            return

        command = self._groups.pop()
        if command.is_noop():
            return
        if self._groups:
            self._groups[-1].add(command)
        else:
            self._record_completed(command)

    @contextmanager
    def group(self, label: str):
        self.begin_group(label)
        try:
            yield
        finally:
            self.end_group()

    def _record_completed(self, command: UndoCommand):
        self._undo_stack.append(command)
        command_image_ids = command.image_ids()
        if command_image_ids:
            self._redo_stack = [
                redo_command
                for redo_command in self._redo_stack
                if redo_command.image_ids().isdisjoint(command_image_ids)
            ]
        else:
            self._redo_stack.clear()
        self._notify()

    def _find_stack_index(self, stack: list[UndoCommand], image_id: int | None = None):
        if image_id is None:
            return len(stack) - 1 if stack else None

        for index in range(len(stack) - 1, -1, -1):
            if image_id in stack[index].image_ids():
                return index
        return None

    def _find_stack_command(self, stack: list[UndoCommand], image_id: int | None = None):
        index = self._find_stack_index(stack, image_id)
        if index is None:
            return None
        return stack[index]

    def undo(self, con: Connection, image_id: int | None = None):
        command_index = self._find_stack_index(self._undo_stack, image_id)
        if command_index is None:
            return ""
        command = self._undo_stack.pop(command_index)
        command.undo(con)
        con.commit()
        self._redo_stack.append(command)
        self._notify()
        return command.label

    def redo(self, con: Connection, image_id: int | None = None):
        command_index = self._find_stack_index(self._redo_stack, image_id)
        if command_index is None:
            return ""
        command = self._redo_stack.pop(command_index)
        command.redo(con)
        con.commit()
        self._undo_stack.append(command)
        self._notify()
        return command.label
