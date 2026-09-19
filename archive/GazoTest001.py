

import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog
import os
from PIL import Image, ImageTk

WIDTH =  200
HEIGHT = 200
WINDOWSSIZE = "".join([str(WIDTH),"x",str(HEIGHT)])

def show_geometry_info(event, root, geo_label):
    geo_label["text"] = root.geometry()

def ByouGa():
    '''
    複数の画像表示
    '''
    global j,img1, FlagPicByousya, file_namae
    flag2 = 1
    k = i
    i = len(img1)
    while flag2:
        x_path = file_path.split("/")
        f_name = file_path[0:len(file_path)-(len(x_path[-1]))]
        x = file_path[:len(file_path)-(len(x_path[-1]))-1]
        i = k
        for f in f_name:
            o = str(f)

            if(o[-4:]==".jpg" or o[-4:]==".png"):# or o[-5:]==".webp"
                global num
                img1.append(Image.open(open(str(f_name)+str(o), 'rb')))
                img1[i].thumbnail((500, 500), 0)
                img1[i] = ImageTk.PhotoImage(img1[i])

                canvas.create_image(x1,y1,image=img1[i],tag="illust",anchor=tk.NW)

                num = num + 1
                i = i + 1
                print(f"{img1[i]=}")
                root.update()
        print(f"{f_name=}")
        flag2 = 0

    return

def main():
    root = tk.Tk()
    root.attributes("-topmost",True)
    root.geometry(WINDOWSSIZE)
    geo_label = tk.Label(root, bg="lightblue", font=("Helvetica", "17"))
    geo_label.pack(anchor="center", expand=1)


    #アプデ予定：右クリック＋座標またはどのボタンの上かを引数にして命令を続ける
    root.bind("<Configure>", lambda event: show_geometry_info(event, root, geo_label))

    root.mainloop()

if __name__ == "__main__":
    main()