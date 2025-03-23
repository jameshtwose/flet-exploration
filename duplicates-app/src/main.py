import flet as ft
import os
from collections import defaultdict
import re
import time

def main(page: ft.Page):
    page.title = "Duplicates Finder"
    page.window_icon = "/images/logo.png"

    folder_path = ft.TextField(label="Folder Path", width=400, read_only=True)
    file_list = ft.ListView(expand=True)
    select_all_checkbox = ft.Checkbox(label="Select/Deselect All", value=True)
    loading_indicator = ft.ProgressBar(width=400, visible=False)

    def format_size(size):
        # Convert bytes to KB, MB, or GB
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024

    def folder_selected(e):
        if e.path:
            folder_path.value = e.path
            folder_path.update()

    folder_dialog = ft.FilePicker(on_result=folder_selected)
    page.overlay.append(folder_dialog)

    def select_folder(e):
        folder_dialog.get_directory_path()

    def toggle_select_all(e):
        for control in file_list.controls:
            if isinstance(control, ft.Row):
                checkbox = control.controls[0]
                checkbox.value = select_all_checkbox.value
        file_list.update()

    def list_files_task(path):
        file_groups = defaultdict(list)
        start_time = time.time()
        for root, _, files in os.walk(path):
            for file in files:
                base_name = re.sub(r'(\(\d+\)| - Copy)$', '', os.path.splitext(file)[0])
                file_path = os.path.join(root, file)
                file_groups[base_name].append(file_path)
                # Yield control back to the UI every 100 files
                if len(file_groups) % 100 == 0:
                    yield
                # Check if the operation is taking too long
                if time.time() - start_time > 3:
                    raise TimeoutError("Too many files, operation timed out.")
        yield file_groups

    def close_timeout_dialog(e):
        page.close(timeout_dialog)

    action_button_style = ft.ButtonStyle(
        color=ft.Colors.BLACK,
        shape=ft.RoundedRectangleBorder(radius=5),
        side=ft.BorderSide(color=ft.Colors.BLACK, width=1),
    )

    timeout_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Timeout Error"),
        content=ft.Text("Too many files, operation timed out. Please select a folder with fewer files."),
        actions=[
            ft.TextButton(text="Close", style=action_button_style, on_click=close_timeout_dialog),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=ft.Colors.RED_100,
    )

    def list_files(e):
        path = folder_path.value
        if os.path.isdir(path):
            file_list.controls.clear()
            loading_indicator.visible = True
            loading_indicator.update()

            try:
                file_groups = None
                for result in list_files_task(path):
                    if isinstance(result, dict):
                        file_groups = result
                    page.update()
            except TimeoutError as ex:
                page.open(timeout_dialog)
                loading_indicator.visible = False
                loading_indicator.update()
                return

            duplicates = {k: v for k, v in file_groups.items() if len(v) > 1}
            if duplicates:
                duplicate_info = []
                for base_name, files in duplicates.items():
                    file_info = []
                    for file in files:
                        file_size = os.path.getsize(file)
                        formatted_size = format_size(file_size)
                        file_info.append((file, formatted_size, file_size))
                        # Sort files by size
                        file_info.sort(key=lambda x: x[2], reverse=True)

                    # Get the maximum file size in the group
                    max_size = max(file_info, key=lambda x: x[2])[2]
                    duplicate_info.append((base_name, file_info, max_size))

                # Sort duplicate groups by the maximum file size
                duplicate_info.sort(key=lambda x: x[2], reverse=True)

                for base_name, file_info, _ in duplicate_info:
                    file_list.controls.append(ft.Text(f"Duplicate group: {base_name}"))
                    for i, (file, formatted_size, _) in enumerate(file_info):
                        file_list.controls.append(
                            ft.Row(
                                [
                                    ft.Checkbox(value=(i == 0)),  # Select only the largest file
                                    ft.Text(file),
                                    ft.Text(formatted_size),
                                ]
                            )
                        )
            else:
                file_list.controls.append(ft.Text("No duplicates found"))
            file_list.update()
            loading_indicator.visible = False
            loading_indicator.update()
        else:
            file_list.controls.clear()
            file_list.controls.append(ft.Text("Invalid folder path"))
            file_list.update()

    def delete_selected_files(e):
        path = folder_path.value
        if os.path.isdir(path):
            for control in file_list.controls:
                if isinstance(control, ft.Row):
                    checkbox = control.controls[0]
                    file_path = control.controls[1].value
                    if checkbox.value:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
            list_files(None)
        page.close(confirm_delete_dialog)

    def open_confirm_delete_dialog(e):
        page.open(confirm_delete_dialog)

    def open_help_dialog(e):
        page.open(help_dialog)

    confirm_delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirm Deletion"),
        content=ft.Text("Are you sure you want to delete the selected files?"),
        actions=[
            ft.TextButton(
                "Cancel", on_click=lambda e: page.close(confirm_delete_dialog)
            ),
            ft.TextButton("Delete", on_click=delete_selected_files),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    help_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Help"),
        content=ft.Text(
            """This application helps you find and delete duplicate files based on their names.
Browse to a folder and click the 'List Files' button to see a list of duplicate files.
The application will display the largest file first in each of the duplicate groups.
You can select the files you want to delete and click the 'Delete Selected Files' button to remove them.
Click the 'Help' button to see this dialog again.
""".replace(
                "\n", " "
            )
        ),
        actions=[ft.TextButton("Close", on_click=lambda e: page.close(help_dialog))],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    select_all_checkbox.on_change = toggle_select_all

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        folder_path,
                        ft.Container(
                            content=ft.Image(
                                src="/images/logo.png",
                                width=100,
                                height=100,
                                fit=ft.ImageFit.CONTAIN,
                            ),
                            padding=2,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton("Select Folder", on_click=select_folder),
                        ft.ElevatedButton("List Files", on_click=list_files),
                        ft.ElevatedButton(
                            "Delete Selected Files", on_click=open_confirm_delete_dialog,
                            color="white",
                            bgcolor="red"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                select_all_checkbox,
                loading_indicator,
                file_list,
                ft.Container(
                    content=ft.ElevatedButton("Help", on_click=open_help_dialog),
                    alignment=ft.alignment.bottom_right,
                    padding=10,
                ),
            ],
            expand=True,
        )
    )

ft.app(main, assets_dir="assets")