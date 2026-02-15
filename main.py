from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QFileDialog,
                             QPushButton, QListWidget, QTableWidget,
                             QApplication, QTableWidgetItem)
from PyQt6.QtCore import QPoint, Qt
import sqlite3
from PyQt6 import uic
from PyQt6.QtGui import QIcon, QPainter, QColor, QPen, QPixmap
from datetime import datetime
import sys
import os
import csv
from typing import List


DEVELOPER = True

def get_db(db, col, other='', value='') -> list:
    with sqlite3.connect('data/data.db') as conn:
        cursor = conn.cursor()
        if_state = f' WHERE {other} = {value}' if other and value else ''
        res = cursor.execute(f"""SELECT {col} FROM {db}{if_state}""").fetchall()
        return res

def delete_db(db, col, value):
    with sqlite3.connect('data/data.db') as conn:
        cursor = conn.cursor()
        cursor.execute(f"""DELETE FROM {db} WHERE {col} = {value}""")

def get_id(table: str) -> int:
    with sqlite3.connect('data/data.db') as con:
        try:
            cur = con.cursor()
            ids = cur.execute(f'''SELECT id FROM {table}''').fetchall()
            debug(ids)
            if len(ids) == 0:
                return 0
            else:
                debug('max:', max(ids, key=lambda x: x[0])[0] + 1)
                return max(ids, key=lambda x: x[0])[0] + 1
        except Exception as e:
            debug(e)
            return 0

def debug(*args, **kwargs) -> None:
    if DEVELOPER:
        print(*args, **kwargs)


class ShelfPackingAlgorithm:
    def __init__(self):
        self.shelves = []

    def pack_objects(self, objects: List, container_width: int) -> List:
        debug(f"Алгоритм Shelf FFD: начата упаковка {len(objects)} объектов")

        sorted_objects = sorted(objects, key=lambda x: x[4], reverse=True)

        packed_objects = []
        self.shelves = []

        for obj in sorted_objects:
            obj_id, _, _, width, height, obj_type, project_id = obj

            shelf_index = self.find_shelf_for_object(width, height, container_width)

            if shelf_index is not None:
                shelf_y, shelf_height, remaining_width = self.shelves[shelf_index]
                x_pos = container_width - remaining_width
                y_pos = shelf_y

                self.shelves[shelf_index] = (shelf_y, shelf_height, remaining_width - width)
                debug(f"Размещен {obj_type} {width}x{height} на полке {shelf_index} ({x_pos}, {y_pos})")

            else:
                if not self.shelves:
                    y_pos = 0
                else:
                    y_pos = max(shelf[0] + shelf[1] for shelf in self.shelves)

                x_pos = 0
                shelf_height = height
                remaining_width = container_width - width
                self.shelves.append((y_pos, shelf_height, remaining_width))
                debug(f"Создана новая полка для {obj_type} {width}x{height} на ({x_pos}, {y_pos})")

            packed_obj = [obj_id, x_pos, y_pos, width, height, obj_type, project_id]
            packed_objects.append(packed_obj)

        total_height = max([shelf[0] + shelf[1] for shelf in self.shelves]) if self.shelves else 0
        total_area = container_width * total_height
        used_area = sum(obj[3] * obj[4] for obj in packed_objects)
        utilization = (used_area / total_area * 100) if total_area > 0 else 0

        debug(f"Алгоритм Shelf FFD: упаковано {len(packed_objects)} объектов")
        debug(f"Использование площади: {utilization:.1f}% ({used_area}/{total_area})")
        debug(f"Количество полок: {len(self.shelves)}, общая высота: {total_height}")

        return packed_objects

    def find_shelf_for_object(self, width: int, height: int, container_width: int) -> int:
        for i, (shelf_y, shelf_height, remaining_width) in enumerate(self.shelves):
            if width <= remaining_width and height <= shelf_height:
                return i
        return None


class AdvancedPackingAlgorithm:
    def __init__(self):
        self.shelves = []

    def pack_objects(self, objects: List, container_width: int, container_height: int = None) -> List:
        rectangles = [obj for obj in objects if obj[5] == 'rec']
        circles = [obj for obj in objects if obj[5] == 'cir']
        triangles = [obj for obj in objects if obj[5] == 'tri']

        rectangles.sort(key=lambda x: (x[4], x[3]), reverse=True)
        circles.sort(key=lambda x: x[3], reverse=True)
        triangles.sort(key=lambda x: x[4], reverse=True)

        packed_objects = []
        current_y = 0

        for rect in rectangles:
            obj_id, _, _, width, height, obj_type, project_id = rect

            placed = False
            for i, (shelf_y, shelf_height, remaining_width) in enumerate(self.shelves):
                if width <= remaining_width and height <= shelf_height:
                    x_pos = container_width - remaining_width
                    packed_obj = [obj_id, x_pos, shelf_y, width, height, obj_type, project_id]
                    packed_objects.append(packed_obj)
                    self.shelves[i] = (shelf_y, shelf_height, remaining_width - width)
                    placed = True
                    break

            if not placed:
                if current_y + height > container_height if container_height else False:
                    continue

                packed_obj = [obj_id, 0, current_y, width, height, obj_type, project_id]
                packed_objects.append(packed_obj)
                self.shelves.append((current_y, height, container_width - width))
                current_y += height

        for circle in circles:
            obj_id, _, _, diameter, _, obj_type, project_id = circle
            size = diameter

            placed = False
            for i, (shelf_y, shelf_height, remaining_width) in enumerate(self.shelves):
                if size <= remaining_width and size <= shelf_height:
                    x_pos = container_width - remaining_width
                    packed_obj = [obj_id, x_pos, shelf_y, diameter, diameter, obj_type, project_id]
                    packed_objects.append(packed_obj)
                    self.shelves[i] = (shelf_y, shelf_height, remaining_width - size)
                    placed = True
                    break

            if not placed:
                if container_height and current_y + size > container_height:
                    continue

                packed_obj = [obj_id, 0, current_y, diameter, diameter, obj_type, project_id]
                packed_objects.append(packed_obj)
                self.shelves.append((current_y, size, container_width - size))
                current_y += size

        for triangle in triangles:
            obj_id, _, _, width, height, obj_type, project_id = triangle

            placed = False
            for i, (shelf_y, shelf_height, remaining_width) in enumerate(self.shelves):
                if width <= remaining_width and height <= shelf_height:
                    x_pos = container_width - remaining_width
                    packed_obj = [obj_id, x_pos, shelf_y, width, height, obj_type, project_id]
                    packed_objects.append(packed_obj)
                    self.shelves[i] = (shelf_y, shelf_height, remaining_width - width)
                    placed = True
                    break

            if not placed:
                if container_height and current_y + height > container_height:
                    continue

                packed_obj = [obj_id, 0, current_y, width, height, obj_type, project_id]
                packed_objects.append(packed_obj)
                self.shelves.append((current_y, height, container_width - width))
                current_y += height

        return packed_objects


class PaintSpace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.objects = []
        self.scale = 1
        self.offset_x = 50
        self.offset_y = 50
        self.setMinimumSize(800, 600)

    def set_objects(self, objects):
        debug(f"PaintSpace.set_objects: получено {len(objects)} объектов")
        self.objects = objects
        self.update()

    def paintEvent(self, event):
        debug("PaintSpace: начата отрисовка")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(255, 255, 255))

        self.draw_grid(painter)

        self.draw_container(painter)

        for obj in self.objects:
            self.draw_object(painter, obj)

        debug("PaintSpace: отрисовка завершена")

    def draw_grid(self, painter):
        painter.setPen(QPen(QColor(200, 200, 200)))
        grid_size = 50

        for x in range(0, self.width(), grid_size):
            painter.drawLine(x, 0, x, self.height())

        for y in range(0, self.height(), grid_size):
            painter.drawLine(0, y, self.width(), y)

    def draw_container(self, painter):
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QColor(0, 0, 0, 0))

        container_width = 500 * self.scale
        container_height = 300 * self.scale

        painter.drawRect(self.offset_x, self.offset_y,
                         int(container_width), int(container_height))
        painter.drawText(self.offset_x, self.offset_y - 5, "Контейнер")

    def draw_object(self, painter, obj):
        try:
            obj_id, x_pos, y_pos, width, height, obj_type, project_id = obj

            x = x_pos * self.scale + self.offset_x
            y = y_pos * self.scale + self.offset_y
            scaled_width = width * self.scale
            scaled_height = height * self.scale

            debug(f"Рисуем {obj_type} {width}x{height} -> {scaled_width:.1f}x{scaled_height:.1f}")

            if obj_type == 'rec':
                color = QColor(255, 0, 0, 180)
            elif obj_type == 'cir':
                color = QColor(0, 255, 0, 180)
            elif obj_type == 'tri':
                color = QColor(0, 0, 255, 180)
            else:
                color = QColor(128, 128, 128, 180)

            painter.setBrush(color)
            painter.setPen(QPen(QColor(0, 0, 0), 1))

            if obj_type == 'rec':
                painter.drawRect(int(x), int(y), int(scaled_width), int(scaled_height))
            elif obj_type == 'cir':
                painter.drawEllipse(int(x), int(y), int(scaled_width), int(scaled_height))
            elif obj_type == 'tri':
                points = [
                    QPoint(int(x + scaled_width / 2), int(y)),
                    QPoint(int(x), int(y + scaled_height)),
                    QPoint(int(x + scaled_width), int(y + scaled_height))
                ]
                painter.drawPolygon(points)

            label = f"{obj_type}"
            painter.drawText(int(x), int(y) - 2, label)

        except Exception as e:
            debug(f"Ошибка при отрисовке: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('ui/main.ui', self)
        self.setWindowIcon(QIcon('resources/packager.png'))
        self.newProjectButton.clicked.connect(self.create_new_project)
        self.req_add.clicked.connect(self.create_new_object)
        self.cir_add.clicked.connect(self.create_new_object)
        self.tri_add.clicked.connect(self.create_new_object)

        self.tri_x_size.textChanged.connect(self.update)
        self.tri_y_size.textChanged.connect(self.update)
        self.req_x_size.textChanged.connect(self.update)
        self.req_y_size.textChanged.connect(self.update)
        self.cir_x_size.textChanged.connect(self.update)
        self.cir_y_size.textChanged.connect(self.update)

        self.tri_count.valueChanged.connect(self.update)
        self.req_count.valueChanged.connect(self.update)
        self.cir_count.valueChanged.connect(self.update)

        self.drawBtn.clicked.connect(self.draw_objects)
        self.saveBtn.clicked.connect(self.save_objects)

        self.deleteObjectBtn.clicked.connect(self.delete_object)

        self.deleteProjectButton.clicked.connect(self.delete_project)

        self.screen = PaintSpace()
        self.setCentralWidget(self.screen)

        self.projectsTable.cellClicked.connect(self.on_project_selected)
        self.objectsTable.cellClicked.connect(self.get_selected_object_data)
        self.cur_project = get_db('projects', 'id')[0][0]
        self.cur_object = get_db('objects', 'id', 'projectId', self.cur_project)
        if self.cur_object:
            self.cur_object = self.cur_object[0][0]
        else:
            self.cur_object = -1

        self.update_project_table()
        self.update_object_table()

        self.newObjectCreation.setTabIcon(0, QIcon('req.png'))
        self.objectsWidget.setWindowTitle('Объекты' + ' - ' + self.projectsTable.item(0, 0).text())

        self.packing_algorithm = ShelfPackingAlgorithm()

        self.projectsTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.projectsTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.objectsTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.objectsTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

    def update(self):
        tri_check = self.tri_count.text() and self.tri_x_size.text() and self.tri_y_size.text()
        if tri_check:
            self.tri_add.setEnabled(True)
        else:
            self.tri_add.setEnabled(False)

        req_check = self.req_count.text() and self.req_x_size.text() and self.req_y_size.text()
        if req_check:
            self.req_add.setEnabled(True)
        else:
            self.req_add.setEnabled(False)

        cir_check = self.cir_count.text() and self.cir_x_size.text() and self.cir_y_size.text()
        if cir_check:
            self.cir_add.setEnabled(True)
        else:
            self.cir_add.setEnabled(False)

    def get_selected_project_id(self):
        current_row = self.projectsTable.currentRow()
        if current_row >= 0:
            id_item = self.projectsTable.item(current_row, 2)
            if id_item and id_item.text().isdigit():
                return int(id_item.text())
        return None

    def get_selected_object_data(self):
        try:
            current_row = self.objectsTable.currentRow()
            if current_row >= 0:
                self.cur_object = current_row
                id_item = self.objectsTable.item(current_row, 2)
                if id_item:
                    object_id = id_item.text()
                    debug(f'Выбран объект: строка {current_row}, ID: {object_id}')
                else:
                    debug('Не удалось получить ID объекта')
            else:
                debug('Объект не выбран')
        except Exception as e:
            debug(f'Ошибка в get_selected_object_data: {e}')

    def create_new_project(self):
        self.createNewProject = CreateNewProject(self)
        self.createNewProject.show()

    def create_new_object(self):
        try:
            sender = self.sender().objectName()
            obj_to_type = {'tri_add': ['tri', self.tri_x_size.text(), self.tri_y_size.text(), self.tri_count.value()],
                           'req_add': ['rec', self.req_x_size.text(), self.req_y_size.text(), self.req_count.value()],
                           'cir_add': ['cir', self.cir_x_size.text(), self.cir_y_size.text(), self.cir_count.value()]}
            object_type = obj_to_type[sender][0]
            x_size = obj_to_type[sender][1]
            y_size = obj_to_type[sender][2]
            object_id = get_id('objects')
            project_id = self.projectsTable.item(self.cur_project, 2).text()
            with sqlite3.connect('data/data.db') as con:
                cur = con.cursor()
                cur.execute('''
                    INSERT INTO objects(id, x_pos, y_pos, x_size, y_size, type, projectId)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', (object_id, 0, 0, x_size, y_size, object_type, project_id))
                con.commit()
                if not DEVELOPER:
                    path = get_db('projects', 'path', 'id', project_id)
                    with open(path[0], 'w') as file:
                        writer = csv.writer(file)
                        writer.writerow([object_id, 0, 0, x_size, y_size, object_type, project_id])
            self.update_object_table()
        except Exception as e:
            debug('ERROR:', e)

    def on_project_selected(self):
        try:
            current_row = self.projectsTable.currentRow()
            if current_row >= 0 and self.projectsTable.item(current_row, 2):
                id_item = self.projectsTable.item(current_row, 2)
                project_id = int(id_item.text()) if id_item and id_item.text().isdigit() else None

                if project_id:
                    debug(f"Выбран проект ID: {project_id}")

                    project_name = self.projectsTable.item(current_row, 0).text()
                    self.objectsWidget.setWindowTitle('Объекты - ' + project_name)

                    objects = get_db('objects', '*', 'projectId', str(project_id))
                    debug(f"Загружено объектов: {len(objects)}")

                    self.screen.set_objects(objects)

                    self.update_object_table()

                    self.cur_project = current_row
                else:
                    debug("Не удалось получить ID проекта")
            else:
                debug("Проект не выбран")

        except Exception as e:
            debug(f"Ошибка в on_project_selected: {e}")
            import traceback
            debug(traceback.format_exc())

    def draw_objects(self):
        try:
            debug("=" * 50)
            debug("Кнопка drawBtn нажата!")

            project_id = self.get_selected_project_id()
            if not project_id:
                debug("Не выбран проект")
                return

            debug(f"Выбран проект ID: {project_id}")

            project_data = get_db('projects', 'x_size, y_size', 'id', str(project_id))
            if not project_data:
                debug("Не удалось получить данные проекта")
                return

            container_width = int(project_data[0][0])
            debug(f"Размер контейнера: {container_width}")

            objects = get_db('objects', '*', 'projectId', str(project_id))
            debug(f"Найдено объектов: {len(objects)}")

            if not objects:
                debug("В проекте нет объектов")
                return

            self.packing_algorithm = ShelfPackingAlgorithm()
            packed_objects = self.packing_algorithm.pack_objects(objects, container_width)

            debug(f"Упаковано: {len(packed_objects)} объектов")
            for obj in packed_objects:
                debug(f"  - {obj[5]} {obj[3]}x{obj[4]} на ({obj[1]}, {obj[2]})")

            self.temp_packed_objects = packed_objects

            self.screen.set_objects(packed_objects)
            debug("Объекты переданы в PaintSpace")

        except Exception as e:
            debug(f"ОШИБКА в draw_objects: {e}")
            import traceback
            debug(traceback.format_exc())

    def show_packing_stats(self, original_objects, packed_objects, container_width, container_height):
        if not packed_objects:
            return

        total_object_area = sum(obj[3] * obj[4] for obj in original_objects)

        if container_height:
            container_area = container_width * container_height
            utilization = total_object_area / container_area * 100
            debug(f"Использование площади: {utilization:.1f}%")
        else:
            max_height = max(obj[2] + obj[4] for obj in packed_objects)
            container_area = container_width * max_height
            utilization = total_object_area / container_area * 100
            debug(f"Использование площади: {utilization:.1f}% (высота: {max_height})")

        debug(f"Упаковано объектов: {len(packed_objects)}/{len(original_objects)}")

    def save_objects(self):
        if not hasattr(self, 'temp_packed_objects') or not self.temp_packed_objects:
            debug("Нет упакованных объектов для сохранения")
            return
        try:
            with sqlite3.connect('data/data.db') as conn:
                cursor = conn.cursor()
                for obj in self.temp_packed_objects:
                    cursor.execute('''
                        UPDATE objects 
                        SET x_pos = ?, y_pos = ?
                        WHERE id = ?
                    ''', (obj[1], obj[2], obj[0]))
                conn.commit()
            debug("Объекты сохранены в БД")
        except Exception as e:
            debug("Ошибка при сохранении:", e)

    def delete_object(self):
        try:
            current_row = self.objectsTable.currentRow()
            if current_row >= 0:
                id_item = self.objectsTable.item(current_row, 2)
                if id_item:
                    object_id = id_item.text()
                    debug(f'Удаление объекта ID: {object_id}')
                    delete_db('objects', 'id', object_id)
                    self.update_object_table()
                else:
                    debug('Не удалось получить ID объекта для удаления')
            else:
                debug('Не выбран объект для удаления')
        except Exception as e:
            debug(f'Ошибка при удалении объекта: {e}')

    def update_project_table(self):
        self.projectsTable.clear()
        self.projectsTable.setColumnCount(3)
        self.projectsTable.setHorizontalHeaderLabels(['Проект', 'Дата', 'Айди'])
        with sqlite3.connect('data/data.db') as con:
            cur = con.cursor()
            projects = cur.execute(f'''SELECT projectName, date, id FROM projects''').fetchall()
            debug(projects)
        self.projectsTable.setRowCount(len(projects))
        for i, row in enumerate(projects):
            for j, col in enumerate(row):
                self.projectsTable.setItem(i, j, QTableWidgetItem(str(col)))

    def update_object_table(self):
        try:
            type_to_icon = {'rec': '▭', 'cir': '○', 'tri': '△'}

            current_row = self.objectsTable.currentRow()

            self.objectsTable.setRowCount(0)

            project_id = self.get_selected_project_id()
            if not project_id:
                debug("Не выбран проект для обновления таблицы объектов")
                return

            objects = get_db('objects', '*', 'projectId', str(project_id))
            debug(f"OBJECTS для таблицы: {len(objects)} объектов")

            if self.objectsTable.columnCount() == 0:
                self.objectsTable.setColumnCount(3)
                self.objectsTable.setHorizontalHeaderLabels(['Объект', 'Размер', 'Айди'])

            self.objectsTable.setRowCount(len(objects))
            for i, row in enumerate(objects):
                self.objectsTable.setItem(i, 0, QTableWidgetItem(type_to_icon[str(row[5])]))
                self.objectsTable.setItem(i, 1, QTableWidgetItem(f"{row[3]} x {row[4]}"))
                self.objectsTable.setItem(i, 2, QTableWidgetItem(str(row[0])))

            if 0 <= current_row < len(objects):
                self.objectsTable.setCurrentCell(current_row, 0)
            elif len(objects) > 0:
                self.objectsTable.setCurrentCell(0, 0)  # Выделяем первую строку

            self.objectsTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.objectsTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        except Exception as e:
            debug(f"Ошибка в update_object_table: {e}")

    def delete_project(self):
        delete_db('projects', 'id', self.projectsTable.item(self.cur_project, 2).text())
        self.update_project_table()

    def on_object_selection_changed(self):
        selected_items = self.objectsTable.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            self.cur_object = row
            id_item = self.objectsTable.item(row, 2)
            if id_item:
                debug(f'Выбран объект ID: {id_item.text()}')


class CreateNewProject(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        uic.loadUi('ui/CreateNewProjectWindow.ui', self)
        self.createProjectButton.setEnabled(False)
        self.createProjectButton.clicked.connect(self.create_new_project)

        self.selectPathButton.clicked.connect(self.select_path)

        self.cancleProjectButton.clicked.connect(self.close)

        self.pathLabel.textChanged.connect(self.change_detected)
        self.projectNameLabel.textChanged.connect(self.change_detected)
        self.projectXSize.textChanged.connect(self.change_detected)
        self.projectYSize.textChanged.connect(self.change_detected)

    def create_new_project(self):
        path = self.pathLabel.text()
        name = self.projectNameLabel.text()
        xSize = self.projectXSize.text()
        ySize = self.projectYSize.text()
        date = str(datetime.now().date())
        debug(path, name, xSize, ySize, date)
        nid = get_id('projects')
        debug('project id:', nid)

        with sqlite3.connect('data/data.db') as con:
            try:
                cur = con.cursor()
                cur.execute('''
                    INSERT INTO projects(id, projectName, date, x_size, y_size, path)
                    VALUES (?, ?, ?, ?, ?, ?)''', (nid, name, date, xSize, ySize, path))
                con.commit()
                self.parent.update_project_table()
                if not DEVELOPER:
                    with open(path, 'w') as file:
                        writer = csv.writer(file)
                        writer.writerow(['id', 'x_pos', 'y_pos', 'x_size', 'y_size', 'type', 'projectId'])
                self.close()
            except Exception as e:
                debug(e)

    def delete_project(self):
        pass

    def select_path(self):
        self.pathLabel.setText(QFileDialog.getExistingDirectory(self, "Выбрать папку"))

    def change_detected(self):
        is_size = self.projectXSize.text().isdigit() and self.projectYSize.text().isdigit()
        is_path = os.path.isdir(self.pathLabel.text())
        is_name = self.projectNameLabel.text()

        if is_path and is_name and is_size:
            self.createProjectButton.setEnabled(True)
        else:
            self.createProjectButton.setEnabled(False)


if __name__ == '__main__':
    #debug(sum(1 for line in open("main.py", 'r') if line.strip()) / 5, '% done', sep='')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())