#!/usr/bin/env python3
"""
Логика экрана прогресса обработки
"""
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtCore import QTimer, Signal, QObject, Qt
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox
from PySide6.QtGui import QDesktopServices, QColor
import logging

logger = logging.getLogger(__name__)


class ProgressScreenLogic(QObject):
    """Класс для логики экрана прогресса"""

    cancel_selected_requested = Signal(list)
    clear_finished_requested = Signal()
    pause_selected_requested = Signal(list)
    resume_selected_requested = Signal(list)
    
    def __init__(self, ui, parent, processing_manager):
        super().__init__(parent)
        self.ui = ui
        self.parent = parent
        self.processing_manager = processing_manager

        self.tasks = {}  # input_path -> task_data
        self.task_rows = {}  # input_path -> row_index
        self.active_tasks = set()
        self.paused_tasks = set()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress_display)
        self.update_timer.start(1000)

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_tasks_status)
        self.status_timer.start(2000)

        self.connect_signals()
    
    def connect_signals(self):
        """Подключение сигналов кнопок"""
        self.ui.pauseSelectedBtn.clicked.connect(self.on_pause_selected)
        self.ui.resumeSelectedBtn.clicked.connect(self.on_resume_selected)
        self.ui.cancelSelectedBtn.clicked.connect(self.on_cancel_selected)
        self.ui.clearFinishedBtn.clicked.connect(self.on_clear_finished)
        self.ui.openLogBtn.clicked.connect(self.on_open_log)
        
        # Скрываем кнопку глобальной паузы
        self.ui.pauseTasksBtn.hide() # TODO: Удалить
        
        self.ui.taskTable.itemDoubleClicked.connect(self.on_task_double_clicked)
        self.ui.taskTable.itemSelectionChanged.connect(self.on_selection_changed)
    
    def add_tasks(self, tasks: list):
        """Добавление задач в таблицу"""
        for task in tasks:
            if task.input_path not in self.tasks:
                self.add_task_to_table(task)
                self.tasks[task.input_path] = {
                    'task': task,
                    'status': 'в очереди',
                    'start_time': None,
                    'end_time': None,
                    'progress': 0,
                    'total_segments': 0,
                    'processed_segments': 0
                }
                logger.info(f"Задача добавлена в таблицу: {Path(task.input_path).name}")
    
    def add_task_to_table(self, task):
        """Добавление задачи в таблицу"""
        row = self.ui.taskTable.rowCount()
        self.ui.taskTable.insertRow(row)
        self.task_rows[task.input_path] = row

        name_item = QTableWidgetItem(Path(task.input_path).name)
        name_item.setData(Qt.UserRole, task.input_path)
        name_item.setToolTip(f"Путь: {task.input_path}\nВыход: {task.output_path}")
        self.ui.taskTable.setItem(row, 0, name_item)

        duration_item = QTableWidgetItem("--:--")
        duration_item.setTextAlignment(Qt.AlignCenter)
        self.ui.taskTable.setItem(row, 1, duration_item)

        ext = Path(task.input_path).suffix.upper()[1:]
        format_item = QTableWidgetItem(ext)
        format_item.setTextAlignment(Qt.AlignCenter)
        self.ui.taskTable.setItem(row, 2, format_item)

        status_item = QTableWidgetItem("в очереди")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(100, 100, 100))
        self.ui.taskTable.setItem(row, 3, status_item)

        if task.input_path in self.paused_tasks:
            self.update_task_display(task.input_path)
    
    def update_task_status(self, input_path: str, status: str, 
                          total_segments: int = None, processed_segments: int = None):
        """Обновление статуса задачи"""
        if input_path in self.tasks:
            task_data = self.tasks[input_path]
            old_status = task_data['status']

            if old_status == 'отменено' and status != 'отменено':
                logger.warning(f"Попытка изменить статус отменённой задачи: {input_path}")
                return

            if input_path in self.paused_tasks and status == 'обработка':
                status = 'приостановлено'
            
            task_data['status'] = status

            now = datetime.now()
            if status == 'обработка' and old_status != 'обработка':
                task_data['start_time'] = now
                self.active_tasks.add(input_path)
                logger.info(f"Начата обработка: {Path(input_path).name}")
            elif status in ['готово', 'ошибка', 'отменено'] and old_status not in ['готово', 'ошибка', 'отменено']:
                task_data['end_time'] = now
                if input_path in self.active_tasks:
                    self.active_tasks.remove(input_path)
                if input_path in self.paused_tasks:
                    self.paused_tasks.remove(input_path)
                
                if status == 'готово':
                    logger.info(f"Завершена обработка: {Path(input_path).name}")
                elif status == 'ошибка':
                    logger.error(f"Ошибка обработки: {Path(input_path).name}")
                elif status == 'отменено':
                    logger.info(f"Отменена обработка: {Path(input_path).name}")

            if total_segments is not None:
                task_data['total_segments'] = total_segments
                logger.debug(f"{Path(input_path).name}: всего сегментов {total_segments}")
            
            if processed_segments is not None:
                task_data['processed_segments'] = processed_segments
                if task_data['total_segments'] and task_data['total_segments'] > 0:
                    task_data['progress'] = (processed_segments / task_data['total_segments']) * 100

            self.update_task_display(input_path)
    
    def update_task_display(self, input_path: str):
        """Обновление отображения задачи"""
        if input_path in self.task_rows:
            row = self.task_rows[input_path]
            task_data = self.tasks[input_path]

            display_status = task_data['status']
            if input_path in self.paused_tasks and display_status not in ['готово', 'ошибка', 'отменено']:
                display_status = 'приостановлено'

            status_item = QTableWidgetItem(display_status)
            status_item.setTextAlignment(Qt.AlignCenter)

            if display_status == 'готово':
                status_item.setForeground(QColor(0, 150, 0))  # зелёный
            elif display_status == 'ошибка':
                status_item.setForeground(QColor(200, 0, 0))  # красный
            elif display_status == 'отменено':
                status_item.setForeground(QColor(150, 150, 150))  # серый
            elif display_status == 'обработка':
                status_item.setForeground(QColor(0, 0, 200))  # синий
            elif display_status == 'приостановлено':
                status_item.setForeground(QColor(255, 140, 0))  # оранжевый
            else:
                status_item.setForeground(QColor(100, 100, 100))  # серый
            
            self.ui.taskTable.setItem(row, 3, status_item)
            
            if task_data['task'].total_segments > 0:
                duration_sec = task_data['task'].total_segments * 30  # TODO: считать умнее
                minutes = duration_sec // 60
                seconds = duration_sec % 60
                duration_str = f"{minutes:02d}:{seconds:02d}"
                
                duration_item = QTableWidgetItem(duration_str)
                duration_item.setTextAlignment(Qt.AlignCenter)
                self.ui.taskTable.setItem(row, 1, duration_item)

            if task_data['total_segments'] > 0:
                tooltip = (f"Прогресс: {task_data['processed_segments']}/"
                          f"{task_data['total_segments']} сегментов "
                          f"({task_data['progress']:.1f}%)")
                self.ui.taskTable.item(row, 0).setToolTip(tooltip)
    
    def check_tasks_status(self):
        """Проверка статуса задач (опрос менеджера)"""
        if not self.tasks:
            return

        for input_path, task_data in self.tasks.items():
            task = task_data['task']
            if input_path in self.paused_tasks or task_data['status'] == 'отменено':
                continue

            if task_data['status'] == 'обработка':
                progress = task.get_progress_percentage()
                if progress > task_data['progress']:
                    task_data['progress'] = progress
                    task_data['processed_segments'] = task.cleaned_segments

                    self.update_task_display(input_path)

            if task.is_completed() and task_data['status'] != 'готово':
                self.update_task_status(input_path, 'готово')
            elif task_data['status'] == 'обработка' and task.total_segments > 0 and task.cleaned_segments == 0:
                pass
    
    def update_progress_display(self):
        """Обновление отображения прогресса"""
        if not self.tasks:
            return

        # Текущий файл (первый в обработке, не приостановленный и не отменённый)
        current_file = None
        current_progress = 0
        total_files = len(self.tasks)
        completed_files = 0
        active_files = 0
        paused_files = len(self.paused_tasks)
        cancelled_files = sum(1 for t in self.tasks.values() if t['status'] == 'отменено')

        for input_path, task_data in self.tasks.items():
            if input_path in self.paused_tasks or task_data['status'] == 'отменено':
                continue
                
            if task_data['status'] == 'обработка':
                if current_file is None:
                    current_file = input_path
                    current_progress = task_data['progress']
                active_files += 1
            elif task_data['status'] in ['готово', 'ошибка']:
                completed_files += 1

        # Обновление меток
        if current_file:
            self.ui.currentFileLabel.setText(
                f"Текущий файл: {Path(current_file).name} ({current_progress:.1f}%)"
            )
            self.ui.currentFileProgress.setValue(int(current_progress))
        else:
            if active_files == 0:
                status_parts = []
                if paused_files > 0:
                    status_parts.append(f"приостановлено: {paused_files}")
                if cancelled_files > 0:
                    status_parts.append(f"отменено: {cancelled_files}")
                
                status_text = ", ".join(status_parts) if status_parts else "нет активных задач"
                self.ui.currentFileLabel.setText(f"Текущий файл: {status_text}")
                self.ui.currentFileProgress.setValue(0)
            else:
                self.ui.currentFileLabel.setText(f"Активных задач: {active_files}")
                self.ui.currentFileProgress.setValue(0)

        # Общий прогресс (игнорируем отменённые задачи)
        total_active_files = total_files - cancelled_files
        if total_active_files > 0:
            total_progress = (completed_files / total_active_files * 100)
        else:
            total_progress = 0

        self.ui.totalProgressLabel.setText(
            f"Общий прогресс: {completed_files}/{total_active_files} файлов "
            f"(приостановлено: {paused_files}, отменено: {cancelled_files})"
        )
        self.ui.totalProgress.setValue(int(total_progress))

        # Оценка оставшегося времени
        remaining_time = self.estimate_remaining_time()
        self.ui.timeRemainingLabel.setText(f"Оставшееся время: {remaining_time}")

        # Статистика очереди
        stats = self.processing_manager.get_queue_stats()
        self.ui.taskTable.setToolTip(
            f"В очереди: {stats['queue_size']} | "
            f"Активных: {stats['active_tasks']} | "
            f"Приостановлено: {paused_files} | "
            f"Слотов: {stats['available_slots']}"
        )

    def estimate_remaining_time(self) -> str:
        """Оценка оставшегося времени"""
        active_not_paused = [p for p in self.active_tasks 
                            if p not in self.paused_tasks 
                            and self.tasks.get(p, {}).get('status') != 'отменено']
        
        if not active_not_paused:
            return "--"
        total_remaining = 0
        active_count = 0
        
        for input_path in active_not_paused:
            task_data = self.tasks.get(input_path)
            if task_data and task_data['progress'] > 0 and task_data['start_time']:
                elapsed = (datetime.now() - task_data['start_time']).total_seconds()
                if elapsed > 0:
                    total_estimated = elapsed / (task_data['progress'] / 100)
                    remaining = total_estimated - elapsed
                    if remaining > 0:
                        total_remaining += remaining
                        active_count += 1
        
        if active_count > 0:
            avg_remaining = total_remaining / active_count
            if avg_remaining < 60:
                return f"{int(avg_remaining)} сек"
            elif avg_remaining < 3600:
                return f"{int(avg_remaining / 60)} мин"
            else:
                hours = int(avg_remaining / 3600)
                minutes = int((avg_remaining % 3600) / 60)
                return f"{hours} ч {minutes} мин"
        
        return "вычисляется..."
    
    def show_error(self, error_msg: str):
        """Отображение ошибки"""
        self.ui.errorNotificationLabel.setText(f"Ошибка: {error_msg}")
        QMessageBox.warning(self.ui.centralwidget, "Ошибка обработки", error_msg)
    
    def on_selection_changed(self):
        """Обработка изменения выделения в таблице"""
        selected_rows = set()
        for item in self.ui.taskTable.selectedItems():
            selected_rows.add(item.row())

        has_cancelled = False
        for input_path, row in self.task_rows.items():
            if row in selected_rows:
                task_data = self.tasks.get(input_path)
                if task_data and task_data['status'] == 'отменено':
                    has_cancelled = True
                    break

        has_selection = len(selected_rows) > 0
        self.ui.pauseSelectedBtn.setEnabled(has_selection and not has_cancelled)
        self.ui.resumeSelectedBtn.setEnabled(has_selection and not has_cancelled)
        self.ui.cancelSelectedBtn.setEnabled(has_selection)
    
    def on_pause_selected(self):
        """Приостановка выбранных задач"""
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
        
        tasks_to_pause = []
        task_names = []
        
        for input_path, row in self.task_rows.items():
            if row in selected_rows:
                task_data = self.tasks.get(input_path)
                if task_data and task_data['status'] not in ['готово', 'ошибка', 'отменено']:
                    if input_path not in self.paused_tasks:
                        tasks_to_pause.append(input_path)
                        task_names.append(Path(input_path).name)
        
        if tasks_to_pause:
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
                for path in tasks_to_pause:
                    self.paused_tasks.add(path)
                    self.update_task_display(path)
                self.pause_selected_requested.emit(tasks_to_pause)
                
                logger.info(f"Приостановлено задач: {len(tasks_to_pause)}")
                
                QMessageBox.information(
                    self.ui.centralwidget,
                    "Задачи приостановлены",
                    f"{len(tasks_to_pause)} задач приостановлено.\n\n"
                    f"Обработка перейдёт к следующим задачам в очереди."
                )
    
    def on_resume_selected(self):
        """Возобновление выбранных задач"""
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
        
        tasks_to_resume = []
        task_names = []
        
        for input_path, row in self.task_rows.items():
            if row in selected_rows:
                task_data = self.tasks.get(input_path)
                if input_path in self.paused_tasks and task_data and task_data['status'] != 'отменено':
                    tasks_to_resume.append(input_path)
                    task_names.append(Path(input_path).name)
        
        if tasks_to_resume:
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
                for path in tasks_to_resume:
                    self.paused_tasks.remove(path)
                    self.update_task_display(path)
                self.resume_selected_requested.emit(tasks_to_resume)
                
                logger.info(f"Возобновлено задач: {len(tasks_to_resume)}")
                
                QMessageBox.information(
                    self.ui.centralwidget,
                    "Задачи возобновлены",
                    f"{len(tasks_to_resume)} задач возобновлено."
                )
    
    def on_cancel_selected(self):
        """Отмена выбранных задач"""
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
        
        tasks_to_cancel = []
        task_names = []
        
        for input_path, row in self.task_rows.items():
            if row in selected_rows:
                task_data = self.tasks.get(input_path)
                if task_data and task_data['status'] not in ['готово', 'ошибка', 'отменено']:
                    tasks_to_cancel.append(input_path)
                    task_names.append(Path(input_path).name)
        
        if tasks_to_cancel:
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
                for path in tasks_to_cancel:
                    if path in self.paused_tasks:
                        self.paused_tasks.remove(path)
                
                self.cancel_selected_requested.emit(tasks_to_cancel)

                for path in tasks_to_cancel:
                    self.update_task_status(path, 'отменяется...')
    
    def on_clear_finished(self):
        """Очистка завершённых и отменённых задач"""
        finished_count = 0
        cancelled_count = 0
        
        for input_path, task_data in list(self.tasks.items()):
            if task_data['status'] == 'отменено':
                cancelled_count += 1
            elif task_data['status'] in ['готово', 'ошибка']:
                finished_count += 1
        
        total_to_clear = finished_count + cancelled_count
        
        if total_to_clear == 0:
            QMessageBox.information(
                self.ui.centralwidget,
                "Нет задач",
                "Нет завершённых или отменённых задач для очистки"
            )
            return
        
        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Подтверждение",
            f"Очистить из таблицы:\n"
            f"• Завершённых задач: {finished_count}\n"
            f"• Отменённых задач: {cancelled_count}\n\n"
            f"Всего: {total_to_clear}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.clear_finished_requested.emit()
            rows_to_remove = []
            for input_path, row in self.task_rows.items():
                task_data = self.tasks.get(input_path)
                if task_data and task_data['status'] in ['готово', 'ошибка', 'отменено']:
                    rows_to_remove.append((input_path, row))

            for input_path, row in sorted(rows_to_remove, key=lambda x: x[1], reverse=True):
                self.ui.taskTable.removeRow(row)
                del self.task_rows[input_path]
                if input_path in self.paused_tasks:
                    self.paused_tasks.remove(input_path)
                del self.tasks[input_path]
            
            logger.info(f"Очищено завершённых: {finished_count}, отменённых: {cancelled_count}")
    
    def on_task_double_clicked(self, item):
        """Обработка двойного клика по задаче"""
        if item.column() == 0:  # клик по имени файла
            input_path = item.data(Qt.UserRole)
            task_data = self.tasks.get(input_path)
            
            if task_data and task_data['status'] == 'готово':
                output_path = task_data['task'].output_path
                QDesktopServices.openUrl(Path(output_path).parent.as_posix())
                logger.debug(f"Открыта папка: {Path(output_path).parent}")
    
    def on_open_log(self):
        """Открыть папку с логами или лог-файл"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = Path("speecheq_debug.log")
        
        try:
            import platform
            import subprocess
            import os
            
            system = platform.system()
            
            if log_file.exists():
                # Открываем файл стандартным способом для ОС
                if system == "Windows":
                    # На Windows используем start
                    os.startfile(str(log_file.absolute()))
                elif system == "Darwin":  # macOS
                    # На macOS используем open
                    subprocess.run(["open", str(log_file.absolute())], check=False)
                else:  # Linux и другие Unix-like
                    # На Linux используем xdg-open (стандартный способ)
                    subprocess.run(["xdg-open", str(log_file.absolute())], check=False)
            else:
                # Если файла нет, открываем папку
                if system == "Windows":
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