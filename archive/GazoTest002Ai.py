import tkinter as tk
import os
from PIL import Image, ImageTk

WIDTH =  600
HEIGHT = 600
WINDOWSSIZE = "".join([str(WIDTH),"x",str(HEIGHT)])

def ByouGa(canvas, folder_path):
    '''
    指定フォルダ内の画像(jpg/png)をCanvasに並べて表示
    '''
    img_list = []
    x1, y1 = 10, 10
    num = 0

    # フォルダ内のファイル一覧取得
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(('.jpg', '.png')):
            fpath = os.path.join(folder_path, fname)
            try:
                img = Image.open(fpath)
                img.thumbnail((200, 200))
                tkimg = ImageTk.PhotoImage(img)
                img_list.append(tkimg)
                canvas.create_image(x1, y1, image=tkimg, anchor=tk.NW)
                x1 += 210  # 横に並べる
                num += 1
            except Exception as e:
                print(f"画像表示エラー: {e}")

    # img_listを返すことで参照を保持（GC対策）
    return img_list

def main():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.geometry(WINDOWSSIZE)
    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT)
    canvas.pack()

    # 画像フォルダのパスを指定
    folder_path = "C:\\Users\\manaby\\Pictures"  # 適宜変更

    # 画像表示
    imgs = ByouGa(canvas, folder_path)

    root.mainloop()

if __name__ == "__main__":
    main()