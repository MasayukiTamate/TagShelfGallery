import tkinter as tk


#resize関数
#
#
#戻り値=横の減らし値、縦の減らし値
def ReSizeTkSmall(reWidth,reHeight,picWidth,picHeight):
    '''
    したいサイズの数字に変換してくれる関数
    引数=したいサイズの横と縦と絵の実際のサイズ


    '''
    mulX = 1
    mulY = 1


    return mulX, mulY

# rootメインウィンドウの設定
root = tk.Tk()
root.title("application")
root.geometry("500x700")

# メインフレームの作成と設置
frame = tk.Frame(root)
frame.pack(fill = tk.BOTH, padx=20,pady=10)

# 画像ファイルをインスタンス変数に代入
img = tk.PhotoImage(file="folder_32.png")

# 画像のリサイズ
small_img = img.subsample(6, 3)
big_img = img.zoom(2, 2)

# 各種ウィジェットの作成
#button = tk.Button(frame, text="画像", image=img, compound="top")
button_small = tk.Button(frame, text="小画像", image=small_img, compound="top")
#button_big = tk.Button(frame, text="大画像", image=big_img, compound="top")

# 各種ウィジェットの設置
#button.grid(row=0, column=0, padx=5)
button_small.grid(row=0, column=1, padx=5)
#button_big.grid(row=0, column=2, padx=5)

root.mainloop()
