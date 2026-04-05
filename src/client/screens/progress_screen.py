"""
Логика экрана прогресса обработки.
"""
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QTimer, Signal, QObject, Qt
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox, QHeaderView, QProgressBar, QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QDesktopServices, QColor
import logging
from .processing_screen import ProcessingScreenLogic

logger = logging.getLogger(__name__)


class ProgressScreenLogic(QObject):
    """
    Управляет отображением прогресса обработки задач в таблице.

    Отвечает за добавление задач, обновление их статуса и прогресса,
    расчёт оставшегося времени и управление действиями пользователя
    (пауза, возобновление, отмена, очистка).
    """

    pause_selected_requested = Signal(list)
    resume_selected_requested = Signal(list)
    cancel_selected_requested = Signal(list)
    clear_finished_requested = Signal()

    STATUS_COLORS = {
        'completed': QColor(34, 197, 94),
        'failed': QColor(239, 68, 68),
        'cancelled': QColor(148, 163, 184),
        'processing': QColor(59, 130, 246),
        'paused': QColor(245, 158, 11),
        'pending': QColor(100, 116, 139),
        'resuming': QColor(100, 116, 139),
        'post_processing': QColor(6, 182, 212)
    }

    NON_CANCELLABLE_STATUSES = {'post_processing', 'failed', 'completed'}
    NON_PAUSABLE_STATUSES = {'post_processing', 'failed', 'completed', 'cancelled'}

    def __init__(self, ui, parent, processing_manager):
        """
        Инициализация логики экрана прогресса.

        :param ui: Экземпляр пользовательского интерфейса
        :param parent: Родительский виджет
        :param processing_manager: Менеджер очереди задач для управления обработкой
        """
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.processing_manager = processing_manager

        self.tasks: dict = {}
        self.task_rows: dict = {}
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress_display)
        self.update_timer.start(1000)

        self.connect_signals()
        self.setup_table_columns()

        self.task_start_times: dict = {}
        self._removed_tasks: set = set()

        self.segment_times: dict = {}
        self.avg_segment_time: float = 0.0
        self.segment_time_samples: int = 0

    def setup_table_columns(self):
        """Настройка заголовков и размеров колонок таблицы задач."""
        header = self.ui.taskTable.horizontalHeader()
        header.setStretchLastSection(False)

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
        """Подключение сигналов кнопок и таблицы к обработчикам событий."""
        self.ui.pauseSelectedBtn.clicked.connect(self.on_pause_selected)
        self.ui.resumeSelectedBtn.clicked.connect(self.on_resume_selected)
        self.ui.cancelSelectedBtn.clicked.connect(self.on_cancel_selected)
        self.ui.clearFinishedBtn.clicked.connect(self.on_clear_finished)
        self.ui.openLogBtn.clicked.connect(self.on_open_log)

        self.ui.pauseTasksBtn.hide()

        self.ui.taskTable.itemSelectionChanged.connect(self.on_selection_changed)
        self.ui.taskTable.itemDoubleClicked.connect(self.on_task_double_clicked)

    def _get_progress_bar_color(self, status: str) -> str:
        """
        Возвращает HEX-цвет для прогресс-бара в зависимости от статуса задачи.

        :param status: Статус задачи
        :return: HEX-строка цвета
        """
        color_map = {
            'processing': '#3b82f6',
            'post_processing': '#06b6d4',
            'resuming': '#64748b',
            'completed': '#22c55e',
            'failed': '#ef4444',
            'paused': '#f59e0b',
            'cancelled': '#94a3b8',
            'pending': '#64748b'
        }
        return color_map.get(status, '#3b82f6')

    def _update_progress_bar_style(self, progress_bar: QProgressBar, status: str):
        """
        Применяет стиль прогресс-бару в соответствии со статусом задачи.

        :param progress_bar: Экземпляр QProgressBar для стилизации
        :param status: Статус задачи для определения цвета
        """
        color = self._get_progress_bar_color(status)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background-color: #f1f5f9;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

    def add_task(self, task_id: str, input_path: str, output_path: str, total_segments: int = 0):
        """
        Добавление новой задачи в таблицу прогресса.

        :param task_id: Уникальный идентификатор задачи
        :param input_path: Путь к исходному файлу
        :param output_path: Путь для сохранения результата
        :param total_segments: Общее количество сегментов для обработки
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

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        progress_bar = QProgressBar()
        if total_segments > 0:
            progress_bar.setRange(0, total_segments)
        else:
            progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(20)

        label = QLabel(f"0/{total_segments}" if total_segments > 0 else "0/0")
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

        duration_item = QTableWidgetItem("--:--")
        duration_item.setTextAlignment(Qt.AlignCenter)
        self.ui.taskTable.setItem(row, 3, duration_item)

        status_item = QTableWidgetItem("Ожидание")
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
            'total': total_segments,
            'duration': 0,
            'progress_bar': progress_bar,
            'progress_label': label,
            'last_segment_time': None,
            'segment_times': []
        }

        self._update_progress_bar_style(progress_bar, 'pending')
        self.ui.taskTable.resizeRowsToContents()

    def update_task_status(self, task_id: str, status: str):
        """
        Обновление статуса задачи в таблице.

        :param task_id: Идентификатор задачи
        :param status: Новый статус задачи
        """
        if task_id in self._removed_tasks:
            return

        if task_id not in self.tasks:
            logger.warning(f"Задача {task_id} не найдена в таблице")
            return

        task_data = self.tasks[task_id]
        old_status = task_data['status']
        task_data['status'] = status

        row = task_data['row']
        status_item = self.ui.taskTable.item(row, 4)
        if status_item:
            status_names = {
                'pending': 'Ожидание',
                'processing': 'Обработка',
                'resuming': 'Ожидание',
                'post_processing': 'Сборка',
                'paused': 'Приостановлена',
                'completed': 'Завершена',
                'cancelled': 'Отменена',
                'failed': 'Ошибка'
            }
            status_text = status_names.get(status, status)
            status_item.setText(status_text)
            self._set_status_color(status_item, status)

        progress_bar = task_data.get('progress_bar')
        if progress_bar:
            self._update_progress_bar_style(progress_bar, status)

        if status == 'processing' and task_id not in self.task_start_times:
            self.task_start_times[task_id] = datetime.now()
            task_data['segment_times'] = []
            task_data['last_segment_time'] = None

        if status in ['completed', 'failed', 'cancelled']:
            self.task_start_times.pop(task_id, None)

        if old_status in ['processing', 'post_processing'] and status not in ['processing', 'post_processing']:
            if task_data['segment_times']:
                avg_time = sum(task_data['segment_times']) / len(task_data['segment_times'])
                self.avg_segment_time = (self.avg_segment_time * self.segment_time_samples + avg_time) / (self.segment_time_samples + 1)
                self.segment_time_samples += 1

        self.on_selection_changed()
        self.update_progress_display()

    def update_task_progress(self, task_id: str, current: int, total: int):
        """
        Обновление прогресса выполнения задачи.

        :param task_id: Идентификатор задачи
        :param current: Текущее количество обработанных сегментов
        :param total: Общее количество сегментов
        """
        if task_id in self._removed_tasks:
            return

        if task_id not in self.tasks:
            logger.warning(f"Задача {task_id} не найдена в таблице при обновлении прогресса")
            return

        task_data = self.tasks[task_id]
        old_current = task_data['current']
        task_data['current'] = current

        if task_data['status'] in ['processing', 'post_processing'] and current > old_current:
            now = datetime.now()
            if task_data['last_segment_time'] is not None and current == old_current + 1:
                segment_time = (now - task_data['last_segment_time']).total_seconds()
                if 0.1 < segment_time < 300:
                    task_data['segment_times'].append(segment_time)
            task_data['last_segment_time'] = now

        if total > 0:
            task_data['total'] = total

        if task_data['total'] > 0:
            task_data['progress'] = (current / task_data['total']) * 100

            progress_bar = task_data.get('progress_bar')
            label = task_data.get('progress_label')

            if progress_bar:
                progress_bar.setRange(0, task_data['total'])
                progress_bar.setValue(current)

            if label:
                label.setText(f"{current}/{task_data['total']}")

            name_item = self.ui.taskTable.item(task_data['row'], 0)
            if name_item:
                name_item.setToolTip(f"Прогресс: {current}/{task_data['total']} сегментов")

            self.update_progress_display()

    def update_task_duration(self, task_id: str, duration: float, formatted_duration: str):
        """
        Обновление отображения длительности задачи.

        :param task_id: Идентификатор задачи
        :param duration: Длительность в секундах
        :param formatted_duration: Отформатированная строка длительности
        """
        if task_id in self._removed_tasks:
            return

        if task_id not in self.tasks:
            logger.warning(f"Задача {task_id} не найдена в таблице при обновлении длительности")
            return

        task_data = self.tasks[task_id]
        task_data['duration'] = duration

        row = task_data['row']
        duration_item = self.ui.taskTable.item(row, 3)
        if duration_item:
            duration_item.setText(formatted_duration)

    def _set_status_color(self, item, status: str):
        """
        Установка цвета текста элемента в зависимости от статуса.

        :param item: QTableWidgetItem для изменения цвета
        :param status: Статус задачи
        """
        color = self.STATUS_COLORS.get(status, QColor(0, 0, 0))
        item.setForeground(color)

    def _calculate_remaining_time(self) -> str:
        """
        Расчёт оставшегося времени обработки на основе статистики сегментов.

        :return: Отформатированная строка оставшегося времени
        """
        remaining_segments = 0
        processing_tasks_count = 0

        for task_id, task_data in self.tasks.items():
            status = task_data['status']
            if status in ['pending', 'processing', 'post_processing', 'resuming']:
                remaining = task_data['total'] - task_data['current']
                if remaining > 0:
                    remaining_segments += remaining
                    if status in ['processing', 'post_processing']:
                        processing_tasks_count += 1

        if remaining_segments == 0:
            return "--"

        if self.avg_segment_time > 0 and self.segment_time_samples > 0:
            avg_time = self.avg_segment_time
        else:
            segment_times = []
            for task_data in self.tasks.values():
                if task_data['segment_times']:
                    segment_times.extend(task_data['segment_times'])

            if segment_times:
                avg_time = sum(segment_times) / len(segment_times)
            else:
                avg_time = 1.0

        if processing_tasks_count > 0:
            effective_time_per_segment = avg_time / processing_tasks_count
        else:
            effective_time_per_segment = avg_time

        remaining_seconds = remaining_segments * effective_time_per_segment

        if remaining_seconds < 60:
            return f"{int(remaining_seconds)} сек"
        elif remaining_seconds < 3600:
            minutes = int(remaining_seconds / 60)
            seconds = int(remaining_seconds % 60)
            return f"{minutes} мин {seconds} сек"
        else:
            hours = int(remaining_seconds / 3600)
            minutes = int((remaining_seconds % 3600) / 60)
            return f"{hours} ч {minutes} мин"

    def update_progress_display(self):
        """Обновление всех индикаторов прогресса и статистики на экране."""
        if not self.tasks:
            self.ui.filesProgress.setValue(0)
            self.ui.totalSegmentsProgress.setValue(0)
            self.ui.timeRemainingValueLabel.setText("--")
            self.ui.statsValueLabel.setText("Активных: 0, Приостановлено: 0, Очередь: 0, Ошибок: 0")
            return

        active_tasks = sum(1 for t in self.tasks.values() 
                          if t['status'] in ['processing', 'post_processing'])
        
        paused_tasks = sum(1 for t in self.tasks.values() 
                          if t['status'] == 'paused')
        
        queue_tasks = sum(1 for t in self.tasks.values() 
                         if t['status'] in ['pending', 'resuming'])
        
        failed_tasks = sum(1 for t in self.tasks.values() 
                          if t['status'] == 'failed')

        completed_tasks = sum(1 for t in self.tasks.values() 
                             if t['status'] == 'completed')
        
        total_active = len([t for t in self.tasks.values() 
                           if t['status'] != 'cancelled'])
        
        finished_tasks = completed_tasks + failed_tasks

        if total_active > 0:
            files_progress = (finished_tasks / total_active) * 100
        else:
            files_progress = 0

        self.ui.filesProgress.setValue(int(files_progress))

        total_segments = 0
        processed_segments = 0

        for task_data in self.tasks.values():
            if task_data['status'] != 'cancelled':
                total_segments += task_data['total']
                processed_segments += task_data['current']

        if total_segments > 0:
            segments_progress = (processed_segments / total_segments) * 100
        else:
            segments_progress = 0

        self.ui.totalSegmentsProgress.setValue(int(segments_progress))

        self.ui.filesProgressLabel.setText(
            f"Прогресс по файлам: {finished_tasks}/{total_active}"
        )

        self.ui.totalSegmentsLabel.setText(
            f"Прогресс по сегментам: {processed_segments}/{total_segments} сегментов"
        )

        remaining_time = self._calculate_remaining_time()
        self.ui.timeRemainingValueLabel.setText(remaining_time)

        stats = f"Активных: {active_tasks}, Приостановлено: {paused_tasks}, Очередь: {queue_tasks}, Ошибок: {failed_tasks}"
        self.ui.statsValueLabel.setText(stats)

    def on_selection_changed(self):
        """Обновление состояния кнопок управления в зависимости от выбранных задач."""
        selected_rows = set()
        for item in self.ui.taskTable.selectedItems():
            selected_rows.add(item.row())

        selected_task_ids = []
        for task_id, task_data in self.tasks.items():
            if task_data['row'] in selected_rows:
                selected_task_ids.append(task_id)

        has_pausable = any(
            self.tasks[tid]['status'] not in self.NON_PAUSABLE_STATUSES
            for tid in selected_task_ids
        )
        has_resumable = any(
            self.tasks[tid]['status'] == 'paused'
            for tid in selected_task_ids
        )
        has_cancellable = any(
            self.tasks[tid]['status'] not in self.NON_CANCELLABLE_STATUSES
            for tid in selected_task_ids
        )

        self.ui.pauseSelectedBtn.setEnabled(has_pausable)
        self.ui.resumeSelectedBtn.setEnabled(has_resumable)
        self.ui.cancelSelectedBtn.setEnabled(has_cancellable)

    def on_pause_selected(self):
        """Обработчик кнопки приостановки выбранных задач с подтверждением пользователя."""
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
                if status not in self.NON_PAUSABLE_STATUSES:
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
        """Обработчик кнопки возобновления выбранных приостановленных задач."""
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
        """Обработчик кнопки отмены выбранных задач с подтверждением пользователя."""
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
                if status not in self.NON_CANCELLABLE_STATUSES:
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
        """Обработчик кнопки очистки завершённых, ошибочных и отменённых задач из таблицы."""
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
            self.clear_finished_requested.emit()
            self._remove_tasks_from_ui(finished_tasks + failed_tasks + cancelled_tasks)
            logger.info(f"Очищено задач: завершённых={len(finished_tasks)}, "
                       f"ошибочных={len(failed_tasks)}, отменённых={len(cancelled_tasks)}")

    def _remove_tasks_from_ui(self, task_ids_to_remove: list):
        """
        Удаление задач из таблицы интерфейса и внутренних структур.

        :param task_ids_to_remove: Список идентификаторов задач для удаления
        """
        for task_id in task_ids_to_remove:
            self._removed_tasks.add(task_id)
            if task_id in self.tasks:
                output_path = self.tasks[task_id].get('output_path')
                if output_path:
                    ProcessingScreenLogic.remove_output_path(output_path)

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
        Обработчик двойного клика по задаче — открытие папки с результатом.

        :param item: Элемент таблицы, по которому выполнен клик
        """
        row = item.row()
        for task_id, task_data in self.tasks.items():
            if task_data['row'] == row:
                if task_data['status'] == 'completed':
                    output_path = task_data['output_path']
                    QDesktopServices.openUrl(Path(output_path).parent.as_posix())
                break

    def on_open_log(self):
        """Обработчик кнопки открытия лог-файла или папки с логами."""
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
        Отображение сообщения об ошибке в интерфейсе и диалоговом окне.

        :param error_msg: Текст сообщения об ошибке
        """
        self.ui.errorNotificationLabel.setText(f"Ошибка: {error_msg}")
        QMessageBox.warning(self.ui.centralwidget, "Ошибка обработки", error_msg)

    def clear_error(self):
        """Очистка отображаемого сообщения об ошибке."""
        self.ui.errorNotificationLabel.setText("")