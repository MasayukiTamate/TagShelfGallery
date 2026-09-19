import tkinter as tk

class CounterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("秒数カウント")

        self.count = 0
        self.label = tk.Label(root, text=f"カウント: {self.count}", font=("Helvetica", 24))
        self.label.pack(pady=20)

        self.start_counter()

    def start_counter(self):
        self.update_counter() # 最初の一回は即時実行する

    def update_counter(self):
        self.count += 1
        self.label.config(text=f"カウント: {self.count}")
        # 1000ミリ秒（1秒）後に自分自身を再度呼び出す
        self.root.after(1000, self.update_counter)

if __name__ == "__main__":
    root = tk.Tk()
    app = CounterApp(root)
    root.mainloop() # ここでイベントループが開始される
