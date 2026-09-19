# VS Code で Claude Code を使う方法

## 概要

VS Code から Claude Code を使うには、通常は Claude Code を CLI としてインストールし、VS Code のターミナルから起動する方法が最も簡単です。

---

## 1. 必要な準備

Node.js と npm が入っていることを確認します。

```bash
node -v
npm -v
```

もし表示されない場合は、Node.js をインストールしてから続けてください。

---

## 2. Claude Code をインストールする

ターミナルで次を実行します。

```bash
npm install -g @anthropic-ai/claude-code
```

インストール確認:

```bash
claude --version
```

正常に入っていれば、バージョン情報が表示されます。

---

## 3. 認証する

初回起動時に認証が必要です。

```bash
claude
```

指示に従ってログインまたは API キー認証を行います。

---

## 4. VS Code から起動する

VS Code でターミナルを開き、プロジェクトのルートに移動してから実行します。

```bash
cd /path/to/project
claude
```

または、どこでも実行できます。

```bash
claude
```

これで Claude Code のチャットモードが起動します。

---

## 5. 使い方の例

以下のように質問できます。

```text
このリポジトリの構成を教えて
このエラーの原因を調べて
このPythonファイルのバグを修正して
テストを追加して
```

または、プロジェクトに対して直接依頼できます。

```text
このコードをリファクタリングして
不具合の修正案を出して
```

---

## 6. よくあるトラブル

### 6.1 `claude: command not found`

Node.js が未インストール、またはグローバルパスが通っていない可能性があります。

```bash
which node
which npm
```

その後、再度実行します。

```bash
npm install -g @anthropic-ai/claude-code
```

### 6.2 認証エラー

```bash
claude
```

を実行して、ログインフローをもう一度完了させます。

### 6.3 VS Code のターミナルで反応しない

新しいターミナルを開いて、次を確認します。

```bash
echo $PATH
```

npm のグローバルパスが通っていない場合は、シェル設定を確認してください。

---

## 7. 最短手順

最短では次の2行でOKです。

```bash
npm install -g @anthropic-ai/claude-code
claude
```

その後、VS Code のターミナルで Claude Code を使えます。

---

## 8. 補足

- Claude Code は主に CLI ベースで使うのが一般的です。
- VS Code での利用は、ターミナルから起動する形が最も安定しています。
- そのままコード編集やデバッグ、リファクタリング、修正案の作成に使えます。

---

## 9. まとめ

VS Code で Claude Code を使う最も簡単な方法は、次の流れです。

1. Node.js と npm を確認
2. `npm install -g @anthropic-ai/claude-code` を実行
3. `claude` を起動して認証
4. VS Code のターミナルで `claude` を実行して利用

必要に応じて、次に「GitHub Copilot と Claude Code の違い」や「このプロジェクトでの使い方」を別途整理できます。
