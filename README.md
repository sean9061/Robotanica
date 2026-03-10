# 🌷 Kinetic-Botanics

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![Unity](https://img.shields.io/badge/Unity-2022%20LTS-000000?logo=unity)](https://unity.com/)
[![Arduino](https://img.shields.io/badge/Arduino-ESP32-00979D?logo=arduino)](https://www.arduino.cc/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey)](https://github.com)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-00BCD4?logo=google)](https://mediapipe.dev/)
[![YOLO](https://img.shields.io/badge/YOLO-v2.6-00FFFF?logo=ultralytics)](https://docs.ultralytics.com/)

> コンピュータビジョン・サーボ制御・リアルタイム3D可視化を融合した、インタラクティブ体感型アートインスタレーション。

[ここにデモ動画や展示の写真へのリンクを追記してください]

---

## 概要

**Kinetic-Botanics** は、人の手の動きとカメラによる花（チューリップ）の検出を組み合わせ、物理的なサーボモーターと3DCGを同時に制御するアートインスタレーションです。

- 手の動き → Arduino ESP32 経由で**サーボモーター3本**をリアルタイム制御
- カメラによる花の検出 → Unity の**3Dオブジェクトをリアルタイムアニメーション**
- 全データを集約した**監視ダッシュボード**でシステム状態を可視化

[ここにプロジェクトの背景・展示コンセプトについて追記してください]

---

## 特徴

- **手トラッキング（MediaPipe）**: Webカメラで手の骨格をリアルタイム推定。指の開き・回転角からサーボ制御値を算出
- **チューリップ検出（YOLO + CoreML）**: カスタム学習済みモデルで花を検出し、位置・信頼度をUDP送信
- **Arduino ESP32 サーボ制御**: 3軸サーボを極座標ベースで制御（0xFF ヘッダ + 3バイトプロトコル）
- **Unity 3D 可視化**: 花の位置・サイズをリアルタイムに3Dオブジェクトへマッピング（5種類のインタラクティブシーン）
- **リアルタイムダッシュボード**: 両カメラ映像・サーボ値・検出データを1画面に集約。MJPEGストリーム＋UDP受信による多マシン対応
- **マルチマシン構成**: macOS × 2台（AIトラッキング）＋ Windows × 1台（Unity・ダッシュボード）を LAN で連携

---

## システム構成

```
mac2: Hand Tracker
  カメラ → MediaPipe → Serial (Arduino ESP32)
                    → UDP [dashboard_ip]:5100  (JSON: servo/polar/detected)
                    → HTTP 0.0.0.0:5102        (MJPEG 映像ストリーム)

mac3: Tulip Tracker
  カメラ → YOLO (CoreML) → UDP [unity_ip]:5004    (JSON → Unity)
                         → UDP [dashboard_ip]:5101 (JSON: x/y/w/h/conf/detected)
                         → HTTP 0.0.0.0:5103       (MJPEG 映像ストリーム)

win1: Unity + Dashboard
  Unity     ← UDP :5004
  Dashboard ← UDP :5100 / :5101
            ← http://[mac2_ip]:5102/  (手の映像)
            ← http://[mac3_ip]:5103/  (チューリップの映像)

Arduino ESP32
  ← Serial from mac2 (0xFF ヘッダ + radius + angle)
  GPIO 25, 26, 27 → サーボ3本 (0–255 → 0–180°)
```

---

## 前提条件

### 共通
- Git

### mac2 / mac3 (Python 環境)
- Python 3.10 以上
- USB接続のWebカメラ
- （mac3のみ）Apple Silicon Mac（CoreML推論に必要）

### win1 (Unity + ダッシュボード)
- Unity 2022 LTS 以上
- Python 3.10 以上

### ハードウェア
- Arduino ESP32 開発ボード
- サーボモーター × 3
- スイッチングハブ（マルチマシン接続用）

---

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/sean9061/Kinetic-Botanics.git
cd Kinetic-Botanics
```

### 2. Hand Tracker のセットアップ（mac2）

```bash
cd ai/hand_tracker
pip install -r requirements.txt
```

### 3. Tulip Tracker のセットアップ（mac3）

```bash
cd ai/tulip_tracker
pip install -r requirements.txt
```

### 4. ダッシュボードのセットアップ（win1）

```bash
cd dashboard
pip install -r requirements.txt
```

### 5. Arduino ファームウェアの書き込み

Arduino IDE で `hardware/arduino_from_mediapipe.ino` を ESP32 に書き込みます（ボーレート: 115200）。

ライブラリ: `ESP32Servo`（Arduino IDE のライブラリマネージャーからインストール）

### 6. Unity プロジェクトを開く

Unity Hub から `unity_projects/try_interactive/` を Unity 2022 LTS で開きます。

---

## 設定

各スクリプトの先頭にある定数を環境に合わせて変更してください。

| ファイル | 定数 | 説明 |
|---------|------|------|
| `ai/hand_tracker/mediapipe_to_arduino.py` | `SERIAL_PORT` | ArduinoのCOMポート（例: `/dev/tty.usbserial-0001`） |
| `ai/hand_tracker/mediapipe_to_arduino.py` | `DASHBOARD_IP` | ダッシュボードを動かすマシンのIPアドレス |
| `ai/tulip_tracker/predict.py` | `DASHBOARD_IP` | 同上 |
| `ai/tulip_tracker/predict.py` | `UNITY_HOST` | UnityマシンのIPアドレス |

---

## 使い方

本番環境では各マシンで以下を起動します。

### mac2: Hand Tracker

```bash
cd ai/hand_tracker
python mediapipe_to_arduino.py
# カメラ映像ウィンドウが開き、右手を検出するとサーボが動きます
# ESC キーで終了
```

### mac3: Tulip Tracker

```bash
cd ai/tulip_tracker
python predict.py
# カメラ映像とYOLO検出結果がウィンドウに表示されます
# スライダーで検出閾値を調整できます (デフォルト: 80%)
# q キーで終了
```

### win1: ダッシュボード（本番）

```bash
python dashboard/dashboard.py --hand-host [mac2のIP] --tulip-host [mac3のIP]
```

### ローカルテスト（1台で全部動かす場合）

各スクリプトの `DASHBOARD_IP` を `127.0.0.1` に変更した上で:

```bash
# ターミナル1
python ai/hand_tracker/mediapipe_to_arduino.py

# ターミナル2
python ai/tulip_tracker/predict.py

# ターミナル3
python dashboard/dashboard.py --hand-host 127.0.0.1 --tulip-host 127.0.0.1
```

### Unity シーン

`unity_projects/try_interactive/Assets/Scenes/` から用途に合わせてシーンを選択:

| シーン | 内容 |
|--------|------|
| `UDP Interactive.unity` | 花の位置でオブジェクトをインタラクティブ制御 |
| `UDP Dwarf.unity` | ドワーフキャラクターを制御 |
| `UDP Joint.unity` | 骨格アニメーション |
| `Serial Interactive.unity` | シリアル（Arduino）による制御 |

---

## 開発者向けガイド

### ブランチ戦略

```bash
# 作業ブランチを作成
git checkout -b feature/your-task-name

# mainの最新を取り込む
git pull --rebase origin main

# 変更をプッシュ
git push origin feature/your-task-name
```

### YOLOモデルの再学習・エクスポート

```bash
cd ai/tulip_tracker

# PyTorchモデルをCoreML形式にエクスポート（mac3のApple Silicon向け）
python export.py

# UDP受信テスト
python udp_receiver_test.py
```

### ダッシュボードのポート一覧

| ポート | 種別 | データ内容 |
|--------|------|-----------|
| 5100 | UDP (受信) | Hand Tracker JSON（servo/polar/detected） |
| 5101 | UDP (受信) | Tulip Tracker JSON（x/y/w/h/conf/detected） |
| 5102 | HTTP (取得) | Hand Tracker MJPEG 映像 |
| 5103 | HTTP (取得) | Tulip Tracker MJPEG 映像 |
| 5004 | UDP (受信) | Tulip → Unity (花の位置情報) |

### Arduino シリアルプロトコル

```
[0xFF] [is_tracking] [radius_8bit] [angle_8bit]
  ↑         ↑              ↑             ↑
ヘッダ  検出フラグ    指の開き幅      回転角
(固定)  (0 or 1)    (0–255)       (0–255)
```

---

## ディレクトリ構成

```
Kinetic-Botanics/
├── ai/
│   ├── hand_tracker/
│   │   ├── mediapipe_to_arduino.py   # MediaPipe手検出 → Serial/UDP/MJPEG
│   │   └── requirements.txt
│   └── tulip_tracker/
│       ├── predict.py                # YOLO花検出 → UDP/MJPEG
│       ├── export.py                 # PyTorch → CoreML変換
│       ├── udp_receiver_test.py      # UDP受信テスト
│       ├── best.pt                   # 学習済みモデル (PyTorch)
│       ├── best.mlpackage/           # 学習済みモデル (CoreML)
│       └── requirements.txt
├── dashboard/
│   ├── dashboard.py                  # リアルタイム監視ダッシュボード
│   └── requirements.txt
├── hardware/
│   └── arduino_from_mediapipe.ino    # ESP32 ファームウェア
└── unity_projects/
    └── try_interactive/
        └── Assets/
            ├── Scenes/               # インタラクティブシーン (5種)
            └── Scripts/              # C#スクリプト (24ファイル)
```

---

## 貢献について

バグ報告・機能提案・Pull Request を歓迎しています！

1. このリポジトリを **Fork** する
2. `feature/your-feature` ブランチを作成する
3. 変更をコミット・プッシュする
4. **Pull Request** を作成する

バグ報告や機能提案は [Issues](https://github.com/sean9061/Kinetic-Botanics/issues) からお気軽にどうぞ。

---

## 開発チーム

このプロジェクトは **【開発チーム名】** によって開発されました。

[ここにチームメンバーのGitHubアカウントや役割を追記してください]

---

## ライセンス

このプロジェクトは **MIT License** のもとで公開されています。詳細は [LICENSE](LICENSE) ファイルをご確認ください。

---

<sub>💡 README の構成は <a href="https://claude.ai/code">Claude Code</a> との対話を通じて作成されました。</sub>
