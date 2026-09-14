import flet as ft
import os
from tkinter import filedialog
import tkinter as tk
import random

def main(page: ft.Page):
    page.window_width = 1400
    page.window_height = 900

    images = []
    current_image_index = [0]
    show_folder_hierarchy = ft.Ref[ft.Switch]()
    show_file_name = ft.Ref[ft.Switch]()

    image = ft.Image(width=800, height=400)
    image_info = ft.Text("", size=14, width=400, text_align=ft.TextAlign.CENTER)
    page.add(image, image_info)

    def next_image(e):
        if images and current_image_index[0] < len(images) - 1:
            current_image_index[0] += 1
        elif images:
            current_image_index[0] = 0
        update_image()

    def prev_image(e):
        if images and current_image_index[0] > 0:
            current_image_index[0] -= 1
        elif images:
            current_image_index[0] = len(images) - 1
        update_image()

    def random_image(e):
        if images:
            current_image_index[0] = random.randint(0, len(images) - 1)
            update_image()

    def update_image():
        if images:
            current_image = images[current_image_index[0]]
            image.src = current_image
            file_name = os.path.basename(current_image)
            folder_path = os.path.dirname(current_image)
            
            info_text = ""
            if show_file_name.current.value:
                info_text += f"ファイル名: {file_name}\n"
            if show_folder_hierarchy.current.value:
                info_text += f"フォルダ: {folder_path}\n"
            
            image_info.value = info_text.strip()
            image_count.value = f"画像 {current_image_index[0] + 1} / {len(images)}"
            page.update()
        else:
            current_image = ""

    next_button = ft.ElevatedButton(text="次の画像", on_click=next_image)
    prev_button = ft.ElevatedButton(text="前の画像", on_click=prev_image)
    random_button = ft.ElevatedButton(text="ランダム表示", on_click=random_image)

    button_row = ft.Row([prev_button, next_button, random_button], alignment=ft.MainAxisAlignment.CENTER)
    page.add(button_row)

    image_count = ft.Text("画像 0 / 0", text_align=ft.TextAlign.CENTER)
    page.add(image_count)

    def select_folder(e):
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory()
        if folder_path:
            load_images(folder_path)

    def load_images(folder_path):
        nonlocal images
        images = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    images.append(os.path.join(root, file))
        if images:
            current_image_index[0] = 0
            update_image()
        else:
            image.src = None
            image_info.value = ""
            image_count.value = "画像が見つかりません"
            page.update()

    select_folder_button = ft.ElevatedButton(text="フォルダを選択", on_click=select_folder)
    page.add(select_folder_button)

    def open_settings(e):
        page.dialog = settings_dialog
        settings_dialog.open = True
        page.update()

    settings_button = ft.ElevatedButton(text="設定", on_click=open_settings)
    page.add(settings_button)

    def close_settings(e):
        settings_dialog.open = False
        page.update()
        update_image()

    settings_dialog = ft.AlertDialog(
        title=ft.Text("設定"),
        content=ft.Column([
            ft.Row([
                ft.Text("フォルダの階層を表示"),
                ft.Switch(ref=show_folder_hierarchy, value=True)
            ]),
            ft.Row([
                ft.Text("ファイル名を表示"),
                ft.Switch(ref=show_file_name, value=True)
            ])
        ]),
        actions=[
            ft.TextButton("閉じる", on_click=close_settings),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.update()

ft.app(target=main)