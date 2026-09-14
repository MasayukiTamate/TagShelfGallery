'''
Created on 2021/12/19

@author: magor
'''
import tkinter as tk
import tkinter.filedialog
import os
from PIL import Image, ImageTk
import tkinter.messagebox as msg
import random
import time


'''変数
イメージ格納用リスト変数
イメージその２
フォルダ名格納リスト変数
四角リスト変数
数を格納する変数

'''
root = 0
canvas = 0 
img1 = []
img2 = []
folder = []
j = 0
k = 0
rectangles = {}
num = 0
FlagPicByousya = True
'''
'''
#基本のウィンドウ作成
root = tk.Tk()
root.attributes("-fullscreen", True)
root.title(str(""))

#《後回し》ウィンドウの縦サイズと横サイズの取得の仕方を考える
WIDTH =  root.winfo_width()
HEIGHT = root.winfo_height()
print(f"{WIDTH=} {HEIGHT=}")
canvas = tk.Canvas(root, width=3440, height=1440)
WIDTH =  root.winfo_width()
HEIGHT = root.winfo_height()
canvas.place(x=0, y=0)
#ここまで

file_namae = []
f_name = ""
'''
図形のクラス
'''
class Zukei:
    def __init__(self,x,y,w,h):
        '''
        
        '''
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        pass
    def atrari(self):
        pass
'''
クラスZukeiここまで
'''

#ダイアログからフォルダ名取得関数
def GetDiaFolder():
    '''
    ダイアログを表示
    のちにフォルダ名を取得
    '''    
    #file_path = tk.filedialog.askdirectory(initialdir = dir)

    x_path = file_path.split("/")
    f_name = file_path[0:len(file_path)-(len(x_path[-1]))]
    x = file_path[:len(file_path)-(len(x_path[-1]))-1]
    files = os.listdir(x)
    
    return files, f_name
'''
関数GetDiaFolder()ここまで
'''
#格納したデータを再描画
def Kurikaesi():
#    global img1
    flag1 = 1
    while flag1:
        canvas.create_image(random.randint(0,1000),random.randint(0,500),image=img1[i],tag="illust",anchor=tk.NW)
        i = i + 1
        if i >= len(img1):
            flag1 = 0
        root.update()

'''
関数Kurikaesi()ここまで
'''
#クリックした画像を一番最後に描写
def Kurikaesi2(n):
    global num
    flag1 = 1
    i = 0 
    img4 = [ImageTk.PhotoImage(image.copy()) for image in img1]
    for i in img2:
        canvas.delete(i)

    while flag1:
            
        

        

#        x1 = random.randint(0,1000)
#        y1 = random.randint(0,500)
#        x2 = x1 + img4[i].width()
#        y2 = y1 + img4[i].height()
        if not(n == i):
#            rectangle = canvas.create_rectangle(x1, y1, x2, y2, fill="blue")
            canvas.create_image(x1,y1,image=img4[i],tag="illust",anchor=tk.NW)
#            rectangles[rectangle] = num# 四角形に番号を割り当てる
            
        num = num + 1
        root.update()
 
        i = i + 1
        if i >= len(img4):
            flag1 = 0
        
#    x1 = random.randint(0,1000)
#   y1 = random.randint(0,500)
#    x2 = x1 + img4[n].width()
#    y2 = y1 + img4[n].height()
#    rectangle = canvas.create_rectangle(x1, y1, x2, y2, fill="blue")
    canvas.create_image(x1,y1,image=img4[n],tag="illust",anchor=tk.NW)
#    rectangles[rectangle] = num# 四角形に番号を割り当てる
    num = num + 1
    root.update()


'''
関数Kurikaesi2()ここまで
'''
#取得したフォルダの新しい画像データを読み込む

def SinByouGa():
    global j,img1, FlagPicByousya, file_namae
    flag2 = 1
    k = i
    i = len(img1)
    while flag2:
        x_path = file_path.split("/")
        f_name = file_path[0:len(file_path)-(len(x_path[-1]))]
        x = file_path[:len(file_path)-(len(x_path[-1]))-1]
#        fol = x + "/" + folder[j] + "/"
#        files = os.listdir(fol)

#        FlagPicByousya = msg.askokcancel(folder[j],str(len(files)) + "個")
        i = k
        for f in f_name:
#        for f in files:
            o = str(f)

            if(o[-4:]==".jpg" or o[-4:]==".png"):# or o[-5:]==".webp"
                global num
#                img1.append(Image.open(open(str(fol)+str(o), 'rb')))
                img1.append(Image.open(open(str(f_name)+str(o), 'rb')))
                img1[i].thumbnail((500, 500), 0)
                img1[i] = ImageTk.PhotoImage(img1[i])


                #乱数
                x1 = random.randint(0,WIDTH - 500)
                y1 = random.randint(0,HEIGHT - 500)
                x2 = x1 + img1[i].width()
                y2 = y1 + img1[i].height()
        
                rectangle = canvas.create_rectangle(x1, y1, x2, y2, fill="blue")
                rectangles[rectangle] = num# 四角形に番号を割り当てる
                canvas.create_image(x1,y1,image=img1[i],tag="illust",anchor=tk.NW)

                num = num + 1
                i = i + 1
                print(f"{img1[i]=}")
                root.update()
        print(f"{f_name=}")
        flag2 = 0

    return
'''
関数SinByouGa()ここまで
'''

#再描画クリックした画像を一番上
#子フォルダの取得
def GetKoFolder(files):
    '''
    子フォルダの取得
    '''
    for f in files:
        o = str(f)
        if not(o[0] == "."):
            if len(o) >= 4:
                if not(o[-4]=="."):
                    if not(o[-3]=="."):
                        if not(o[-5=="."]):
                            folder.append(o)
            else:
                folder.append(o)

    for f in folder:
        print(f)

    return
'''
関数GetKoFolder()ここまで
'''

def reHyoujiZahyou(sumi, sizeW,sizeH):
    '''
    表示する時に４隅にセット
    '''
    HidariUe = 0
    HidariSita = 1
    MigiUe = 2
    MigiSita = 3
    Mannaka = 4

    x1 = 0
    y1 = 0
    x2 = 0 + sizeW
    y2 = 0 + sizeH

    match sumi:
        case 1:#左下の場合
            y1 = HEIGHT - sizeH
            y2 = HEIGHT
            pass
        case 2:#右上の場合
            x1 = WIDTH - sizeW
            x2 = WIDTH
            pass
        case 3:#右下の場合
            x1 = WIDTH - sizeW
            y1 = HEIGHT - sizeH
            x2 = WIDTH
            y2 = HEIGHT
            pass
        case "真ん中":#
            pass
        case _:
            pass
    

    return x1, y1, x2, y2

#終了する時のメゾット
def owari():
    if msg.askokcancel("", "終わり？"):

        msg.showinfo("終わるのか…","終わるのか…")
        exit()
        return
    else:
        msg.showinfo("終らないのか…")
        return

'''
関数owari()ここまで
'''




'''
------------------------------------------------------------------------------------------------------------------------

プログラム基本部分

流れ
→ダイアログでフォルダ名を取得
→子フォルダ名を取得
→
→
→画像を表示


変数
パス
ファイル名

'''


file_path = tk.filedialog.askdirectory(initialdir=".")
print(f"{file_path=}")
file_path = tk.filedialog.askopenfilename(initialdir=".")
print(f"{file_path=}")
ByougaFlag = True

files, f_name = GetDiaFolder()
GetKoFolder(files)
msg.showinfo("開始の合図","始めるぞ-いいか-開始-スタート")

#ウィンドウの縦と横のサイズ
WIDTH =  root.winfo_width()
HEIGHT = root.winfo_height()



i = 0
for f in files:
    o = str(f)
    if(o[-4:]==".jpg" or o[-4:]==".png" or o[-5:]==".webp"):
        
        img1.append(Image.open(open(str(f_name)+str(o), 'rb')))
        img1[i].thumbnail((500, 500), 0)
        img2.append(ImageTk.PhotoImage(img1[i]))

        #乱数
        x1 = random.randint(0,WIDTH -500)
        y1 = random.randint(0,HEIGHT -500)
        x2 = x1 + img2[i].width()
        y2 = y1 + img2[i].height()
        
        x2 = img2[i].width()
        y2 = img2[i].height()


        x1, y1, x2, y2 = reHyoujiZahyou(int(i % 4), x2, y2)
        rectangle = canvas.create_rectangle(x1, y1, x2, y2, fill="blue")
        rectangles[rectangle] = num# 四角形に番号を割り当てる

        canvas.create_image(x1,y1,image=img2[i],tag="illust",anchor=tk.NW)


        root.update()

        num = num + 1
        
        i = i + 1



img3 = [ImageTk.PhotoImage(image.copy()) for image in img1]

while FlagPicByousya:
    SinByouGa()
    time.sleep(3)

'''
--------------------------------------------------------------------------------------------------------------------------------
操作-アクション
'''
    
#左クリックアクション
def rightClick(event):
    print(rectangles)
    global j,folder
    if j >= len(folder):
        a = msg.askokcancel("", "終わり？")
        if a:
            exit()
        else:
            global file_path, f_name
            file_path = tk.filedialog.askopenfilename(initialdir=".")
            files, f_name = GetDiaFolder()
            GetKoFolder(files)


    SinByouGa()

    j = j + 1
    return
    
#真ん中クリックアクション
def middleClick(event):

    owari()


#右クリックアクション
def leftClick(event):
    print('left')

    item = canvas.find_closest(event.x, event.y)[0]
    print(item)
    item1 = item - 1
    rectangle_number = 0
    if item1 in rectangles:
        rectangle_number = rectangles[item1]
        print(f"Rectangle number: {rectangle_number}")    
        Kurikaesi2(rectangle_number)
    return

#リターンボタンアクション
def ReturnDown(event):
    print("エンター")
    global j,folder
    if j >= len(folder):
        a = msg.askokcancel("", "終わり？")
        if a:
            exit()
        else:
            global file_path, f_name
            file_path = tk.filedialog.askopenfilename(initialdir=".")
            files, f_name = GetDiaFolder()
            GetKoFolder(files)

    SinByouGa()

    j = j + 1

    return

#キーイベント
def key_event(e):
    print(e.keysym)
    global j,folder



    if e.keysym == "Return" or e.keysym == "space":
        if j >= len(folder):
            a = msg.askokcancel("", "終わり？")
            if a:
                exit()
            else:
                msg.showinfo("","",x=0)
                global file_path, f_name
                file_path = tk.filedialog.askopenfilename(initialdir=".")
                files, f_name = GetDiaFolder()
                GetKoFolder(files)

        SinByouGa()

    j = j + 1

    return

#操作それぞれ
canvas.bind('<Button-1>', leftClick)
canvas.bind('<Button-2>', middleClick)
canvas.bind('<Button-3>', rightClick)
canvas.bind("<Return>", ReturnDown)
root.bind("<KeyPress>", key_event)
canvas.pack()



root.mainloop()