#!/usr/bin/env python3
"""
Логика экрана прогресса обработки
"""
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QTimer, Signal, QObject, Qt
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox, QHeaderView
from PySide6.QtGui import QDesktopServices, QColor
import logging

logger = logging.getLogger(__name__)


class ProgressScreenLogic(QObject):
    """
    Управляет отображением прогресса обработки задач в таблице.

    Отвечает за добавление/обновление задач, управление кнопками паузы/возобновления/отмены,
    отображение прогресс-баров и общую статистику выполнения.
    """

    # Сигналы для связи с обработчиком
    pause_selected_requested = Signal(list)
    resume_selected_requested = Signal(list)
    cancel_selected_requested = Signal(list)
    clear_finished_requested = Signal()

    def __init__(self, ui, parent, processing_manager):
        """
        Инициализирует логику экрана прогресса.

        Args:
            ui: Объект UI главного окна
            parent: Родительский объект Qt
            processing_manager: Менеджер обработки задач
        """
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.processing_manager = processing_manager

        self.tasks: dict = {}  # task_id -> {task, row, status, progress}
        self.task_rows: dict = {}  # task_id -> row index
        self.paused_tasks: set = set()
        self.cancelled_tasks: set = set()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress_display)
        self.update_timer.start(1000)

        self.connect_signals()
        self.setup_table_columns()

        self.task_start_times: dict = {}

        self._removed_tasks: set = set()

    def setup_table_columns(self):
        """Настройка колонок таблицы задач."""
        header = self.ui.taskTable.horizontalHeader()
        header.setStretchLastSection(False)

        # 5 колонок: Имя файла, Выходной файл, Прогресс, Длительность, Статус
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)

        header.setMinimumSectionSize(80)
        self.ui.taskTable.setColumnWidth(0, 300)
        self.ui.taskTable.setColumnWidth(1, 250)
        self.ui.taskTable.setColumnWidth(2, 120)
        self.ui.taskTable.setColumnWidth(3, 100)
        self.ui.taskTable.setColumnWidth(4, 120)

        self.ui.taskTable.setAlternatingRowColors(True)
        header.setSectionsMovable(False)

    def connect_signals(self):
        """Подключает сигналы кнопок управления."""
        self.ui.pauseSelectedBtn.clicked.connect(self.on_pause_selected)
        self.ui.resumeSelectedBtn.clicked.connect(self.on_resume_selected)
        self.ui.cancelSelectedBtn.clicked.connect(self.on_cancel_selected)
        self.ui.clearFinishedBtn.clicked.connect(self.on_clear_finished)
        self.ui.openLogBtn.clicked.connect(self.on_open_log)

        self.ui.pauseTasksBtn.hide()

        self.ui.taskTable.itemSelectionChanged.connect(self.on_selection_changed)
        self.ui.taskTable.itemDoubleClicked.connect(self.on_task_double_clicked)

    def add_task(self, task_id: str, input_path: str, output_path: str):
        """
        Добавляет задачу в таблицу.

        Args:
            task_id: Уникальный идентификатор задачи
            input_path: Путь к входному файлу
            output_path: Путь к выходному файлу
        """
        if task_id in self.tasks:
            return

        if task_id in self._removed_tasks:
            self._removed_tasks.remove(task_id)

        row = self.ui.taskTable.rowCount()
        self.ui.taskTable.insertRow(row)
        self.task_rows[task_id] = row

        input_name = Path(input_path).name
        output_name = Path(output_path).name

        name_item = QTableWidgetItem(input_name)
        name_item.setData(Qt.UserRole, input_path)
        name_item.setToolTip(f"Путь: {input_path}\nВыход: {output_path}")
        self.ui.taskTable.setItem(row, 0, name_item)

        output_item = QTableWidgetItem(output_name)
        output_item.setToolTip(f"Выходной файл: {output_path}")
        self.ui.taskTable.setItem(row, 1, output_item)

        progress_item = QTableWidgetItem("0/0")
        progress_item.setTextAlignment(Qt.AlignCenter)
        self.ui.taskTable.setItem(row, 2, progress_item)

        duration_item = QTableWidgetItem("--:--")
        duration_item.setTextAlignment(Qt.AlignCenter)
        self.ui.taskTable.setItem(row, 3, duration_item)

        status_item = QTableWidgetItem("pending")
        status_item.setTextAlignment(Qt.AlignCenter)
        self._set_status_color(status_item, "pending")
        self.ui.taskTable.setItem(row, 4, status_item)

        self.tasks[task_id] = {
            'task_id': task_id,
            'input_path': input_path,
            'output_path': output_path,
            'row': row,
            'status': 'pending',
            'progress': 0,
            'current': 0,
            'total': 0,
            'duration': 0
        }

        self.ui.taskTable.resizeRowsToContents()
        logger.debug(f"Задача добавлена в таблицу: {input_name} (ID: {task_id})")

    def update_task_status(self, task_id: str, status: str):
        """
        Обновляет статус задачи в таблице.

        Args:
            task_id: Идентификатор задачи
            status: Новый статус (pending, processing, completed, failed, cancelled, paused)
        """
        if task_id in self._removed_tasks:
            logger.debug(f"Пропускаем обновление статуса для удаленной задачи {task_id}")
            return

        if task_id not in self.tasks:
            logger.warning(f"UI: задача {task_id} не найдена в tasks при обновлении статуса")
            return

        task_data = self.tasks[task_id]
        task_data['status'] = status

        row = task_data['row']
        status_item = self.ui.taskTable.item(row, 4)
        if status_item:
            status_item.setText(status)
            self._set_status_color(status_item, status)
            logger.debug(f"UI: статус задачи {task_id} обновлён на '{status}', цвет установлен")

        if status == 'processing' and task_id not in self.task_start_times:
            self.task_start_times[task_id] = datetime.now()

        if status in ['completed', 'failed', 'cancelled']:
            self.task_start_times.pop(task_id, None)

        self.on_selection_changed()
        self.update_progress_display()

        logger.info(f"Статус задачи {task_id} обновлён: {status}")

    def update_task_progress(self, task_id: str, current: int, total: int):
        """
        Обновляет прогресс задачи с отображением прогресс-бара.

        Args:
            task_id: Идентификатор задачи
            current: Количество обработанных сегментов
            total: Общее количество сегментов
        """
        if task_id in self._removed_tasks:
            logger.debug(f"Пропускаем обновление прогресса для удаленной задачи {task_id}")
            return

        if task_id not in self.tasks:
            logger.warning(f"UI: задача {task_id} не найдена в tasks при обновлении прогресса")
            return

        task_data = self.tasks[task_id]
        task_data['current'] = current
        task_data['total'] = total

        if total > 0:
            progress = (current / total) * 100
            task_data['progress'] = progress

            row = task_data['row']

            from PySide6.QtWidgets import QProgressBar, QWidget, QHBoxLayout, QLabel
            from PySide6.QtCore import Qt

            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)

            progress_bar = QProgressBar()
            progress_bar.setRange(0, total)
            progress_bar.setValue(current)
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(20)

            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    background-color: #f1f5f9;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #3b82f6;
                    border-radius: 3px;
                }
            """)

            label = QLabel(f"{current}/{total}")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumWidth(60)
            label.setStyleSheet("""
                QLabel {
                    color: #1f2d3d;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)

            layout.addWidget(progress_bar, 1)
            layout.addWidget(label, 0)

            self.ui.taskTable.setCellWidget(row, 2, container)

            name_item = self.ui.taskTable.item(row, 0)
            if name_item:
                name_item.setToolTip(f"Прогресс: {current}/{total} сегментов ({progress:.1f}%)")

            self.update_progress_display()

    def update_task_duration(self, task_id: str, duration: float, formatted_duration: str):
        """
        Обновляет отображение длительности видео.

        Args:
            task_id: Идентификатор задачи
            duration: Длительность в секундах
            formatted_duration: Отформатированная строка длительности
        """
        if task_id in self._removed_tasks:
            logger.debug(f"Пропускаем обновление длительности для удаленной задачи {task_id}")
            return

        if task_id not in self.tasks:
            logger.warning(f"UI: задача {task_id} не найдена в tasks при обновлении длительности")
            return

        task_data = self.tasks[task_id]
        task_data['duration'] = duration

        row = task_data['row']
        duration_item = self.ui.taskTable.item(row, 3)
        if duration_item:
            duration_item.setText(formatted_duration)

    def _format_duration(self, seconds: float) -> str:
        """
        Форматирует секунды в MM:SS или HH:MM:SS.

        Args:
            seconds: Количество секунд

        Returns:
            Отформатированная строка длительности
        """
        if seconds <= 0:
            return "--:--"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _set_status_color(self, item, status: str):
        """
        Устанавливает цвет текста в зависимости от статуса.

        Args:
            item: Элемент таблицы QTableWidgetItem
            status: Статус задачи
        """
        if status == 'completed':
            item.setForeground(QColor(0, 150, 0))
        elif status == 'failed':
            item.setForeground(QColor(200, 0, 0))
        elif status == 'cancelled':
            item.setForeground(QColor(150, 150, 150))
        elif status == 'processing':
            item.setForeground(QColor(0, 0, 200))
        elif status == 'paused':
            item.setForeground(QColor(255, 140, 0))
        elif status == 'pending':
            item.setForeground(QColor(100, 100, 100))
        else:
            item.setForeground(QColor(0, 0, 0))
            logger.warning(f"Неизвестный статус: {status}")

    def update_progress_display(self):
        """Обновляет общую статистику прогресса (прогресс-бары, время, количество задач)."""
        if not self.tasks:
            self.ui.filesProgress.setValue(0)
            self.ui.totalSegmentsProgress.setValue(0)
            self.ui.timeRemainingValueLabel.setText("--")
            return

        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for t in self.tasks.values() if t['status'] == 'completed')
        failed_tasks = sum(1 for t in self.tasks.values() if t['status'] == 'failed')
        cancelled_tasks = sum(1 for t in self.tasks.values() if t['status'] == 'cancelled')
        paused_tasks = sum(1 for t in self.tasks.values() if t['status'] == 'paused')
        processing_tasks = sum(1 for t in self.tasks.values() if t['status'] == 'processing')

        active_tasks = total_tasks - cancelled_tasks

        if active_tasks > 0:
            files_progress = ((completed_tasks + failed_tasks) / active_tasks) * 100
        else:
            files_progress = 0

        self.ui.filesProgress.setValue(int(files_progress))

        total_segments = 0
        processed_segments = 0

        for task_data in self.tasks.values():
            if task_data['status'] not in ['cancelled']:
                total_segments += task_data['total']
                processed_segments += task_data['current']

        if total_segments > 0:
            segments_progress = (processed_segments / total_segments) * 100
        else:
            segments_progress = 0

        self.ui.totalSegmentsProgress.setValue(int(segments_progress))

        self.ui.filesProgressLabel.setText(
            f"Прогресс по файлам: {completed_tasks + failed_tasks}/{active_tasks} "
            f"(обработано: {completed_tasks}, ошибок: {failed_tasks}, "
            f"приостановлено: {paused_tasks}, отменено: {cancelled_tasks})"
        )

        self.ui.totalSegmentsLabel.setText(
            f"Прогресс по сегментам: {processed_segments}/{total_segments} сегментов"
        )

        remaining_time = self._estimate_remaining_time()
        self.ui.timeRemainingValueLabel.setText(remaining_time)

        stats = f"Активных задач: {processing_tasks}, Приостановлено: {paused_tasks}, "
        stats += f"Очередь: {active_tasks - processing_tasks - paused_tasks}"
        self.ui.statsValueLabel.setText(stats)

    def _estimate_remaining_time(self) -> str:
        """
        Оценивает оставшееся время обработки на основе текущих задач.

        Returns:
            Строка с оценкой времени (сек/мин/ч)
        """
        processing_tasks = []

        for task_id, task_data in self.tasks.items():
            if task_data['status'] == 'processing':
                start_time = self.task_start_times.get(task_id)
                if start_time and task_data['current'] > 0 and task_data['total'] > 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    progress = task_data['current'] / task_data['total']
                    if progress > 0:
                        total_estimated = elapsed / progress
                        remaining = total_estimated - elapsed
                        if remaining > 0:
                            processing_tasks.append(remaining)

        if not processing_tasks:
            return "вычисляется..."

        max_remaining = max(processing_tasks)

        if max_remaining < 60:
            return f"{int(max_remaining)} сек"
        elif max_remaining < 3600:
            return f"{int(max_remaining / 60)} мин"
        else:
            hours = int(max_remaining / 3600)
            minutes = int((max_remaining % 3600) / 60)
            return f"{hours} ч {minutes} мин"

    def on_selection_changed(self):
        """Обновляет состояние кнопок в зависимости от выделенных задач."""
        selected_rows = set()
        for item in self.ui.taskTable.selectedItems():
            selected_rows.add(item.row())

        selected_task_ids = []
        for task_id, task_data in self.tasks.items():
            if task_data['row'] in selected_rows:
                selected_task_ids.append(task_id)

        has_pausable = any(
            self.tasks[tid]['status'] in ['pending', 'processing']
            for tid in selected_task_ids
        )
        has_resumable = any(
            self.tasks[tid]['status'] == 'paused'
            for tid in selected_task_ids
        )
        has_cancellable = any(
            self.tasks[tid]['status'] in ['pending', 'processing', 'paused']
            for tid in selected_task_ids
        )

        self.ui.pauseSelectedBtn.setEnabled(has_pausable)
        self.ui.resumeSelectedBtn.setEnabled(has_resumable)
        self.ui.cancelSelectedBtn.setEnabled(has_cancellable)

    def on_pause_selected(self):
        """Обрабатывает приостановку выбранных задач."""
        selected_rows = set()
        for item in self.ui.taskTable.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(
                self.ui.centralwidget,
                "Нет выбора",
                "Выберите задачи для приостановки в таблице"
            )
            return

        task_ids_to_pause = []
        task_names = []

        for task_id, task_data in self.tasks.items():
            if task_data['row'] in selected_rows:
                status = task_data['status']
                if status in ['pending', 'processing']:
                    task_ids_to_pause.append(task_id)
                    task_names.append(Path(task_data['input_path']).name)

        if task_ids_to_pause:
            task_list = "\n".join(task_names[:5])
            if len(task_names) > 5:
                task_list += f"\n... и ещё {len(task_names) - 5}"

            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Подтверждение",
                f"Приостановить следующие задачи?\n\n{task_list}\n\n"
                f"Приостановленные задачи будут пропущены, и обработка перейдёт к следующим по приоритету.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.pause_selected_requested.emit(task_ids_to_pause)
                logger.info(f"Запрошена приостановка задач: {task_ids_to_pause}")

    def on_resume_selected(self):
        """Обрабатывает возобновление выбранных задач."""
        selected_rows = set()
        for item in self.ui.taskTable.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(
                self.ui.centralwidget,
                "Нет выбора",
                "Выберите задачи для возобновления в таблице"
            )
            return

        task_ids_to_resume = []
        task_names = []

        for task_id, task_data in self.tasks.items():
            if task_data['row'] in selected_rows:
                status = task_data['status']
                if status == 'paused':
                    task_ids_to_resume.append(task_id)
                    task_names.append(Path(task_data['input_path']).name)

        if task_ids_to_resume:
            task_list = "\n".join(task_names[:5])
            if len(task_names) > 5:
                task_list += f"\n... и ещё {len(task_names) - 5}"

            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Подтверждение",
                f"Возобновить следующие задачи?\n\n{task_list}",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.resume_selected_requested.emit(task_ids_to_resume)
                logger.info(f"Запрошено возобновление задач: {task_ids_to_resume}")

    def on_cancel_selected(self):
        """Обрабатывает отмену выбранных задач."""
        selected_rows = set()
        for item in self.ui.taskTable.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(
                self.ui.centralwidget,
                "Нет выбора",
                "Выберите задачи для отмены в таблице"
            )
            return

        task_ids_to_cancel = []
        task_names = []

        for task_id, task_data in self.tasks.items():
            if task_data['row'] in selected_rows:
                status = task_data['status']
                if status in ['pending', 'processing', 'paused']:
                    task_ids_to_cancel.append(task_id)
                    task_names.append(Path(task_data['input_path']).name)

        if task_ids_to_cancel:
            task_list = "\n".join(task_names[:5])
            if len(task_names) > 5:
                task_list += f"\n... и ещё {len(task_names) - 5}"

            reply = QMessageBox.question(
                self.ui.centralwidget,
                "Подтверждение",
                f"Отменить следующие задачи?\n\n{task_list}\n\n"
                f"Отменённые задачи нельзя будет возобновить или обработать повторно.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.cancel_selected_requested.emit(task_ids_to_cancel)
                logger.info(f"Запрошена отмена задач: {task_ids_to_cancel}")

    def on_clear_finished(self):
        """Очищает завершённые, ошибочные и отменённые задачи из UI и менеджера."""
        finished_tasks = []
        failed_tasks = []
        cancelled_tasks = []

        for task_id, task_data in self.tasks.items():
            status = task_data['status']
            if status == 'completed':
                finished_tasks.append(task_id)
            elif status == 'failed':
                failed_tasks.append(task_id)
            elif status == 'cancelled':
                cancelled_tasks.append(task_id)

        total_to_clear = len(finished_tasks) + len(failed_tasks) + len(cancelled_tasks)

        if total_to_clear == 0:
            QMessageBox.information(
                self.ui.centralwidget,
                "Нет задач",
                "Нет завершённых, ошибочных или отменённых задач для очистки"
            )
            return

        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Подтверждение",
            f"Очистить из таблицы:\n"
            f"• Завершённых задач: {len(finished_tasks)}\n"
            f"• Ошибочных задач: {len(failed_tasks)}\n"
            f"• Отменённых задач: {len(cancelled_tasks)}\n\n"
            f"Всего: {total_to_clear}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            all_to_clear = finished_tasks + failed_tasks + cancelled_tasks
            self.clear_finished_requested.emit()
            self._remove_tasks_from_ui(all_to_clear)

            logger.info(f"Очищено задач: завершённых={len(finished_tasks)}, "
                       f"ошибочных={len(failed_tasks)}, отменённых={len(cancelled_tasks)}")

    def _remove_tasks_from_ui(self, task_ids_to_remove: list):
        """
        Удаляет задачи из UI таблицы.

        Args:
            task_ids_to_remove: Список ID задач для удаления
        """
        for task_id in task_ids_to_remove:
            self._removed_tasks.add(task_id)

        rows_to_remove = []
        for task_id in task_ids_to_remove:
            if task_id in self.tasks:
                rows_to_remove.append((task_id, self.tasks[task_id]['row']))

        for task_id, row in sorted(rows_to_remove, key=lambda x: x[1], reverse=True):
            self.ui.taskTable.removeRow(row)
            del self.tasks[task_id]
            if task_id in self.task_rows:
                del self.task_rows[task_id]

        if rows_to_remove:
            self.task_rows.clear()
            for idx, (task_id, task_data) in enumerate(self.tasks.items()):
                task_data['row'] = idx
                self.task_rows[task_id] = idx

    def on_task_double_clicked(self, item):
        """
        Обрабатывает двойной клик по задаче (открывает папку с выходным файлом).

        Args:
            item: Элемент таблицы, по которому был клик
        """
        row = item.row()
        for task_id, task_data in self.tasks.items():
            if task_data['row'] == row:
                if task_data['status'] == 'completed':
                    output_path = task_data['output_path']
                    QDesktopServices.openUrl(Path(output_path).parent.as_posix())
                    logger.debug(f"Открыта папка: {Path(output_path).parent}")
                break

    def on_open_log(self):
        """Открывает папку с логами или файл лога в стандартном приложении."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = Path("speecheq_debug.log")

        try:
            import platform
            import subprocess

            system = platform.system()

            if log_file.exists():
                if system == "Windows":
                    import os
                    os.startfile(str(log_file.absolute()))
                elif system == "Darwin":
                    subprocess.run(["open", str(log_file.absolute())], check=False)
                else:
                    subprocess.run(["xdg-open", str(log_file.absolute())], check=False)
            else:
                if system == "Windows":
                    import os
                    os.startfile(str(log_dir.absolute()))
                elif system == "Darwin":
                    subprocess.run(["open", str(log_dir.absolute())], check=False)
                else:
                    subprocess.run(["xdg-open", str(log_dir.absolute())], check=False)

        except Exception as e:
            logger.error(f"Не удалось открыть лог-файл: {e}")
            QMessageBox.information(
                self.ui.centralwidget,
                "Лог-файл",
                f"Лог-файл находится по пути:\n{log_file.absolute()}\n\n"
                f"Вы можете открыть его в любом текстовом редакторе."
            )

    def show_error(self, error_msg: str):
        """
        Отображает сообщение об ошибке.

        Args:
            error_msg: Текст сообщения об ошибке
        """
        self.ui.errorNotificationLabel.setText(f"Ошибка: {error_msg}")
        QMessageBox.warning(self.ui.centralwidget, "Ошибка обработки", error_msg)

    def clear_error(self):
        """Очищает отображение сообщения об ошибке."""
        self.ui.errorNotificationLabel.setText("")