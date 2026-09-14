'''
Created on 2025 08 27

@author: tamate masayuki

英単語化
hakoNamae~BoxName
namaeHenkou=nameChange
hajimari=begins,start

今後の予定
フォルダを取得するときに子フォルダも取得する
ファイルのリスト化
ファイルのリストをテキストボックスで表示

'''
import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog
import os
from PIL import Image, ImageTk

'''_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
各パラメータ
メインウィンドウの幅
高さ
TK様式のウィンドウサイズ定数

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


#dirName = "K:\\100-eMomo"
dirName = "C:\\Users\\manaby\\Pictures"
fileName = "壁紙001.jpg"
fullFileName = dirName + "\\" + fileName

img = []
HakoNamae = []
DEFHAKOANMAE = ["色々、保存する箱"]
for n in DEFHAKOANMAE:
    HakoNamae.append(n)
'''_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
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
def Hajimari():
    '''
    ボタンを押すと新しいウィンドウで画像表示
    '''
    Gazo = tk.Toplevel()
    Gazo.geometry("220x220")
    Gazo.title("画像表示")
    GazoCanvas = tk.Canvas(Gazo, width=200, height=200)
    GazoCanvas.pack()
    # 画像表示
    img_path = fullFileName
    try:
        img = Image.open(img_path)
        img.thumbnail((200, 200))
        tkimg = ImageTk.PhotoImage(img)
        # 参照保持しないとGCで消えるのでCanvasに保持
        GazoCanvas.image = tkimg
        GazoCanvas.create_image(0, 0, image=tkimg, anchor=tk.NW)
    except Exception as e:
        print(f"画像表示エラー: {e}")
    pass

def zGazoHyoji(GazoCanvas,fileStr):
    '''
    画像表示
    '''
#    img.append(ImageTk.open(open(str(fileStr),"rb")))
    img.append(ImageTk.PhotoImage(file=str(fullFileName)))
    GazoCanvas.create_image(0,0,image=img,tag="illust",anchor="nw")
    pass

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

def namaeHenkou(event, root):
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

def kaisouHenkou(event, root):
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

def HakoSakusei(root):
    '''
    ボタンの作成
    '''
    for hn in HakoNamae:
        btn = tk.Button(root, text=hn + "\n" + dirName, command=Hajimari, width=int(WIDTH/10), height=int(HEIGHT/22))
        btn.pack()

'''_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
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

 #   canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT)
 #   canvas.pack()

    


    #ボタンの作成
    HakoSakusei(root)

    pmenu = tk.Menu(root, tearoff=0)
    pmenu.add_command(label="名前変更", command= lambda event: namaeHenkou(event, root))
    pmenu.add_command(label="フォルダ指定", command= lambda event: kaisouHenkou(event, root))
    pmenu.add_command(label="Exit", command=root.quit)

    hakoLabel = tk.Label(root, bg="lightblue", font=("Helvetica", "17"))
    geo_label = tk.Label(root, bg="lightblue", font=("Helvetica", "17"))
    geo_label.pack(anchor="center", expand=1)


    #アプデ予定：右クリック＋座標またはどのボタンの上かを引数にして命令を続ける
    root.bind("<Button-3>", lambda event: showMenu(event, pmenu))
    root.bind("<Configure>", lambda event: hako_info(event, hakoLabel))
    root.bind("<Configure>", lambda event: show_geometry_info(event, root, geo_label))

    
    root.mainloop()

if __name__ == "__main__":
    main()