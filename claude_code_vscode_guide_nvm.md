# VS Code で Claude Code を使う方法（nvm 版）

## 問題

`dnf install` で Node.js を入れようとしたところ、Fedora のミラー側で `nodejs-npm` が 404 になり、インストールに失敗しました。

そのため、`node` と `npm` が使えない状態です。Claude Code は Node.js が必要なので、まず Node.js を別の方法で入れる必要があります。

---

## 解決策

`nvm` を使って Node.js を入れます。これは Fedora のパッケージミラーの問題を回避しやすい方法です。

---

## 1. nvm をインストールする

ターミナルで次を実行します。

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

そのあと、現在のシェルを再読み込みします。

```bash
source ~/.bashrc
```

新しいターミナルを開いてもOKです。

---

## 2. Node.js 22 を入れる

```bash
nvm install 22
nvm use 22
```

確認します。

```bash
node -v
npm -v
```

これで `node` と `npm` が使えるようになります。

---

## 3. Claude Code をインストールする

```bash
npm install -g @anthropic-ai/claude-code
```

確認:

```bash
claude --version
```

正常に表示されればインストール済みです。

---

## 4. VS Code で起動する

VS Code のターミナルで次を実行します。

```bash
claude
```

これで Claude Code の対話モードが起動します。

---

## 5. 使い方の例

```text
このリポジトリの構成を教えて
このエラーの原因を調べて
このPythonファイルのバグを修正して
```

---

## 6. 最短手順まとめ

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
node -v
npm -v
npm install -g @anthropic-ai/claude-code
claude
```

---

## 7. 補足

`dnf install nodejs` の方法は、この Fedora 環境ではミラーの 404 で失敗したため、nvm 版を推奨します。

nvm は各ユーザーごとに Node 環境を管理できるので、システム全体の依存関係を壊しにくいです。

---

## 8. まとめ

今回の失敗は Node.js 自体が未導入だったことが原因で、Fedora のパッケージ導入経路が不安定だったためです。nvm を使えば、Claude Code を VS Code で利用できる環境を確実に作れます。
