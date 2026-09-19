'''
Created on 2025 08 27

@author: tamate masayuki

英単語化
hakoNamae=BoxName
namaeHenkou=nameChange
hajimari=begins,start

今後の予定
フォルダを取得するときに子フォルダも取得する
ファイルのリスト化
ファイルのリストをテキストボックスで表示-2025-09-03
_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_
'''
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # これをimport文の一番上に

import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog
from PIL import Image, ImageTk
import random
'''_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
グローバル変数の各パラメータ
メインウィンドウの幅
高さ
TK様式のウィンドウサイズ定数と様式に変換の式

初期パス
デバック用ファイル名
フルパス変数

グローバル-ピクチャー表示用リスト変数
グローバル-ボタンの名前のリスト変数-片方は要らない？-どちらか-もう一つ
ボタンのデフォルト名　　　　　　　 -片方は要らない？-どちらか-もう一つ
for文-ボタンのデフォルト名の数の分-作成-要らない工程？
_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
'''
WIDTH =  200
HEIGHT = 200
WINDOWSSIZE = "".join([str(WIDTH),"x",str(HEIGHT)])

dirName = "K:\\100-eMomo"#環境１
dirName = "C:\\Users\\manaby\\Pictures"#環境２
dirName = "C:\\Users\\"#環境３

fileName = "壁紙001.jpg"
fullFileName = dirName + "\\" + fileName

img = []
HakoNamae = []
DEFHAKOANMAE = ["色々、保存する箱"]
for n in DEFHAKOANMAE:
    HakoNamae.append(n)
'''_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
関数群
hajimari=StartPreparation
GazoHyouji=PicterDraw
hako_info=box_info
show_geometry_info
showMenu
namaeHenkou=nameChange
kaisouHenkou=なんとかfolderChange
HakoSakusei=boxcreate
_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
'''
def Hajimari(textbox):
    '''
    画僧のデータを取得
    ↓
    子窓のサイズを決める
    ↓
    描画
    '''
    from above.GazoToolsLib2 import GetKoFolder




    fn = ""
    #ファイル群を取得
    fname = os.listdir(dirName)
    # 間違い
    # dirNames = GetKoFolder(os.listdir(dirName))
    # 正しい
    dirNames = GetKoFolder(os.listdir(dirName), dirName)
    print(f"{dirNames=}")
    print(type(dirNames))
    s = fname
    textbox.insert('0.5',"\n".join(dirNames) )
    #最下層のフォルダまで探索してファイル群を取得
    #複数のフォルダからファイル群を取得


    count = 0

    while not fn.lower().endswith((".jpg",".jpeg",".png",".webg")):
        sai = random.randint(0,len(fname)-1)
        fn = fname[sai]
        count += 1
        if count > len(fname):
            print("画像ファイルが見つかりません")
            return
    print(fn)
    img_path = dirName + "\\" + fn


    img = Image.open(img_path)
    img.thumbnail((1000, 1000))
    tkimg = ImageTk.PhotoImage(img)


    width = tkimg.width()
    height = tkimg.height()
    x, y = randPoint(width,height)

    Gazo = tk.Toplevel()
    Gazo.geometry("".join([str(width),"x",str(height),"+",str(x),"+",str(y)]))
    Gazo.title(fn)
    GazoCanvas = tk.Canvas(Gazo, width=width,height=height)
    GazoCanvas.pack()
    GazoCanvas.image = tkimg
    GazoCanvas.create_image(0, 0, image=tkimg, anchor=tk.NW)

    pass


#ディスプレイのサイズが取得できるようになったら別のファイルに移動
#DISPLAY_W, DISPLAY_H = GetDisplaySize()
DISPLAY_W = 2400
DISPLAY_H = 1600
def randPoint(width, height):
    '''
    乱数作成関数で戻り値がポイント
    '''
    x = random.randint(0,DISPLAY_W-width)
    y = random.randint(0,DISPLAY_H-height)
    print(f"{width=} {height=} {x=} {y=}")
    return x, y

def randPointAndSize():
    '''
    乱数生成関数で戻り値がポイントとサイズ
    '''
    height = random.randint(12,31) * 50
    width = int(height * (3/4))

    x = random.randint(0,DISPLAY_W-width)
    y = random.randint(0,DISPLAY_H-height)

    return x, y, width, height

def hako_info(event, hakoLabel):
    '''
    ボタンの名前をラベルに表示
    予定：どのボタンの上にカーソルがあるかを判断してその名前を表示
    予定：ボタンの上にカーソルがあるときだけ表示
    '''
    hakoLabel["text"] = HakoNamae


def show_geometry_info(event, root, geo_label):
    '''
    ウィンドウのサイズをラベルに表示'''
    geo_label["text"] = root.geometry()

def showMenu(event, pmenu):
    '''
    ポップアップメニューを表示
    '''
    pmenu.post(event.x_root, event.y_root)

def namaeHenkou( root):
    '''
    ボタンの名前を変更
    '''
    new_name = tk.simpledialog.askstring("名前変更", "新しい名前を入力してください:", initialvalue=HakoNamae[0])
    if new_name:
        HakoNamae[0] = new_name
        for widget in root.winfo_children():
            widget.destroy()
        Hako = []
        for hn in HakoNamae:
            Hako.append(tk.Button(root,text=hn+"\n"+dirName, command=Hajimari,width=int(WIDTH/10),height=int(HEIGHT/22)))
        for hk in Hako:
            hk.pack()

def kaisouHenkou():
    '''
    フォルダの指定'''
    global dirName
    if dirName:
        iDir = dirName
    else:
        iDir = os.path.abspath(os.path.dirname(__file__))
    iDirPath = tk.filedialog.askdirectory(initialdir = iDir)

    dirName = iDirPath
    print(dirName)  # fの中身を表示する
    pass

def HakoSakusei(root,textbox):
    '''
    ボタンの作成'''
    Hako = []
    for hn in HakoNamae:
        Hako.append(tk.Button(root,text=hn+"\n"+dirName, command = lambda : Hajimari(textbox),width=int(WIDTH/10),height=int(HEIGHT/30)))
    for hk in Hako:
        hk.pack()

    pass

def PopupMenuCreate(root):
    '''
    ポップアップメニューの作成
    '''
    pmenu = tk.Menu(root, tearoff=0)
    pmenu.add_command(label="名前変更", command= lambda event: namaeHenkou(root))
    pmenu.add_command(label="フォルダ指定", command= lambda event: kaisouHenkou())
    pmenu.add_command(label="Exit", command=root.quit)
    return pmenu

def CreateKoWindow():
    '''
    子ウィンドウの作成  予定
    '''
    koWindowRoot = tk.Tk()
    koWindowRoot.attributes("-topmost",True)
    koWindowRoot.geometry(WINDOWSSIZE)
    textbox = tk.Text(koWindowRoot, width=40, height=120)
    textbox.pack()

    return textbox


'''/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
メイン

メイン内で行っている事
root(メイン窓)の事前設定（常に前面、ウィンドウのサイズ、タイトル）
ボタンの作成→関数
ポップアップメニューの事前設定（サブコマンド（名前変更、フォルダ設定、EXIT））
ラベルの事前設定（ボタン用のラベルと
_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
'''
def main():
    '''

    '''

    #基本のウィンドウ作成
    root = tk.Tk()
    root.attributes("-topmost",True)
    root.geometry(WINDOWSSIZE)


    #ボタンの作成
    koTextBox = CreateKoWindow()
    HakoSakusei(root, koTextBox)
    pmenu = PopupMenuCreate(root)



    hakoLabel = tk.Label(root, bg="lightblue", font=("Helvetica", "17"))
    geo_label = tk.Label(root, bg="lightblue", font=("Helvetica", "7"))
    geo_label.pack(anchor="center", expand=1)


    #アプデ予定：右クリック＋座標またはどのボタンの上かを引数にして命令を続ける
    root.bind("<Button-3>", lambda event: showMenu(event, pmenu))
    root.bind("<Configure>", lambda event: hako_info(event, hakoLabel))
    root.bind("<Configure>", lambda event: show_geometry_info(event, root, geo_label))

    print(root.geometry())
    root.mainloop()

if __name__ == "__main__":
    main()






    '''
    子窓を作成のち画像表示
    予定：フォルダ内の画像をランダムで表示
    予定：同じ画像は出てほしくない
    予定：フォルダ内の画像をリスト化してテキストボックスに表示
    予定：テキストボックスで選択した画像を表示
    予定：フォルダ内の画像をサムネイルで表示
    予定：サムネイルをクリックしたらその画像を表示
    '''
